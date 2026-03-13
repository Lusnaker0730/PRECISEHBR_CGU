"""
Configuration Loader Service
Handles loading and accessing CDSS configuration from cdss_config.json
"""
import logging
import json
import os
import threading


class ConfigLoader:
    """Thread-safe singleton configuration loader for CDSS system."""

    _instance = None
    _lock = threading.Lock()

    # Configuration file path relative to project root
    CONFIG_FILENAME = 'config/cdss_config.json'

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking: re-check after acquiring lock
                if cls._instance is None:
                    instance = super(ConfigLoader, cls).__new__(cls)
                    instance._config = None
                    instance._load_config()
                    cls._instance = instance
        return cls._instance

    def _get_config_path(self):
        """Get absolute path to configuration file"""
        # Go up one level from services/ to project root
        services_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(services_dir)
        # Note: CONFIG_FILENAME already includes 'config/' but we construct it robustly
        return os.path.join(project_root, 'config', 'cdss_config.json')

    def _load_config(self):
        """Load CDSS configuration from JSON file"""
        config_path = self._get_config_path()
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            logging.info(f"Successfully loaded {self.CONFIG_FILENAME} from {config_path}")
        except FileNotFoundError:
            logging.error("CRITICAL: cdss_config.json not found. Calculations will fail.")
            self._config = {}
        except json.JSONDecodeError:
            logging.error("CRITICAL: cdss_config.json is not valid JSON. Calculations will fail.")
            self._config = {}

    @property
    def config(self):
        """Get the full configuration dictionary"""
        return self._config or {}

    def get_loinc_codes(self):
        """
        Load LOINC codes from cdss_config.json.
        Returns dictionary mapping observation types to LOINC code tuples.
        """
        if not self._config:
            return {}

        lab_config = self._config.get('laboratory_value_extraction', {})

        return {
            "EGFR": tuple(lab_config.get('egfr_loinc_codes', [])),
            "CREATININE": tuple(lab_config.get('creatinine_loinc_codes', [])),
            "HEMOGLOBIN": tuple(lab_config.get('hemoglobin_loinc_codes', [])),
            "WBC": tuple(lab_config.get('white_blood_cell_loinc_codes', [])),
            "PLATELETS": tuple(lab_config.get('platelet_loinc_codes', [])),
        }

    def get_text_search_terms(self):
        """
        Load text search terms from cdss_config.json.
        Returns dictionary mapping observation types to list of text search terms.
        """
        if not self._config:
            return {}

        lab_config = self._config.get('laboratory_value_extraction', {})

        return {
            "EGFR": lab_config.get('egfr_text_search', []),
            "CREATININE": lab_config.get('creatinine_text_search', []),
            "HEMOGLOBIN": lab_config.get('hemoglobin_text_search', []),
            "WBC": lab_config.get('wbc_text_search', []),
            "PLATELETS": lab_config.get('platelet_text_search', []),
        }

    def get_snomed_codes(self, category):
        """Get SNOMED codes for a specific category"""
        return self._config.get('precise_hbr_snomed_codes', {}).get(category, {})

    def get_tradeoff_config(self):
        """Get tradeoff analysis configuration"""
        return self._config.get('tradeoff_analysis', {})

    def get_medication_keywords(self):
        """Get medication keywords configuration"""
        return self._config.get('medication_keywords', {})

    def get_bleeding_history_keywords(self):
        """Get bleeding history keywords from prior_bleeding config"""
        prior_bleeding = self.get_snomed_codes('prior_bleeding')
        return prior_bleeding.get('text_keywords', [])

    def get_fhir_systems(self):
        """Get FHIR system URIs configuration"""
        return self._config.get('fhir_systems', {})

    def get_fhir_system(self, system_name):
        """
        Get a specific FHIR system URI.

        Args:
            system_name: Key name (e.g., 'snomed_ct', 'condition_clinical')

        Returns:
            System URI string or None if not found
        """
        return self.get_fhir_systems().get(system_name)

    def get_clinical_status_codes(self, status_type='active'):
        """
        Get clinical status codes.

        Args:
            status_type: 'active' or 'inactive'

        Returns:
            List of status codes
        """
        status_config = self._config.get('clinical_status', {})
        return status_config.get(f'{status_type}_codes', [])

    def get_precise_hbr_params(self):
        """Get PRECISE-HBR parameters configuration including truncation limits and scoring coefficients"""
        return self._config.get('precise_hbr_parameters', {})


# Global instance
config_loader = ConfigLoader()
