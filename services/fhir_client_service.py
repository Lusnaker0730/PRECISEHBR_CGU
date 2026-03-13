"""
FHIR Client Service
Handles all FHIR server interactions and data retrieval
"""
import logging
import time

import requests
from requests.adapters import HTTPAdapter
from fhirclient import client
from fhirclient.models import condition, medicationrequest, observation, patient, procedure

from services.circuit_breaker import circuit_breaker_registry
from services.config_loader import config_loader
from services.fhir_utils import sort_bundle_entries_by_date
from utils.input_validator import validate_loinc_code
from utils.security_labels import check_resources_security, get_security_summary

MAX_FHIR_SEARCH_COUNT = 100


class TimeoutHTTPAdapter(HTTPAdapter):
    """Custom HTTP adapter with short timeout for App Engine Standard.
    
    App Engine Standard has a hard 60-second request deadline.
    Since we make multiple FHIR calls per request, each call needs
    a short timeout (15s) to ensure total time stays under the limit.
    Retries are disabled to avoid extending total request time.
    """
    
    # GAE Standard has 60s limit; with ~4 FHIR calls, use 15s per call max
    DEFAULT_TIMEOUT = 15
    
    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop('timeout', self.DEFAULT_TIMEOUT)
        # Remove retries parameter if passed (we don't use it)
        kwargs.pop('retries', None)
        super().__init__(*args, **kwargs)
    
    def send(self, request, **kwargs):
        kwargs['timeout'] = kwargs.get('timeout', self.timeout)
        return super().send(request, **kwargs)


class FHIRClientService:
    """Service for interacting with FHIR servers."""

    # Circuit breaker defaults — tuned for clinical CDS context
    # 5 consecutive failures → open circuit for 30s
    CB_FAILURE_THRESHOLD = 5
    CB_RECOVERY_TIMEOUT = 30.0

    def __init__(self, fhir_server_url, access_token, client_id):
        """
        Initialize FHIR client service.

        Args:
            fhir_server_url: Base URL of the FHIR server
            access_token: OAuth2 access token
            client_id: Client application ID
        """
        self.fhir_server_url = fhir_server_url
        self.access_token = access_token
        self.client_id = client_id
        self.smart = self._create_client()
        # Per-server circuit breaker (state persists across request instances)
        self._cb = circuit_breaker_registry.get_or_create(
            name=fhir_server_url,
            failure_threshold=self.CB_FAILURE_THRESHOLD,
            recovery_timeout=self.CB_RECOVERY_TIMEOUT,
        )
        # Track resources that returned 403 (Break the Glass / VIP patients)
        self._access_denied_resources = []
    
    def _create_client(self):
        """
        Create and configure the FHIR client with authentication.

        Returns:
            Configured FHIRClient instance

        Raises:
            Exception: If client setup fails
        """
        settings = {
            'app_id': self.client_id,
            'api_base': self.fhir_server_url,
        }
        smart = client.FHIRClient(settings=settings)

        if not self.access_token:
            return smart

        smart.prepare()
        if hasattr(smart.server, 'prepare'):
            smart.server.prepare()

        smart.server.auth = None
        smart.server._auth = None

        if not hasattr(smart.server, 'session'):
            smart.server.session = requests.Session()

        smart.server.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/fhir+json, application/json',
            'Content-Type': 'application/fhir+json'
        })

        adapter = TimeoutHTTPAdapter(timeout=15)  # 15s per request, fits GAE 60s limit
        smart.server.session.mount('http://', adapter)
        smart.server.session.mount('https://', adapter)

        logging.info(f'FHIR client configured for: {self.fhir_server_url}')
        return smart
    
    def get_patient(self, patient_id):
        """
        Fetch patient resource.

        Args:
            patient_id: Patient identifier

        Returns:
            Tuple of (patient_resource, error_message)
        """
        if not self._cb.allow_request():
            self._cb.record_rejected()
            logging.warning(f'Circuit breaker OPEN for {self.fhir_server_url} — skipping patient fetch')
            return None, 'Health records server is temporarily unavailable. Please try again shortly.'

        try:
            logging.info(f'Fetching patient {patient_id}')
            patient_resource = patient.Patient.read(patient_id, self.smart.server)
            self._cb.record_success()
            return patient_resource.as_json(), None

        except requests.exceptions.ConnectTimeout:
            self._cb.record_failure()
            logging.error('Connection timeout fetching patient')
            return None, 'Connection to health records timed out. Please try again.'
        except requests.exceptions.ReadTimeout:
            self._cb.record_failure()
            logging.error('Read timeout fetching patient')
            return None, 'Health records server is slow to respond. Please try again.'
        except requests.exceptions.Timeout:
            self._cb.record_failure()
            logging.error('Timeout fetching patient')
            return None, 'Request timed out. The health records server may be busy.'
        except Exception as e:
            error_msg = str(e)
            logging.error(f'Error fetching patient: {type(e).__name__}')

            # Only record failure for server-side errors, not client errors (401/403/404)
            if not any(code in error_msg for code in ('401', '403', '404')):
                self._cb.record_failure()

            error_responses = {
                '401': 'Authentication failed. Please re-launch the application from your EHR.',
                '403': 'Access denied. The application may not have permission to access this patient\'s data.',
                '404': f'Patient {patient_id} not found in the FHIR server.',
            }

            for code, message in error_responses.items():
                if code in error_msg:
                    return None, message

            return None, f'Failed to retrieve patient data. Error type: {type(e).__name__}'
    
    @staticmethod
    def _is_access_denied(exception):
        """Check if an exception indicates a 403 Forbidden (Break the Glass)."""
        error_msg = str(exception).lower()
        return '403' in error_msg or 'forbidden' in error_msg

    def _record_access_denied(self, resource_type, patient_id=''):
        """Record that a resource type returned 403 Access Denied."""
        self._access_denied_resources.append(resource_type)
        logging.warning(
            f'FHIR 403 Access Denied for {resource_type} (patient {patient_id}). '
            f'Possible Break the Glass (BTG) restriction.'
        )

    def _extract_sorted_observations(self, search_result):
        """
        Extract and sort observations from a FHIR search result.

        Args:
            search_result: FHIR Bundle from observation search

        Returns:
            List of observation JSON dicts, sorted by date (most recent first)
        """
        if not search_result.entry:
            return []

        sorted_entries = sort_bundle_entries_by_date(search_result.entry, descending=True)
        return [resource.as_json() for _, resource in sorted_entries]

    def get_observations_by_loinc(self, patient_id, loinc_codes, count=5):
        """
        Fetch observations by LOINC codes.

        Args:
            patient_id: Patient identifier
            loinc_codes: List or tuple of LOINC codes
            count: Number of results to fetch

        Returns:
            List of observation resources (most recent first)
        """
        if not loinc_codes:
            return []

        # H-07: Validate LOINC codes before search
        validated_codes = []
        for code in loinc_codes:
            is_valid, _ = validate_loinc_code(code)
            if is_valid:
                validated_codes.append(code)
            else:
                logging.warning(f'Invalid LOINC code rejected: {str(code)[:20]}')
        if not validated_codes:
            return []
        count = min(max(1, count), MAX_FHIR_SEARCH_COUNT)

        if not self._cb.allow_request():
            self._cb.record_rejected()
            logging.warning(f'Circuit breaker OPEN — skipping observation fetch')
            return []

        try:
            search_params = {
                'patient': patient_id,
                'code': ','.join(validated_codes),
                '_count': str(count)
            }
            result = observation.Observation.where(search_params).perform(self.smart.server)
            self._cb.record_success()
            return self._extract_sorted_observations(result)

        except requests.exceptions.Timeout:
            self._cb.record_failure()
            logging.warning('Timeout fetching observations by LOINC')
            return []
        except Exception as e:
            if self._is_access_denied(e):
                self._record_access_denied('Observation', patient_id)
            else:
                self._cb.record_failure()
                logging.warning(f'Error fetching observations by LOINC: {type(e).__name__}')
            return []

    def get_observations_by_text(self, patient_id, text_terms, count=5):
        """
        Fetch observations by text search.

        Args:
            patient_id: Patient identifier
            text_terms: List of text search terms
            count: Number of results to fetch

        Returns:
            List of observation resources (most recent first)
        """
        if not self._cb.allow_request():
            self._cb.record_rejected()
            return []

        for term in text_terms:
            try:
                search_params = {
                    'patient': patient_id,
                    'code:text': term,
                    '_count': str(count)
                }
                result = observation.Observation.where(search_params).perform(self.smart.server)
                observations = self._extract_sorted_observations(result)

                if observations:
                    self._cb.record_success()
                    logging.info(f'Found observations via text search: {term}')
                    return observations

            except requests.exceptions.Timeout:
                self._cb.record_failure()
                logging.debug(f'Timeout for text search "{term}"')
                continue
            except Exception as e:
                if self._is_access_denied(e):
                    self._record_access_denied('Observation', patient_id)
                    return []
                self._cb.record_failure()
                logging.debug(f'Text search failed for "{term}": {type(e).__name__}')

        return []
    
    def _extract_resources(self, search_result):
        """
        Extract resources from a FHIR search result.

        Args:
            search_result: FHIR Bundle from a search

        Returns:
            List of resource JSON dicts
        """
        if not search_result.entry:
            return []
        return [entry.resource.as_json() for entry in search_result.entry if entry.resource]

    def get_conditions(self, patient_id, count=100):
        """
        Fetch patient conditions.

        Uses 'subject' search parameter per TWCDI CapabilityStatement.
        Filters by clinical-status=active to reduce payload size.

        Args:
            patient_id: Patient identifier
            count: Number of conditions to fetch

        Returns:
            List of condition resources
        """
        if not self._cb.allow_request():
            self._cb.record_rejected()
            logging.warning('Circuit breaker OPEN — skipping conditions fetch')
            return []

        try:
            result = condition.Condition.where({
                'subject': f'Patient/{patient_id}',
                'clinical-status': 'active',
                '_count': str(count)
            }).perform(self.smart.server)

            conditions_list = self._extract_resources(result)
            self._cb.record_success()
            logging.info(f'Fetched {len(conditions_list)} condition(s)')
            return conditions_list

        except requests.exceptions.Timeout:
            self._cb.record_failure()
            logging.warning('Timeout fetching conditions - continuing without condition data')
            return []
        except Exception as e:
            if self._is_access_denied(e):
                self._record_access_denied('Condition', patient_id)
            else:
                self._cb.record_failure()
                error_str = str(e).lower()
                if '504' in error_str or 'timeout' in error_str:
                    logging.error(f'Timeout fetching conditions: {type(e).__name__}')
                else:
                    logging.error(f'Error fetching conditions: {type(e).__name__}')
            return []

    def get_procedures(self, patient_id, count=50):
        """
        Fetch patient procedures.

        Uses 'subject' search parameter per TWCDI CapabilityStatement.

        Args:
            patient_id: Patient identifier
            count: Number of procedures to fetch

        Returns:
            List of procedure resources
        """
        if not self._cb.allow_request():
            self._cb.record_rejected()
            return []

        try:
            result = procedure.Procedure.where({
                'subject': f'Patient/{patient_id}',
                '_count': str(count)
            }).perform(self.smart.server)

            procedures_list = self._extract_resources(result)
            self._cb.record_success()
            logging.info(f'Fetched {len(procedures_list)} procedure(s)')
            return procedures_list

        except Exception as e:
            if self._is_access_denied(e):
                self._record_access_denied('Procedure', patient_id)
            else:
                self._cb.record_failure()
                logging.warning(f'Error fetching procedures: {type(e).__name__}')
            return []

    def get_medication_requests(self, patient_id, category=None):
        """
        Fetch patient medication requests.

        Uses 'subject' search parameter per TWCDI CapabilityStatement.
        Category filtering is done client-side because TWCDI does not
        define 'category' as a supported search parameter for MedicationRequest.

        Args:
            patient_id: Patient identifier
            category: Optional medication category for client-side filtering

        Returns:
            List of medication request resources
        """
        if not self._cb.allow_request():
            self._cb.record_rejected()
            return []

        try:
            search_params = {'subject': f'Patient/{patient_id}'}

            result = medicationrequest.MedicationRequest.where(search_params).perform(self.smart.server)

            med_list = self._extract_resources(result)

            if category:
                med_list = self._filter_by_category(med_list, category)

            self._cb.record_success()
            logging.info(f'Fetched {len(med_list)} medication request(s)')
            return med_list

        except Exception as e:
            if self._is_access_denied(e):
                self._record_access_denied('MedicationRequest', patient_id)
            else:
                self._cb.record_failure()
                logging.warning(f'Error fetching medication requests: {type(e).__name__}')
            return []

    @staticmethod
    def _filter_by_category(med_list, category):
        """
        Filter medication requests by category client-side.

        TWCDI does not support 'category' as a server-side search parameter
        for MedicationRequest, so filtering is performed after retrieval.

        Args:
            med_list: List of MedicationRequest resources
            category: Category string to match (e.g. 'outpatient')

        Returns:
            Filtered list of medication requests
        """
        filtered = []
        for med in med_list:
            for cat in med.get('category', []):
                matched = any(
                    coding.get('code') == category
                    for coding in cat.get('coding', [])
                )
                if matched or cat.get('text', '').lower() == category.lower():
                    filtered.append(med)
                    break
        return filtered
    
    def _fetch_observation_with_fallback(self, patient_id, resource_type, loinc_codes, text_terms):
        """
        Fetch observations by LOINC codes with text search fallback.

        Args:
            patient_id: Patient identifier
            resource_type: Type of observation being fetched
            loinc_codes: List of LOINC codes to search
            text_terms: List of text terms for fallback search

        Returns:
            List containing the most recent observation, or empty list
        """
        obs_list = []

        if loinc_codes:
            obs_list = self.get_observations_by_loinc(patient_id, loinc_codes)

        if not obs_list and text_terms:
            logging.debug(f'No LOINC results for {resource_type}, trying text search')
            obs_list = self.get_observations_by_text(patient_id, text_terms)

        if not obs_list:
            logging.warning(f'No {resource_type} observations found for patient {patient_id}')
            return []

        return obs_list[:1]

    def get_all_patient_data(self, patient_id):
        """
        Fetch all required patient data for PRECISE-HBR calculation.

        Args:
            patient_id: Patient identifier

        Returns:
            Tuple of (raw_data_dict, error_message)
        """
        patient_data, error = self.get_patient(patient_id)
        if error:
            return None, error

        # Validate Patient resource ownership
        if not self._validate_resource_ownership(patient_data, patient_id):
            logging.error(f"Patient resource ownership mismatch for {patient_id}")
            return None, "Patient data integrity error: resource ownership mismatch."

        loinc_codes = config_loader.get_loinc_codes()
        text_search_terms = config_loader.get_text_search_terms()

        conditions = self.get_conditions(patient_id)
        conditions = self._filter_owned_resources(conditions, patient_id, 'Condition')

        raw_data = {
            'patient': patient_data,
            'conditions': conditions,
            'med_requests': [],
            'procedures': [],
        }

        for resource_type, codes in loinc_codes.items():
            text_terms = text_search_terms.get(resource_type, [])
            observations = self._fetch_observation_with_fallback(
                patient_id, resource_type, codes, text_terms
            )
            raw_data[resource_type] = self._filter_owned_resources(
                observations, patient_id, resource_type
            )

        # Check security labels on all retrieved resources
        all_resources = self._collect_all_resources(raw_data)
        security_summary = get_security_summary(all_resources)
        
        if security_summary['warnings']:
            raw_data['_security_warnings'] = security_summary['warnings']
            logging.info(
                f"Security labels found: {security_summary['restricted_count']} restricted, "
                f"{security_summary['very_restricted_count']} very restricted resources"
            )
        
        raw_data['_security_summary'] = {
            'has_restricted': security_summary['requires_elevated_access'],
            'restricted_count': security_summary['restricted_count'],
            'very_restricted_count': security_summary['very_restricted_count'],
        }

        # Propagate Break the Glass / 403 Access Denied info
        if self._access_denied_resources:
            # Deduplicate while preserving order
            denied = list(dict.fromkeys(self._access_denied_resources))
            raw_data['_access_denied_resources'] = denied
            logging.warning(
                f'Break the Glass: {len(denied)} resource type(s) returned 403: {denied}'
            )

        return raw_data, None
    
    def _validate_resource_ownership(self, resource: dict, expected_patient_id: str) -> bool:
        """
        Validate that a FHIR resource belongs to the expected patient.

        Checks the 'subject' or 'patient' reference field to ensure the resource
        is not for a different patient (defense-in-depth against FHIR server bugs
        or MITM attacks).

        Args:
            resource: FHIR resource as dict
            expected_patient_id: The authorized patient ID

        Returns:
            True if ownership is valid or cannot be determined, False if mismatch
        """
        if not resource or not isinstance(resource, dict):
            return True

        resource_type = resource.get('resourceType', '')

        # Patient resource: check the id directly
        if resource_type == 'Patient':
            resource_id = resource.get('id')
            if resource_id and str(resource_id) != str(expected_patient_id):
                logging.warning(
                    f"OWNERSHIP MISMATCH: Patient resource id={resource_id} "
                    f"does not match expected={expected_patient_id}"
                )
                return False
            return True

        # For other resources, check subject/patient reference
        ref_value = None
        for ref_field in ('subject', 'patient'):
            ref_obj = resource.get(ref_field)
            if isinstance(ref_obj, dict):
                ref_value = ref_obj.get('reference', '')
                break
            elif isinstance(ref_obj, str):
                ref_value = ref_obj
                break

        if not ref_value:
            # No reference field — cannot validate (e.g., ValueSet); allow through
            return True

        # Extract patient ID from reference like "Patient/12345"
        expected_refs = {
            f"Patient/{expected_patient_id}",
            expected_patient_id,
        }
        if ref_value not in expected_refs:
            # Handle full URL references like "https://fhir.example.com/Patient/12345"
            if ref_value.endswith(f"/Patient/{expected_patient_id}"):
                return True
            logging.warning(
                f"OWNERSHIP MISMATCH: {resource_type} resource references "
                f"'{ref_value}', expected Patient/{expected_patient_id}"
            )
            return False

        return True

    def _filter_owned_resources(self, resources: list, patient_id: str, resource_label: str = "") -> list:
        """
        Filter a list of resources, removing any that don't belong to the expected patient.

        Args:
            resources: List of FHIR resource dicts
            patient_id: Expected patient ID
            resource_label: Label for logging (e.g. 'Observation', 'Condition')

        Returns:
            Filtered list with only owned resources
        """
        owned = []
        for r in resources:
            if self._validate_resource_ownership(r, patient_id):
                owned.append(r)
            else:
                logging.warning(
                    f"Dropping {resource_label or r.get('resourceType', 'unknown')} "
                    f"resource {r.get('id', '?')} — ownership mismatch for patient {patient_id}"
                )
        return owned

    def _collect_all_resources(self, raw_data: dict) -> list:
        """Collect all FHIR resources from raw_data for security analysis."""
        resources = []
        
        # Add patient
        if raw_data.get('patient'):
            resources.append(raw_data['patient'])
        
        # Add conditions
        for condition in raw_data.get('conditions', []):
            resources.append(condition)
        
        # Add observations (various types stored by resource_type keys)
        for key, value in raw_data.items():
            if key.startswith('_') or key in ('patient', 'conditions', 'med_requests', 'procedures'):
                continue
            if isinstance(value, list):
                resources.extend(value)
            elif isinstance(value, dict) and 'resourceType' in value:
                resources.append(value)
        
        return resources


def get_fhir_data(fhir_server_url, access_token, patient_id, client_id):
    """
    Fetch all required patient data using the fhirclient library.

    This is a convenience function for backward compatibility.

    Args:
        fhir_server_url: Base URL of the FHIR server
        access_token: OAuth2 access token
        patient_id: Patient identifier
        client_id: Client application ID

    Returns:
        Tuple of (raw_data_dict, error_message)
    """
    try:
        service = FHIRClientService(fhir_server_url, access_token, client_id)
        return service.get_all_patient_data(patient_id)
    except Exception as e:
        logging.error(f'Unexpected error in get_fhir_data: {type(e).__name__}')
        return None, 'An unexpected error occurred while fetching FHIR data.'

