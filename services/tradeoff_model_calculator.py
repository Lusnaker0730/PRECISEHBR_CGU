"""
Tradeoff Model Calculator Service
Handles bleeding-thrombosis tradeoff risk calculation
"""
import logging
import json
import os
import math
from services.config_loader import config_loader
from services.unit_conversion_service import unit_converter
from services.fhir_client_service import FHIRClientService
from fhirclient.models import observation, condition, procedure, medicationrequest


class TradeoffModelCalculator:
    """Calculator for bleeding-thrombosis tradeoff analysis"""
    
    @staticmethod
    def _resource_has_code(resource, system, code):
        """Checks if a resource's coding matches the given system and code."""
        for coding in resource.get('code', {}).get('coding', []):
            if coding.get('system') == system and coding.get('code') == code:
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
        
        # Fetch and check conditions
        try:
            conditions = condition.Condition.where({
                'patient': patient_id, 
                '_count': '200'
            }).perform(fhir_client.server)
            
            if conditions.entry:
                for entry in conditions.entry:
                    c = entry.resource
                    
                    # Check for diabetes
                    diabetes_code = snomed_codes.get('diabetes', '73211009')
                    if cls._resource_has_code(c.as_json(), 'http://snomed.info/sct', diabetes_code):
                        tradeoff_data["diabetes"] = True
                    
                    # Check for MI
                    mi_code = snomed_codes.get('myocardial_infarction', '22298006')
                    if cls._resource_has_code(c.as_json(), 'http://snomed.info/sct', mi_code):
                        tradeoff_data["prior_mi"] = True
                    
                    # Check for NSTEMI/STEMI
                    nstemi_code = snomed_codes.get('nstemi', '164868009')
                    stemi_code = snomed_codes.get('stemi', '164869001')
                    if cls._resource_has_code(c.as_json(), 'http://snomed.info/sct', nstemi_code) or \
                       cls._resource_has_code(c.as_json(), 'http://snomed.info/sct', stemi_code):
                        tradeoff_data["nstemi_stemi"] = True
                    
                    # Check for COPD
                    copd_code = snomed_codes.get('copd', '13645005')
                    if cls._resource_has_code(c.as_json(), 'http://snomed.info/sct', copd_code):
                        tradeoff_data["copd"] = True
        
        except Exception as e:
            logging.warning(f"Error fetching conditions for tradeoff model: {e}")
        
        # Check for smoking status
        try:
            obs_search = observation.Observation.where({
                'patient': patient_id, 
                'code': '72166-2'  # Smoking status LOINC
            }).perform(fhir_client.server)
            
            if obs_search and obs_search.entry:
                sorted_obs = []
                for entry in obs_search.entry:
                    if entry.resource:
                        date_str = '1900-01-01'
                        if hasattr(entry.resource, 'effectiveDateTime') and entry.resource.effectiveDateTime:
                            date_str = entry.resource.effectiveDateTime.isostring
                        elif hasattr(entry.resource, 'effectivePeriod') and entry.resource.effectivePeriod:
                            if entry.resource.effectivePeriod.start:
                                date_str = entry.resource.effectivePeriod.start.isostring
                        sorted_obs.append((date_str, entry.resource))
                
                if sorted_obs:
                    sorted_obs.sort(key=lambda x: x[0], reverse=True)
                    latest_obs = sorted_obs[0][1]
                    if latest_obs.valueCodeableConcept and latest_obs.valueCodeableConcept.coding:
                        if latest_obs.valueCodeableConcept.coding[0].code in ['449868002', 'LA18978-9']:
                            tradeoff_data["smoker"] = True
        
        except Exception as e:
            logging.warning(f"Error fetching smoking status: {e}")
        
        # Check for complex PCI and BMS from procedures
        try:
            procedures = procedure.Procedure.where({
                'patient': patient_id, 
                '_count': '50'
            }).perform(fhir_client.server)
            
            if procedures.entry:
                complex_pci_code = snomed_codes.get('complex_pci', '397682003')
                bms_code = snomed_codes.get('bare_metal_stent', '427183000')
                
                for entry in procedures.entry:
                    p = entry.resource
                    if cls._resource_has_code(p.as_json(), 'http://snomed.info/sct', complex_pci_code):
                        tradeoff_data["complex_pci"] = True
                    if cls._resource_has_code(p.as_json(), 'http://snomed.info/sct', bms_code):
                        tradeoff_data["bms_used"] = True
        
        except Exception as e:
            logging.warning(f"Error fetching procedures for tradeoff model: {e}")
        
        # Check for OAC at discharge
        try:
            rxnorm_codes = tradeoff_config.get('rxnorm_codes', {})
            oac_codes = [
                rxnorm_codes.get('warfarin', '11289'),
                rxnorm_codes.get('rivaroxaban', '21821'),
                rxnorm_codes.get('apixaban', '1364430'),
                rxnorm_codes.get('dabigatran', '1037042'),
                rxnorm_codes.get('edoxaban', '1537033')
            ]
            
            med_requests = medicationrequest.MedicationRequest.where({
                'patient': patient_id, 
                'category': 'outpatient'
            }).perform(fhir_client.server)
            
            if med_requests.entry:
                for entry in med_requests.entry:
                    mr = entry.resource
                    if any(cls._resource_has_code(mr.as_json(), 'http://www.nlm.nih.gov/research/umls/rxnorm', code) 
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
        age_threshold = thresholds.get('age_threshold', 65)
        if demographics.get('age', 0) >= age_threshold:
            detected_factors['age_ge_65'] = True
        
        # Hemoglobin thresholds
        hb_obs = raw_data.get('HEMOGLOBIN', [])
        if hb_obs:
            hb_val = unit_converter.get_value_from_observation(
                hb_obs[0], 
                unit_converter.TARGET_UNITS['HEMOGLOBIN']
            )
            if hb_val:
                hb_ranges = thresholds.get('hemoglobin_ranges', {})
                moderate = hb_ranges.get('moderate', {'min': 11, 'max': 13})
                severe = hb_ranges.get('severe', {'max': 11})
                
                if moderate['min'] <= hb_val < moderate['max']:
                    detected_factors['hemoglobin_11_12.9'] = True
                elif hb_val < severe['max']:
                    detected_factors['hemoglobin_lt_11'] = True
        
        # eGFR thresholds
        egfr_obs = raw_data.get('EGFR', [])
        cr_obs = raw_data.get('CREATININE', [])
        egfr_val = None
        
        if egfr_obs:
            egfr_val = unit_converter.get_value_from_observation(
                egfr_obs[0], 
                unit_converter.TARGET_UNITS['EGFR']
            )
        elif cr_obs:
            cr_val = unit_converter.get_value_from_observation(
                cr_obs[0], 
                unit_converter.TARGET_UNITS['CREATININE']
            )
            if cr_val and demographics.get('age') and demographics.get('gender'):
                egfr_val, _ = unit_converter.calculate_egfr(
                    cr_val, 
                    demographics['age'], 
                    demographics['gender']
                )
        
        if egfr_val:
            egfr_ranges = thresholds.get('egfr_ranges', {})
            moderate = egfr_ranges.get('moderate', {'min': 30, 'max': 60})
            severe = egfr_ranges.get('severe', {'max': 30})
            
            if moderate['min'] <= egfr_val < moderate['max']:
                detected_factors['egfr_30_59'] = True
            elif egfr_val < severe['max']:
                detected_factors['egfr_lt_30'] = True
        
        # Clinical factors
        if tradeoff_data.get('diabetes'):
            detected_factors['diabetes'] = True
        if tradeoff_data.get('prior_mi'):
            detected_factors['prior_mi'] = True
        if tradeoff_data.get('smoker'):
            detected_factors['smoker'] = True
        if tradeoff_data.get('nstemi_stemi'):
            detected_factors['nstemi_stemi'] = True
        if tradeoff_data.get('complex_pci'):
            detected_factors['complex_pci'] = True
        if tradeoff_data.get('bms_used'):
            detected_factors['bms'] = True
        if tradeoff_data.get('copd'):
            detected_factors['copd'] = True
        if tradeoff_data.get('oac_discharge'):
            detected_factors['oac_discharge'] = True
        
        return detected_factors
    
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
        
        # Get baseline rates from configuration
        tradeoff_config = config_loader.get_tradeoff_config()
        baseline_rates = tradeoff_config.get('baseline_event_rates', {})
        baseline_bleeding_rate = baseline_rates.get('bleeding_rate_percent', 2.5)
        baseline_thrombotic_rate = baseline_rates.get('thrombotic_rate_percent', 2.5)
        
        # Use multiplicative model: start with HR = 1
        bleeding_score_hr = 1.0
        thrombotic_score_hr = 1.0
        
        bleeding_factors = []
        thrombotic_factors = []
        
        # Helper function to add score
        def add_score(event_type, factor, ratio):
            nonlocal bleeding_score_hr, thrombotic_score_hr
            if event_type == 'bleeding':
                bleeding_score_hr *= ratio
                bleeding_factors.append(f"{factor} (HR: {ratio})")
            else:
                thrombotic_score_hr *= ratio
                thrombotic_factors.append(f"{factor} (HR: {ratio})")
        
        # Demographics
        if demographics.get('age', 0) >= 65:
            add_score('bleeding', 'Age >= 65', 1.50)
        
        # Hemoglobin
        hb_obs = raw_data.get('HEMOGLOBIN', [])
        if hb_obs:
            hb_val = unit_converter.get_value_from_observation(
                hb_obs[0], 
                unit_converter.TARGET_UNITS['HEMOGLOBIN']
            )
            if hb_val:
                if 11 <= hb_val < 13:
                    add_score('bleeding', 'Hb 11-12.9', 1.69)
                    add_score('thrombotic', 'Hb 11-12.9', 1.27)
                elif hb_val < 11:
                    add_score('bleeding', 'Hb < 11', 3.99)
                    add_score('thrombotic', 'Hb < 11', 1.50)
        
        # eGFR
        egfr_obs = raw_data.get('EGFR', [])
        if egfr_obs:
            egfr_val = unit_converter.get_value_from_observation(
                egfr_obs[0], 
                unit_converter.TARGET_UNITS['EGFR']
            )
            if egfr_val:
                if 30 <= egfr_val < 60:
                    add_score('thrombotic', 'eGFR 30-59', 1.30)
                elif egfr_val < 30:
                    add_score('bleeding', 'eGFR < 30', 1.43)
                    add_score('thrombotic', 'eGFR < 30', 1.69)
        
        # Tradeoff data factors
        if tradeoff_data.get('diabetes'):
            add_score('thrombotic', 'Diabetes', 1.56)
        if tradeoff_data.get('prior_mi'):
            add_score('thrombotic', 'Prior MI', 1.89)
        if tradeoff_data.get('smoker'):
            add_score('bleeding', 'Smoker', 1.47)
            add_score('thrombotic', 'Smoker', 1.48)
        if tradeoff_data.get('nstemi_stemi'):
            add_score('thrombotic', 'NSTEMI/STEMI', 1.82)
        if tradeoff_data.get('complex_pci'):
            add_score('bleeding', 'Complex PCI', 1.32)
            add_score('thrombotic', 'Complex PCI', 1.50)
        if tradeoff_data.get('bms_used'):
            add_score('thrombotic', 'BMS Used', 1.53)
        if tradeoff_data.get('copd'):
            add_score('bleeding', 'COPD', 1.39)
        if tradeoff_data.get('oac_discharge'):
            add_score('bleeding', 'OAC at Discharge', 2.00)
        
        # Convert HR scores to probabilities
        bleeding_prob = cls.convert_hr_to_probability(bleeding_score_hr, baseline_bleeding_rate)
        thrombotic_prob = cls.convert_hr_to_probability(thrombotic_score_hr, baseline_thrombotic_rate)
        
        return {
            "bleeding_score": bleeding_prob,
            "thrombotic_score": thrombotic_prob,
            "bleeding_factors": bleeding_factors,
            "thrombotic_factors": thrombotic_factors
        }
    
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
        # Get baseline rates from configuration
        tradeoff_config = config_loader.get_tradeoff_config()
        baseline_rates = tradeoff_config.get('baseline_event_rates', {})
        baseline_bleeding_rate = baseline_rates.get('bleeding_rate_percent', 2.5)
        baseline_thrombotic_rate = baseline_rates.get('thrombotic_rate_percent', 2.5)
        
        bleeding_score_hr = 1.0
        thrombotic_score_hr = 1.0
        
        bleeding_factors_details = []
        thrombotic_factors_details = []
        
        # Calculate bleeding score
        for predictor in model_predictors['bleedingEvents']['predictors']:
            factor_key = predictor['factor']
            if active_factors.get(factor_key, False):
                bleeding_score_hr *= predictor['hazardRatio']
                bleeding_factors_details.append(
                    f"{predictor['description']} (HR: {predictor['hazardRatio']})"
                )
        
        # Calculate thrombotic score
        for predictor in model_predictors['thromboticEvents']['predictors']:
            factor_key = predictor['factor']
            if active_factors.get(factor_key, False):
                thrombotic_score_hr *= predictor['hazardRatio']
                thrombotic_factors_details.append(
                    f"{predictor['description']} (HR: {predictor['hazardRatio']})"
                )
        
        # Convert to probabilities
        bleeding_prob = cls.convert_hr_to_probability(bleeding_score_hr, baseline_bleeding_rate)
        thrombotic_prob = cls.convert_hr_to_probability(thrombotic_score_hr, baseline_thrombotic_rate)
        
        return {
            "bleeding_score": bleeding_prob,
            "thrombotic_score": thrombotic_prob,
            "bleeding_factors": bleeding_factors_details,
            "thrombotic_factors": thrombotic_factors_details
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
    return tradeoff_calculator.detect_tradeoff_factors(raw_data, demographics, tradeoff_data)


def calculate_tradeoff_scores(raw_data, demographics, tradeoff_data):
    """Legacy function - calls the new service"""
    return tradeoff_calculator.calculate_tradeoff_scores(raw_data, demographics, tradeoff_data)


def calculate_tradeoff_scores_interactive(model_predictors, active_factors):
    """Legacy function - calls the new service"""
    return tradeoff_calculator.calculate_tradeoff_scores_interactive(model_predictors, active_factors)

