"""
Tradeoff Model Calculator Service
Handles bleeding-thrombosis tradeoff risk calculation

All clinical codes, thresholds, and mappings are loaded from cdss_config.json for maintainability.
"""
import json
import logging
import math
import os

from fhirclient.models import condition, medicationrequest, observation, procedure

from services.config_loader import config_loader
from services.fhir_client_service import FHIRClientService
from services.fhir_utils import get_observation_effective_date_from_model
from services.unit_conversion_service import unit_converter


def _is_outpatient_category(med_resource):
    """Check if a MedicationRequest has 'outpatient' category (client-side filter)."""
    for cat in med_resource.get('category', []):
        for coding in cat.get('coding', []):
            if coding.get('code') == 'outpatient':
                return True
        if cat.get('text', '').lower() == 'outpatient':
            return True
    return False


class TradeoffModelCalculator:
    """Calculator for bleeding-thrombosis tradeoff analysis"""

    # Default FHIR system URIs (fallback if config missing)
    DEFAULT_SNOMED_SYSTEM = 'http://snomed.info/sct'
    DEFAULT_RXNORM_SYSTEM = 'http://www.nlm.nih.gov/research/umls/rxnorm'

    # Default mappings (fallback if config missing)
    DEFAULT_CONDITION_MAPPINGS = {
        'diabetes': 'diabetes',
        'myocardial_infarction': 'prior_mi',
        'copd': 'copd',
    }
    DEFAULT_NSTEMI_STEMI_KEYS = ('nstemi', 'stemi')
    DEFAULT_PROCEDURE_MAPPINGS = {
        'complex_pci': 'complex_pci',
        'bare_metal_stent': 'bms_used',
    }
    DEFAULT_TRADEOFF_DATA_FIELDS = [
        'diabetes', 'prior_mi', 'smoker', 'nstemi_stemi',
        'complex_pci', 'bms_used', 'copd', 'oac_discharge'
    ]
    DEFAULT_CLINICAL_FACTOR_MAPPINGS = {
        'diabetes': 'diabetes',
        'prior_mi': 'prior_mi',
        'smoker': 'smoker',
        'nstemi_stemi': 'nstemi_stemi',
        'complex_pci': 'complex_pci',
        'bms_used': 'bms',
        'copd': 'copd',
        'oac_discharge': 'oac_discharge',
    }

    @classmethod
    def _get_snomed_system(cls):
        """Get SNOMED CT system URI from config"""
        return config_loader.get_fhir_system('snomed_ct') or cls.DEFAULT_SNOMED_SYSTEM

    @classmethod
    def _get_rxnorm_system(cls):
        """Get RxNorm system URI from config"""
        return config_loader.get_fhir_system('rxnorm') or cls.DEFAULT_RXNORM_SYSTEM

    @classmethod
    def _get_condition_mappings(cls):
        """Get condition mappings from config"""
        tradeoff_config = config_loader.get_tradeoff_config()
        return tradeoff_config.get('condition_mappings', cls.DEFAULT_CONDITION_MAPPINGS)

    @classmethod
    def _get_nstemi_stemi_keys(cls):
        """Get NSTEMI/STEMI keys from config"""
        tradeoff_config = config_loader.get_tradeoff_config()
        keys = tradeoff_config.get('nstemi_stemi_keys', list(cls.DEFAULT_NSTEMI_STEMI_KEYS))
        return tuple(keys) if isinstance(keys, list) else keys

    @classmethod
    def _get_procedure_mappings(cls):
        """Get procedure mappings from config"""
        tradeoff_config = config_loader.get_tradeoff_config()
        return tradeoff_config.get('procedure_mappings', cls.DEFAULT_PROCEDURE_MAPPINGS)

    @classmethod
    def _get_tradeoff_data_fields(cls):
        """Get tradeoff data field names from config"""
        tradeoff_config = config_loader.get_tradeoff_config()
        return tradeoff_config.get('tradeoff_data_fields', cls.DEFAULT_TRADEOFF_DATA_FIELDS)

    @classmethod
    def _get_clinical_factor_mappings(cls):
        """Get clinical factor mappings from config"""
        tradeoff_config = config_loader.get_tradeoff_config()
        return tradeoff_config.get('clinical_factor_mappings', cls.DEFAULT_CLINICAL_FACTOR_MAPPINGS)

    @staticmethod
    def _resource_has_code(resource, system, code):
        """Checks if a resource's coding matches the given system and code."""
        codings = resource.get('code', {}).get('coding', [])
        return any(
            coding.get('system') == system and coding.get('code') == code
            for coding in codings
        )

    @staticmethod
    def _resource_has_icd10_prefix(resource, icd10_prefixes):
        """
        Check if a resource has an ICD-10-CM or ICD-10-PCS code matching any prefix.

        TWCDI-compliant servers may use ICD-10 instead of SNOMED CT.

        Args:
            resource: FHIR resource as dict
            icd10_prefixes: List of ICD-10 code prefixes to match

        Returns:
            True if any coding matches an ICD-10 prefix
        """
        icd10_systems = ('icd-10-cm', 'icd-10-pcs', 'icd-10')
        for coding in resource.get('code', {}).get('coding', []):
            system = coding.get('system', '').lower()
            code = coding.get('code', '')
            if any(s in system for s in icd10_systems):
                if any(code == prefix or code.startswith(prefix + '.') or code.startswith(prefix)
                       for prefix in icd10_prefixes):
                    return True
        return False
    
    @classmethod
    def get_tradeoff_data(cls, fhir_server_url, access_token, client_id, patient_id):
        """
        Fetches additional data required for the bleeding-thrombosis tradeoff model.
        
        Args:
            fhir_server_url: FHIR server base URL
            access_token: OAuth2 access token
            client_id: Client application ID
            patient_id: Patient identifier
        
        Returns:
            Dictionary with tradeoff factor flags
        """
        try:
            fhir_service = FHIRClientService(fhir_server_url, access_token, client_id)
            fhir_client = fhir_service.smart
            
        except Exception as e:
            logging.error(f"Failed to create FHIRClient in get_tradeoff_data: {e}")
            return cls._get_empty_tradeoff_data()
        
        tradeoff_data = cls._get_empty_tradeoff_data()
        tradeoff_config = config_loader.get_tradeoff_config()
        snomed_codes = tradeoff_config.get('snomed_codes', {})
        icd10_codes = tradeoff_config.get('icd10_codes', {})
        query_limits = tradeoff_config.get('fhir_query_limits', {})
        snomed_system = cls._get_snomed_system()

        # Get mappings from config
        condition_mappings = cls._get_condition_mappings()
        nstemi_stemi_keys = cls._get_nstemi_stemi_keys()
        procedure_mappings = cls._get_procedure_mappings()

        # Fetch and check conditions
        try:
            condition_limit = query_limits.get('conditions', 200)
            conditions = condition.Condition.where({
                'subject': f'Patient/{patient_id}',
                'clinical-status': 'active',
                '_count': str(condition_limit)
            }).perform(fhir_client.server)

            if conditions.entry:
                for entry in conditions.entry:
                    resource_json = entry.resource.as_json()

                    # Check standard condition mappings (SNOMED + ICD-10 fallback)
                    for config_key, data_key in condition_mappings.items():
                        code = snomed_codes.get(config_key)
                        if code and cls._resource_has_code(resource_json, snomed_system, code):
                            tradeoff_data[data_key] = True
                        elif config_key in icd10_codes:
                            if cls._resource_has_icd10_prefix(resource_json, icd10_codes[config_key]):
                                tradeoff_data[data_key] = True

                    # Check for NSTEMI/STEMI (multiple codes map to same flag)
                    for key in nstemi_stemi_keys:
                        code = snomed_codes.get(key)
                        if code and cls._resource_has_code(resource_json, snomed_system, code):
                            tradeoff_data["nstemi_stemi"] = True
                            break
                        elif key in icd10_codes:
                            if cls._resource_has_icd10_prefix(resource_json, icd10_codes[key]):
                                tradeoff_data["nstemi_stemi"] = True
                                break

        except Exception as e:
            logging.warning(f"Error fetching conditions for tradeoff model: {e}")
        
        # Check for smoking status
        try:
            smoking_config = tradeoff_config.get('smoking_status', {})
            smoking_loinc = smoking_config.get('loinc_code', '72166-2')
            current_smoker_codes = smoking_config.get('current_smoker_codes', ['449868002', 'LA18978-9'])

            obs_search = observation.Observation.where({
                'patient': patient_id,
                'code': smoking_loinc
            }).perform(fhir_client.server)

            if obs_search and obs_search.entry:
                sorted_obs = []
                for entry in obs_search.entry:
                    if entry.resource:
                        date_str = get_observation_effective_date_from_model(entry.resource)
                        sorted_obs.append((date_str, entry.resource))

                if sorted_obs:
                    sorted_obs.sort(key=lambda x: x[0], reverse=True)
                    latest_obs = sorted_obs[0][1]
                    if latest_obs.valueCodeableConcept and latest_obs.valueCodeableConcept.coding:
                        if latest_obs.valueCodeableConcept.coding[0].code in current_smoker_codes:
                            tradeoff_data["smoker"] = True

        except Exception as e:
            logging.warning(f"Error fetching smoking status: {e}")
        
        # Check for complex PCI and BMS from procedures
        try:
            procedure_limit = query_limits.get('procedures', 50)
            procedures = procedure.Procedure.where({
                'subject': f'Patient/{patient_id}',
                '_count': str(procedure_limit)
            }).perform(fhir_client.server)

            if procedures.entry:
                for entry in procedures.entry:
                    resource_json = entry.resource.as_json()
                    for config_key, data_key in procedure_mappings.items():
                        code = snomed_codes.get(config_key)
                        if code and cls._resource_has_code(resource_json, snomed_system, code):
                            tradeoff_data[data_key] = True
                        elif config_key in icd10_codes:
                            if cls._resource_has_icd10_prefix(resource_json, icd10_codes[config_key]):
                                tradeoff_data[data_key] = True

        except Exception as e:
            logging.warning(f"Error fetching procedures for tradeoff model: {e}")
        
        # Check for OAC at discharge
        try:
            # Get RxNorm codes from medication_keywords (consolidated location)
            med_keywords = config_loader.get_medication_keywords()
            oac_config = med_keywords.get('oral_anticoagulants', {})
            oac_codes = oac_config.get('rxnorm_codes', ['11289', '1364430', '21821', '1037042', '1537033'])
            rxnorm_system = cls._get_rxnorm_system()

            med_requests = medicationrequest.MedicationRequest.where({
                'subject': f'Patient/{patient_id}',
            }).perform(fhir_client.server)

            if med_requests.entry:
                for entry in med_requests.entry:
                    # Client-side category filter (TWCDI does not support category search param)
                    mr_json = entry.resource.as_json()
                    if not _is_outpatient_category(mr_json):
                        continue
                    mr = entry.resource
                    if any(cls._resource_has_code(mr.as_json(), rxnorm_system, code)
                           for code in oac_codes):
                        tradeoff_data["oac_discharge"] = True

        except Exception as e:
            logging.warning(f"Error fetching medication requests for OAC: {e}")
        
        return tradeoff_data
    
    @classmethod
    def _get_empty_tradeoff_data(cls):
        """Returns empty tradeoff data structure based on config"""
        fields = cls._get_tradeoff_data_fields()
        return {field: False for field in fields}
    
    @staticmethod
    def load_tradeoff_model():
        """
        Loads and returns the tradeoff model from arc-hbr-model.json.
        
        Returns:
            Dictionary with tradeoff model data or None if error
        """
        script_dir = os.path.dirname(os.path.dirname(__file__))  # Go up one level from services/
        model_path = os.path.join(script_dir, 'fhir_resources', 'valuesets', 'arc-hbr-model.json')
        
        logging.info(f"Attempting to load tradeoff model from: {model_path}")
        
        try:
            with open(model_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if 'tradeoffModel' not in data:
                    logging.error(f"'tradeoffModel' key not found in JSON")
                    return None
                
                model = data['tradeoffModel']
                logging.info(f"Tradeoff model loaded successfully")
                return model
        
        except FileNotFoundError as e:
            logging.error(f"File not found: {model_path}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error loading tradeoff model: {e}")
            return None
    
    @classmethod
    def detect_tradeoff_factors(cls, raw_data, demographics, tradeoff_data):
        """
        Detects which tradeoff factors are present based on patient data.
        
        Args:
            raw_data: Dictionary with FHIR observation data
            demographics: Dictionary with patient demographics
            tradeoff_data: Dictionary with clinical factor flags
        
        Returns:
            Tuple of (detected_factors dict, missing_data list)
        """
        detected_factors = {}
        
        tradeoff_config = config_loader.get_tradeoff_config()
        thresholds = tradeoff_config.get('risk_factor_thresholds', {})
        
        # Age threshold
        missing_data = []
        age = demographics.get('age')
        age_threshold = thresholds.get('age_threshold', 65)
        
        if age is not None:
            if age >= age_threshold:
                detected_factors['age_ge_65'] = True
        else:
            missing_data.append('Age')
        
        # Hemoglobin thresholds
        hb_obs = raw_data.get('HEMOGLOBIN', [])
        hb_checked = False
        if hb_obs:
            hb_val = unit_converter.get_value_from_observation(
                hb_obs[0], 
                unit_converter.TARGET_UNITS['HEMOGLOBIN']
            )
            if hb_val is not None:
                hb_checked = True
                hb_ranges = thresholds.get('hemoglobin_ranges', {})
                moderate = hb_ranges.get('moderate', {'min': 11, 'max': 13})
                severe = hb_ranges.get('severe', {'max': 11})
                
                if moderate['min'] <= hb_val <= moderate['max']:
                    detected_factors['hemoglobin_11_12.9'] = True
                elif hb_val < severe['max']:
                    detected_factors['hemoglobin_lt_11'] = True
        
        if not hb_checked:
            missing_data.append('Hemoglobin')
        
        # eGFR thresholds
        egfr_obs = raw_data.get('EGFR', [])
        cr_obs = raw_data.get('CREATININE', [])
        egfr_val = None
        egfr_checked = False
        
        if egfr_obs:
            egfr_val = unit_converter.get_value_from_observation(
                egfr_obs[0], 
                unit_converter.TARGET_UNITS['EGFR']
            )
        
        if egfr_val is None and cr_obs:
            cr_val = unit_converter.get_value_from_observation(
                cr_obs[0], 
                unit_converter.TARGET_UNITS['CREATININE']
            )
            if cr_val and age is not None and demographics.get('gender'):
                egfr_val, _ = unit_converter.calculate_egfr(
                    cr_val, 
                    age, 
                    demographics['gender']
                )
        
        if egfr_val is not None:
            egfr_checked = True
            egfr_ranges = thresholds.get('egfr_ranges', {})
            moderate = egfr_ranges.get('moderate', {'min': 30, 'max': 60})
            severe = egfr_ranges.get('severe', {'max': 30})
            
            if moderate['min'] <= egfr_val <= moderate['max']:
                detected_factors['egfr_30_59'] = True
            elif egfr_val < severe['max']:
                detected_factors['egfr_lt_30'] = True
                
        if not egfr_checked:
            missing_data.append('eGFR')
        
        # Clinical factors - get mappings from config
        clinical_factor_mappings = cls._get_clinical_factor_mappings()
        for source_key, target_key in clinical_factor_mappings.items():
            if tradeoff_data.get(source_key):
                detected_factors[target_key] = True

        return detected_factors, missing_data
    
    # Baseline 1-year event rate for the ARC-HBR reference group (all
    # predictors absent).  Validated against the official ARC-HBR app
    # (25 golden-dataset cases, max error < 0.01%).
    _BASELINE_EVENT_RATE_PERCENT = 1.4

    @staticmethod
    def convert_hr_to_probability(total_hr_score, baseline_event_rate):
        """
        Converts a total Hazard Ratio (HR) product to an estimated 1-year
        event probability using the Cox proportional hazards model.

        Formula: P = 1 - exp(-baseline_hazard × HR)

        Args:
            total_hr_score: Total hazard ratio (product of individual HRs)
            baseline_event_rate: Baseline 1-year event rate as percentage

        Returns:
            Event probability as percentage (0-100)
        """
        # Validate inputs to prevent math domain errors
        if baseline_event_rate <= 0:
            logging.warning(f"baseline_event_rate={baseline_event_rate} is non-positive, returning 0")
            return 0.0
        if baseline_event_rate >= 100.0:
            return 100.0
        if total_hr_score <= 0:
            logging.warning(f"total_hr_score={total_hr_score} is non-positive, returning 0")
            return 0.0

        baseline_rate_decimal = baseline_event_rate / 100.0
        baseline_hazard = -math.log(1 - baseline_rate_decimal)
        adjusted_hazard = baseline_hazard * total_hr_score

        # Guard against overflow in exp()
        try:
            event_probability = 1 - math.exp(-adjusted_hazard)
        except OverflowError:
            return 100.0

        return round(min(event_probability * 100.0, 100.0), 2)
    
    @classmethod
    def calculate_tradeoff_scores(cls, raw_data, demographics, tradeoff_data):
        """
        Calculates bleeding and thrombotic risk scores using the ARC-HBR tradeoff model.
        
        Uses the same JSON model as calculate_tradeoff_scores_interactive for consistency.
        
        Args:
            raw_data: Dictionary with FHIR observation data
            demographics: Dictionary with patient demographics
            tradeoff_data: Dictionary with clinical factor flags
        
        Returns:
            Dictionary with bleeding and thrombotic scores and factors
        """
        model = cls.load_tradeoff_model()
        if not model:
            logging.error("Failed to load tradeoff model")
            return {
                "error": "ARC-HBR model file not found on server.",
                "bleeding_score": 0,
                "thrombotic_score": 0,
                "bleeding_factors": [],
                "thrombotic_factors": []
            }

        # Detect which factors are active based on patient data
        active_factors, missing_data = cls.detect_tradeoff_factors(raw_data, demographics, tradeoff_data)
        
        # Use the interactive calculation method with the detected factors
        # This ensures consistency between both calculation paths
        result = cls.calculate_tradeoff_scores_interactive(model, active_factors)
        
        # Inject missing data info
        result['missing_data'] = missing_data
        if missing_data:
            result['warning'] = f"Missing data for: {', '.join(missing_data)}. Risks may be underestimated."
            
        return result
    
    @classmethod
    def _calculate_event_score(cls, predictors, active_factors):
        """
        Calculates hazard ratio score and factor details for a set of predictors.

        Args:
            predictors: List of predictor dictionaries from the model
            active_factors: Dictionary of active factor flags

        Returns:
            Tuple of (hazard_ratio_product, factor_details_list)
        """
        hr_product = 1.0
        factor_details = []

        for predictor in predictors:
            factor_key = predictor['factor']
            if active_factors.get(factor_key, False):
                hr_product *= predictor['hazardRatio']
                factor_details.append(
                    f"{predictor['description']} (HR: {predictor['hazardRatio']})"
                )

        return hr_product, factor_details

    @classmethod
    def calculate_tradeoff_scores_interactive(cls, model_predictors, active_factors):
        """
        Calculates bleeding and thrombotic scores for interactive mode.

        Args:
            model_predictors: Model predictor data
            active_factors: Dictionary of active factor flags

        Returns:
            Dictionary with scores and factor details
        """
        bleeding_hr, bleeding_factors = cls._calculate_event_score(
            model_predictors['bleedingEvents']['predictors'],
            active_factors
        )
        thrombotic_hr, thrombotic_factors = cls._calculate_event_score(
            model_predictors['thromboticEvents']['predictors'],
            active_factors
        )

        baseline = cls._BASELINE_EVENT_RATE_PERCENT

        return {
            "bleeding_score": cls.convert_hr_to_probability(
                bleeding_hr, baseline),
            "thrombotic_score": cls.convert_hr_to_probability(
                thrombotic_hr, baseline),
            "bleeding_factors": bleeding_factors,
            "thrombotic_factors": thrombotic_factors
        }


# Global instance
tradeoff_calculator = TradeoffModelCalculator()


# Legacy functions for backward compatibility
def get_tradeoff_model_data(fhir_server_url, access_token, client_id, patient_id):
    """Legacy function - calls the new service"""
    return tradeoff_calculator.get_tradeoff_data(fhir_server_url, access_token, client_id, patient_id)


def get_tradeoff_model_predictors():
    """Legacy function - calls the new service"""
    return tradeoff_calculator.load_tradeoff_model()


def detect_tradeoff_factors(raw_data, demographics, tradeoff_data):
    """Legacy function - calls the new service"""
    val, _ = tradeoff_calculator.detect_tradeoff_factors(raw_data, demographics, tradeoff_data)
    return val


def calculate_tradeoff_scores(raw_data, demographics, tradeoff_data):
    """Legacy function - calls the new service"""
    return tradeoff_calculator.calculate_tradeoff_scores(raw_data, demographics, tradeoff_data)


def calculate_tradeoff_scores_interactive(model_predictors, active_factors):
    """Legacy function - calls the new service"""
    return tradeoff_calculator.calculate_tradeoff_scores_interactive(model_predictors, active_factors)
