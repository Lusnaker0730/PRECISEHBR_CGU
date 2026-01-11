"""
Tradeoff Model Calculator Service
Handles bleeding-thrombosis tradeoff risk calculation

All clinical codes and thresholds are loaded from cdss_config.json for maintainability.
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


class TradeoffModelCalculator:
    """Calculator for bleeding-thrombosis tradeoff analysis"""

    # Default FHIR system URIs
    DEFAULT_SNOMED_SYSTEM = 'http://snomed.info/sct'
    DEFAULT_RXNORM_SYSTEM = 'http://www.nlm.nih.gov/research/umls/rxnorm'

    # Mapping from config keys to tradeoff data keys for conditions
    CONDITION_MAPPINGS = {
        'diabetes': 'diabetes',
        'myocardial_infarction': 'prior_mi',
        'copd': 'copd',
    }

    # Conditions that map to nstemi_stemi (any match sets it True)
    NSTEMI_STEMI_KEYS = ('nstemi', 'stemi')

    # Mapping from config keys to tradeoff data keys for procedures
    PROCEDURE_MAPPINGS = {
        'complex_pci': 'complex_pci',
        'bare_metal_stent': 'bms_used',
    }

    @classmethod
    def _get_snomed_system(cls):
        """Get SNOMED CT system URI from config"""
        return config_loader.get_fhir_system('snomed_ct') or cls.DEFAULT_SNOMED_SYSTEM

    @classmethod
    def _get_rxnorm_system(cls):
        """Get RxNorm system URI from config"""
        return config_loader.get_fhir_system('rxnorm') or cls.DEFAULT_RXNORM_SYSTEM

    @staticmethod
    def _resource_has_code(resource, system, code):
        """Checks if a resource's coding matches the given system and code."""
        codings = resource.get('code', {}).get('coding', [])
        return any(
            coding.get('system') == system and coding.get('code') == code
            for coding in codings
        )
    
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
        query_limits = tradeoff_config.get('fhir_query_limits', {})
        snomed_system = cls._get_snomed_system()

        # Fetch and check conditions
        try:
            condition_limit = query_limits.get('conditions', 200)
            conditions = condition.Condition.where({
                'patient': patient_id,
                '_count': str(condition_limit)
            }).perform(fhir_client.server)

            if conditions.entry:
                for entry in conditions.entry:
                    resource_json = entry.resource.as_json()

                    # Check standard condition mappings
                    for config_key, data_key in cls.CONDITION_MAPPINGS.items():
                        code = snomed_codes.get(config_key)
                        if code and cls._resource_has_code(resource_json, snomed_system, code):
                            tradeoff_data[data_key] = True

                    # Check for NSTEMI/STEMI (multiple codes map to same flag)
                    for key in cls.NSTEMI_STEMI_KEYS:
                        code = snomed_codes.get(key)
                        if code and cls._resource_has_code(resource_json, snomed_system, code):
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
                'patient': patient_id,
                '_count': str(procedure_limit)
            }).perform(fhir_client.server)

            if procedures.entry:
                for entry in procedures.entry:
                    resource_json = entry.resource.as_json()
                    for config_key, data_key in cls.PROCEDURE_MAPPINGS.items():
                        code = snomed_codes.get(config_key)
                        if code and cls._resource_has_code(resource_json, snomed_system, code):
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
                'patient': patient_id,
                'category': 'outpatient'
            }).perform(fhir_client.server)

            if med_requests.entry:
                for entry in med_requests.entry:
                    mr = entry.resource
                    if any(cls._resource_has_code(mr.as_json(), rxnorm_system, code)
                           for code in oac_codes):
                        tradeoff_data["oac_discharge"] = True

        except Exception as e:
            logging.warning(f"Error fetching medication requests for OAC: {e}")
        
        return tradeoff_data
    
    @staticmethod
    def _get_empty_tradeoff_data():
        """Returns empty tradeoff data structure"""
        return {
            "diabetes": False,
            "prior_mi": False,
            "smoker": False,
            "nstemi_stemi": False,
            "complex_pci": False,
            "bms_used": False,
            "copd": False,
            "oac_discharge": False
        }
    
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
    
    @staticmethod
    def detect_tradeoff_factors(raw_data, demographics, tradeoff_data):
        """
        Detects which tradeoff factors are present based on patient data.
        
        Args:
            raw_data: Dictionary with FHIR observation data
            demographics: Dictionary with patient demographics
            tradeoff_data: Dictionary with clinical factor flags
        
        Returns:
            Dictionary of detected factor keys
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
                
                if moderate['min'] <= hb_val < moderate['max']:
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
            
            if moderate['min'] <= egfr_val < moderate['max']:
                detected_factors['egfr_30_59'] = True
            elif egfr_val < severe['max']:
                detected_factors['egfr_lt_30'] = True
                
        if not egfr_checked:
            missing_data.append('eGFR')
        
        # Clinical factors - map tradeoff_data keys to detected_factors keys
        clinical_factor_mappings = {
            'diabetes': 'diabetes',
            'prior_mi': 'prior_mi',
            'smoker': 'smoker',
            'nstemi_stemi': 'nstemi_stemi',
            'complex_pci': 'complex_pci',
            'bms_used': 'bms',  # Note: key differs in detected_factors
            'copd': 'copd',
            'oac_discharge': 'oac_discharge',
        }
        for source_key, target_key in clinical_factor_mappings.items():
            if tradeoff_data.get(source_key):
                detected_factors[target_key] = True

        return detected_factors, missing_data
    
    @staticmethod
    def convert_hr_to_probability(total_hr_score, baseline_event_rate):
        """
        Converts a total Hazard Ratio (HR) score to an estimated 1-year event probability.
        
        Uses the Cox proportional hazards model:
        P(event) = 1 - exp(-baseline_hazard × HR)
        
        Args:
            total_hr_score: Total hazard ratio (product of individual HRs)
            baseline_event_rate: Baseline event rate as percentage
        
        Returns:
            Event probability as percentage (0-100)
        """
        baseline_rate_decimal = baseline_event_rate / 100.0
        
        if baseline_rate_decimal >= 1.0:
            return 100.0
        
        baseline_hazard = -math.log(1 - baseline_rate_decimal)
        adjusted_hazard = baseline_hazard * total_hr_score
        survival_probability = math.exp(-adjusted_hazard)
        event_probability = 1 - survival_probability
        event_probability_percent = event_probability * 100.0
        
        return round(min(event_probability_percent, 100.0), 2)
    
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
        tradeoff_config = config_loader.get_tradeoff_config()
        baseline_rates = tradeoff_config.get('baseline_event_rates', {})
        baseline_bleeding_rate = baseline_rates.get('bleeding_rate_percent', 2.5)
        baseline_thrombotic_rate = baseline_rates.get('thrombotic_rate_percent', 2.5)

        bleeding_hr, bleeding_factors = cls._calculate_event_score(
            model_predictors['bleedingEvents']['predictors'],
            active_factors
        )
        thrombotic_hr, thrombotic_factors = cls._calculate_event_score(
            model_predictors['thromboticEvents']['predictors'],
            active_factors
        )

        return {
            "bleeding_score": cls.convert_hr_to_probability(bleeding_hr, baseline_bleeding_rate),
            "thrombotic_score": cls.convert_hr_to_probability(thrombotic_hr, baseline_thrombotic_rate),
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

