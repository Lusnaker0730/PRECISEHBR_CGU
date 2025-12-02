"""
FHIR Client Service
Handles all FHIR server interactions and data retrieval
"""
import logging
import requests
from requests.adapters import HTTPAdapter
from fhirclient import client
from fhirclient.models import patient, observation, condition, medicationrequest, procedure
from services.config_loader import config_loader
from services.fhir_utils import get_observation_effective_date


class TimeoutHTTPAdapter(HTTPAdapter):
    """Custom HTTP adapter with configurable timeout"""
    
    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop('timeout', 60)  # 60 seconds default
        super().__init__(*args, **kwargs)
    
    def send(self, request, **kwargs):
        kwargs['timeout'] = kwargs.get('timeout', self.timeout)
        return super().send(request, **kwargs)


class FHIRClientService:
    """Service for interacting with FHIR servers"""
    
    def __init__(self, fhir_server_url, access_token, client_id):
        """
        Initialize FHIR client service
        
        Args:
            fhir_server_url: Base URL of the FHIR server
            access_token: OAuth2 access token
            client_id: Client application ID
        """
        self.fhir_server_url = fhir_server_url
        self.access_token = access_token
        self.client_id = client_id
        self.smart = None
        self._setup_client()
    
    def _setup_client(self):
        """Set up FHIR client with authentication"""
        try:
            # Set up FHIR client settings
            settings = {
                'app_id': self.client_id,
                'api_base': self.fhir_server_url,
            }
            
            # Create FHIR client instance
            self.smart = client.FHIRClient(settings=settings)
            
            # Set authorization
            if self.access_token:
                self.smart.prepare()
                
                if hasattr(self.smart.server, 'prepare'):
                    self.smart.server.prepare()
                
                self.smart.server.auth = None
                
                # Set proper headers for FHIR requests
                headers = {
                    'Authorization': f'Bearer {self.access_token}',
                    'Accept': 'application/fhir+json, application/json',
                    'Content-Type': 'application/fhir+json'
                }
                
                # Use the server's session to set headers
                if not hasattr(self.smart.server, 'session'):
                    self.smart.server.session = requests.Session()
                self.smart.server.session.headers.update(headers)
                
                # Set up custom adapter with timeout
                adapter = TimeoutHTTPAdapter(timeout=90)  # 90 seconds for condition queries
                self.smart.server.session.mount('http://', adapter)
                self.smart.server.session.mount('https://', adapter)
                
                self.smart.server._auth = None
                
                logging.debug(f"Set authorization header with token length: {len(self.access_token)}")
                logging.info(f"FHIR Server prepared for: {self.fhir_server_url}")
        
        except Exception as e:
            logging.error(f"Failed to set up FHIR client: {type(e).__name__}")
            raise
    
    def get_patient(self, patient_id):
        """
        Fetch patient resource
        
        Args:
            patient_id: Patient identifier
        
        Returns:
            Tuple of (patient_resource, error_message)
        """
        try:
            logging.info(f"Attempting to fetch patient {patient_id} from {self.fhir_server_url}")
            patient_resource = patient.Patient.read(patient_id, self.smart.server)
            logging.info(f"Successfully fetched Patient resource for patient: {patient_id}")
            return patient_resource.as_json(), None
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error fetching patient resource. Status code or error type: {type(e).__name__}")
            
            if '401' in error_msg:
                return None, f"Authentication failed. Please re-launch the application from your EHR."
            elif '403' in error_msg:
                return None, f"Access denied. The application may not have permission to access this patient's data."
            elif '404' in error_msg:
                return None, f"Patient {patient_id} not found in the FHIR server."
            else:
                return None, f"Failed to retrieve patient data. Error type: {type(e).__name__}"
    
    def get_observations_by_loinc(self, patient_id, loinc_codes, count=5):
        """
        Fetch observations by LOINC codes
        
        Args:
            patient_id: Patient identifier
            loinc_codes: List or tuple of LOINC codes
            count: Number of results to fetch
        
        Returns:
            List of observation resources (most recent first)
        """
        try:
            if not loinc_codes:
                return []
            
            search_params = {
                'patient': patient_id,
                'code': ','.join(loinc_codes),
                '_count': str(count)
            }
            
            observations = observation.Observation.where(search_params).perform(self.smart.server)
            
            if observations.entry:
                # Sort by effective date in memory using shared utility
                sorted_entries = []
                for entry in observations.entry:
                    if entry.resource:
                        resource_json = entry.resource.as_json()
                        date_str = get_observation_effective_date(resource_json)
                        sorted_entries.append((date_str, resource_json))
                
                sorted_entries.sort(key=lambda x: x[0], reverse=True)
                return [entry[1] for entry in sorted_entries]
            
            return []
        
        except Exception as e:
            logging.warning(f"Error fetching observations by LOINC: {type(e).__name__}")
            return []
    
    def get_observations_by_text(self, patient_id, text_terms, count=5):
        """
        Fetch observations by text search
        
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
                
                text_observations = observation.Observation.where(search_params).perform(self.smart.server)
                
                if text_observations.entry:
                    sorted_entries = []
                    for entry in text_observations.entry:
                        if entry.resource:
                            resource_json = entry.resource.as_json()
                            date_str = get_observation_effective_date(resource_json)
                            sorted_entries.append((date_str, resource_json))
                    
                    sorted_entries.sort(key=lambda x: x[0], reverse=True)
                    logging.info(f"Successfully fetched observations by text search: '{term}'")
                    return [entry[1] for entry in sorted_entries]
            
            except Exception as e:
                logging.debug(f"Text search failed for term '{term}': {type(e).__name__}")
                continue
        
        return []
    
    def get_conditions(self, patient_id, count=100):
        """
        Fetch patient conditions
        
        Args:
            patient_id: Patient identifier
            count: Number of conditions to fetch
        
        Returns:
            List of condition resources
        """
        try:
            logging.info(f"Attempting to fetch conditions with _count={count} for patient {patient_id}")
            conditions_search = condition.Condition.where({
                'patient': patient_id,
                '_count': str(count)
            }).perform(self.smart.server)
            
            conditions_list = []
            if conditions_search.entry:
                for entry in conditions_search.entry:
                    if entry.resource:
                        conditions_list.append(entry.resource.as_json())
            
            logging.info(f"Successfully fetched {len(conditions_list)} condition(s)")
            return conditions_list
        
        except Exception as e:
            error_str = str(e)
            if '504' in error_str or 'timeout' in error_str.lower():
                logging.error(f"Timeout error fetching conditions: {type(e).__name__}")
            else:
                logging.error(f"Error fetching conditions: {type(e).__name__}")
            return []
    
    def get_procedures(self, patient_id, count=50):
        """Fetch patient procedures"""
        try:
            procedures_search = procedure.Procedure.where({
                'patient': patient_id,
                '_count': str(count)
            }).perform(self.smart.server)
            
            procedures_list = []
            if procedures_search.entry:
                for entry in procedures_search.entry:
                    if entry.resource:
                        procedures_list.append(entry.resource.as_json())
            
            logging.info(f"Successfully fetched {len(procedures_list)} procedure(s)")
            return procedures_list
        
        except Exception as e:
            logging.warning(f"Error fetching procedures: {type(e).__name__}")
            return []
    
    def get_medication_requests(self, patient_id, category=None):
        """Fetch patient medication requests"""
        try:
            search_params = {'patient': patient_id}
            if category:
                search_params['category'] = category
            
            med_requests_search = medicationrequest.MedicationRequest.where(search_params).perform(self.smart.server)
            
            med_requests_list = []
            if med_requests_search.entry:
                for entry in med_requests_search.entry:
                    if entry.resource:
                        med_requests_list.append(entry.resource.as_json())
            
            logging.info(f"Successfully fetched {len(med_requests_list)} medication request(s)")
            return med_requests_list
        
        except Exception as e:
            logging.warning(f"Error fetching medication requests: {type(e).__name__}")
            return []
    
    def get_all_patient_data(self, patient_id):
        """
        Fetch all required patient data for PRECISE-HBR calculation
        
        Args:
            patient_id: Patient identifier
        
        Returns:
            Tuple of (raw_data_dict, error_message)
        """
        # Get patient demographics
        patient_data, error = self.get_patient(patient_id)
        if error:
            return None, error
        
        raw_data = {"patient": patient_data}
        
        # Get LOINC codes and text search terms from config
        loinc_codes = config_loader.get_loinc_codes()
        text_search_terms = config_loader.get_text_search_terms()
        
        # Fetch observations for each resource type
        for resource_type, codes in loinc_codes.items():
            obs_list = []
            
            # Try LOINC codes first
            if codes:
                obs_list = self.get_observations_by_loinc(patient_id, codes)
                if obs_list:
                    logging.info(f"Successfully fetched {resource_type} observation by LOINC code")
            
            # Fall back to text search if needed
            if not obs_list and resource_type in text_search_terms:
                text_terms = text_search_terms[resource_type]
                if text_terms:
                    logging.info(f"No results from LOINC codes for {resource_type}, attempting text search")
                    obs_list = self.get_observations_by_text(patient_id, text_terms)
            
            raw_data[resource_type] = obs_list[:1] if obs_list else []  # Take most recent only
            
            if not obs_list:
                logging.warning(f"No {resource_type} observations found for patient {patient_id}")
        
        # Fetch conditions
        raw_data['conditions'] = self.get_conditions(patient_id)
        
        # Fetch minimal medication data for compatibility
        raw_data['med_requests'] = []
        raw_data['procedures'] = []
        
        return raw_data, None


def get_fhir_data(fhir_server_url, access_token, patient_id, client_id):
    """
    Legacy function for backward compatibility.
    Fetches all required patient data using the fhirclient library.
    
    Returns a dictionary of FHIR resources and an error message if any.
    """
    try:
        fhir_service = FHIRClientService(fhir_server_url, access_token, client_id)
        return fhir_service.get_all_patient_data(patient_id)
    except Exception as e:
        logging.error(f"An unexpected error occurred in get_fhir_data. Error type: {type(e).__name__}")
        return None, "An unexpected error occurred while fetching FHIR data."

