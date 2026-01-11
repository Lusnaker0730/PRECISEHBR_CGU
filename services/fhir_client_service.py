"""
FHIR Client Service
Handles all FHIR server interactions and data retrieval
"""
import logging

import requests
from requests.adapters import HTTPAdapter
from fhirclient import client
from fhirclient.models import condition, medicationrequest, observation, patient, procedure

from services.config_loader import config_loader
from services.fhir_utils import sort_bundle_entries_by_date


class TimeoutHTTPAdapter(HTTPAdapter):
    """Custom HTTP adapter with configurable timeout"""
    
    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop('timeout', 60)  # 60 seconds default
        super().__init__(*args, **kwargs)
    
    def send(self, request, **kwargs):
        kwargs['timeout'] = kwargs.get('timeout', self.timeout)
        return super().send(request, **kwargs)


class FHIRClientService:
    """Service for interacting with FHIR servers."""

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

        adapter = TimeoutHTTPAdapter(timeout=90)
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
        try:
            logging.info(f'Fetching patient {patient_id}')
            patient_resource = patient.Patient.read(patient_id, self.smart.server)
            return patient_resource.as_json(), None

        except Exception as e:
            error_msg = str(e)
            logging.error(f'Error fetching patient: {type(e).__name__}')

            error_responses = {
                '401': 'Authentication failed. Please re-launch the application from your EHR.',
                '403': 'Access denied. The application may not have permission to access this patient\'s data.',
                '404': f'Patient {patient_id} not found in the FHIR server.',
            }

            for code, message in error_responses.items():
                if code in error_msg:
                    return None, message

            return None, f'Failed to retrieve patient data. Error type: {type(e).__name__}'
    
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

        try:
            search_params = {
                'patient': patient_id,
                'code': ','.join(loinc_codes),
                '_count': str(count)
            }
            result = observation.Observation.where(search_params).perform(self.smart.server)
            return self._extract_sorted_observations(result)

        except Exception as e:
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
                    logging.info(f'Found observations via text search: {term}')
                    return observations

            except Exception as e:
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

        Args:
            patient_id: Patient identifier
            count: Number of conditions to fetch

        Returns:
            List of condition resources
        """
        try:
            result = condition.Condition.where({
                'patient': patient_id,
                '_count': str(count)
            }).perform(self.smart.server)

            conditions_list = self._extract_resources(result)
            logging.info(f'Fetched {len(conditions_list)} condition(s)')
            return conditions_list

        except Exception as e:
            error_str = str(e).lower()
            if '504' in error_str or 'timeout' in error_str:
                logging.error(f'Timeout fetching conditions: {type(e).__name__}')
            else:
                logging.error(f'Error fetching conditions: {type(e).__name__}')
            return []

    def get_procedures(self, patient_id, count=50):
        """
        Fetch patient procedures.

        Args:
            patient_id: Patient identifier
            count: Number of procedures to fetch

        Returns:
            List of procedure resources
        """
        try:
            result = procedure.Procedure.where({
                'patient': patient_id,
                '_count': str(count)
            }).perform(self.smart.server)

            procedures_list = self._extract_resources(result)
            logging.info(f'Fetched {len(procedures_list)} procedure(s)')
            return procedures_list

        except Exception as e:
            logging.warning(f'Error fetching procedures: {type(e).__name__}')
            return []

    def get_medication_requests(self, patient_id, category=None):
        """
        Fetch patient medication requests.

        Args:
            patient_id: Patient identifier
            category: Optional medication category filter

        Returns:
            List of medication request resources
        """
        try:
            search_params = {'patient': patient_id}
            if category:
                search_params['category'] = category

            result = medicationrequest.MedicationRequest.where(search_params).perform(self.smart.server)

            med_list = self._extract_resources(result)
            logging.info(f'Fetched {len(med_list)} medication request(s)')
            return med_list

        except Exception as e:
            logging.warning(f'Error fetching medication requests: {type(e).__name__}')
            return []
    
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

        loinc_codes = config_loader.get_loinc_codes()
        text_search_terms = config_loader.get_text_search_terms()

        raw_data = {
            'patient': patient_data,
            'conditions': self.get_conditions(patient_id),
            'med_requests': [],
            'procedures': [],
        }

        for resource_type, codes in loinc_codes.items():
            text_terms = text_search_terms.get(resource_type, [])
            raw_data[resource_type] = self._fetch_observation_with_fallback(
                patient_id, resource_type, codes, text_terms
            )

        return raw_data, None


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

