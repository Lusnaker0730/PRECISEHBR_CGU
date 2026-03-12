"""
PRECISE-HBR Calculator Service
Calculates PRECISE-HBR bleeding risk score

All scoring coefficients and truncation limits are loaded from cdss_config.json for maintainability.
"""
import logging
import math
from services.unit_conversion_service import unit_converter
from services.condition_checker import condition_checker
from services.config_loader import config_loader
from datetime import datetime, timedelta


class PreciseHBRCalculator:
    """Calculator for PRECISE-HBR bleeding risk score"""
    
    # Default truncation limits (used if config is missing)
    DEFAULT_MIN_AGE, DEFAULT_MAX_AGE = 30, 80
    DEFAULT_MIN_HB, DEFAULT_MAX_HB = 5.0, 15.0
    DEFAULT_MIN_EGFR, DEFAULT_MAX_EGFR = 5, 100
    DEFAULT_MIN_WBC, DEFAULT_MAX_WBC = 3.0, 15.0
    
    # Default scoring coefficients
    DEFAULT_BASE_SCORE = 2
    DEFAULT_AGE_THRESHOLD = 30
    DEFAULT_AGE_COEFFICIENT = 0.25
    DEFAULT_HB_THRESHOLD = 15.0
    DEFAULT_HB_COEFFICIENT = 2.5
    DEFAULT_EGFR_THRESHOLD = 100
    DEFAULT_EGFR_COEFFICIENT = 0.05
    DEFAULT_WBC_THRESHOLD = 3.0
    DEFAULT_WBC_COEFFICIENT = 0.8
    DEFAULT_BLEEDING_SCORE = 7
    DEFAULT_ANTICOAG_SCORE = 5
    DEFAULT_ARC_HBR_SCORE = 3

    @classmethod
    def _get_config_params(cls):
        """Get PRECISE-HBR parameters from config with fallback defaults."""
        params = config_loader.get_precise_hbr_params()
        return params if params else {}

    @classmethod
    def _get_truncation_limits(cls):
        """Get truncation limits from config."""
        params = cls._get_config_params()
        return {
            'min_age': params.get('age', {}).get('truncation_min', cls.DEFAULT_MIN_AGE),
            'max_age': params.get('age', {}).get('truncation_max', cls.DEFAULT_MAX_AGE),
            'min_hb': params.get('hemoglobin', {}).get('truncation_min', cls.DEFAULT_MIN_HB),
            'max_hb': params.get('hemoglobin', {}).get('truncation_max', cls.DEFAULT_MAX_HB),
            'min_egfr': params.get('egfr', {}).get('truncation_min', cls.DEFAULT_MIN_EGFR),
            'max_egfr': params.get('egfr', {}).get('truncation_max', cls.DEFAULT_MAX_EGFR),
            'min_wbc': params.get('white_blood_cell_count', {}).get('truncation_min', cls.DEFAULT_MIN_WBC),
            'max_wbc': params.get('white_blood_cell_count', {}).get('truncation_max', cls.DEFAULT_MAX_WBC),
        }

    @classmethod
    def _get_scoring_coefficients(cls):
        """Get scoring coefficients and thresholds from config."""
        params = cls._get_config_params()
        return {
            'base_score': params.get('base_score', cls.DEFAULT_BASE_SCORE),
            'age_threshold': params.get('age', {}).get('threshold', cls.DEFAULT_AGE_THRESHOLD),
            'age_coefficient': params.get('age', {}).get('coefficient', cls.DEFAULT_AGE_COEFFICIENT),
            'hb_threshold': params.get('hemoglobin', {}).get('threshold', cls.DEFAULT_HB_THRESHOLD),
            'hb_coefficient': params.get('hemoglobin', {}).get('coefficient', cls.DEFAULT_HB_COEFFICIENT),
            'egfr_threshold': params.get('egfr', {}).get('threshold', cls.DEFAULT_EGFR_THRESHOLD),
            'egfr_coefficient': params.get('egfr', {}).get('coefficient', cls.DEFAULT_EGFR_COEFFICIENT),
            'wbc_threshold': params.get('white_blood_cell_count', {}).get('threshold', cls.DEFAULT_WBC_THRESHOLD),
            'wbc_coefficient': params.get('white_blood_cell_count', {}).get('coefficient', cls.DEFAULT_WBC_COEFFICIENT),
            'bleeding_score': params.get('previous_bleeding', {}).get('score', cls.DEFAULT_BLEEDING_SCORE),
            'anticoag_score': params.get('oral_anticoagulation', {}).get('score', cls.DEFAULT_ANTICOAG_SCORE),
            'arc_hbr_score': params.get('arc_hbr_factors', {}).get('score', cls.DEFAULT_ARC_HBR_SCORE),
        }

    @staticmethod
    def _is_outdated(date_str):
        """Checks if the date is older than 3 months"""
        if not date_str or date_str == 'N/A':
            return False
            
        try:
            date_str = str(date_str).strip()
            
            if len(date_str) == 10 and '-' in date_str:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            elif 'T' in date_str:
                if date_str.endswith('Z'):
                    date_str = date_str[:-1] + '+00:00'
                dt = datetime.fromisoformat(date_str)
            else:
                return False
                
            if dt.tzinfo:
                now = datetime.now(dt.tzinfo)
            else:
                now = datetime.now()
                
            return (now - dt) > timedelta(days=90)
            
        except Exception as e:
            logging.warning(f"Error parsing date {date_str}: {e}")
            return False

    @classmethod
    def extract_inputs(cls, raw_data, demographics):
        """
        Extracts and normalizes inputs from FHIR data for PRECISE-HBR calculation.
        
        Args:
            raw_data: Dictionary with FHIR observation data
            demographics: Dictionary with patient demographics
            
        Returns:
            Dictionary of extracted inputs with metadata and missing field tracking
        """
        limits = cls._get_truncation_limits()
        
        inputs = {
            'age': None,
            'hb': None,
            'egfr': None,
            'wbc': None,
            'prior_bleeding': False,
            'oral_anticoag': False,
            'arc_hbr_count': 0,
            'missing_fields': [],
            'empty_fhir_resources': [],  # Track empty FHIR resource types
            'metadata': {}
        }
        
        # 1. Age
        age = demographics.get('age')
        if age is not None:
            inputs['age'] = age
            inputs['metadata']['age_effective'] = max(limits['min_age'], min(limits['max_age'], age))
        else:
            inputs['missing_fields'].append('Age')
            
        # 2. Hemoglobin
        hemoglobin_list = raw_data.get('HEMOGLOBIN', [])
        if hemoglobin_list:
            hb_obs = hemoglobin_list[0]
            hb_val = unit_converter.get_value_from_observation(hb_obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
            if hb_val is not None:
                inputs['hb'] = hb_val
                inputs['metadata']['hb_effective'] = max(limits['min_hb'], min(limits['max_hb'], hb_val))
                inputs['metadata']['hb_date'] = hb_obs.get('effectiveDateTime', 'N/A')
            else:
                inputs['missing_fields'].append('Hemoglobin')
        else:
            inputs['missing_fields'].append('Hemoglobin')
            
        # 3. eGFR
        egfr_val = None
        egfr_source = ""
        egfr_list = raw_data.get('EGFR', [])
        if egfr_list:
            egfr_obs = egfr_list[0]
            egfr_val = unit_converter.get_value_from_observation(egfr_obs, unit_converter.TARGET_UNITS['EGFR'])
            egfr_source = "Direct eGFR"
            inputs['metadata']['egfr_date'] = egfr_obs.get('effectiveDateTime', 'N/A')
            
        if egfr_val is None:
            creatinine_list = raw_data.get('CREATININE', [])
            if creatinine_list and inputs['age'] is not None and demographics.get('gender'):
                creatinine_obs = creatinine_list[0]
                creatinine_val = unit_converter.get_value_from_observation(creatinine_obs, unit_converter.TARGET_UNITS['CREATININE'])
                if creatinine_val:
                    calc_egfr, reason = unit_converter.calculate_egfr(creatinine_val, inputs['age'], demographics['gender'])
                    if calc_egfr:
                        egfr_val = calc_egfr
                        egfr_source = reason
                        inputs['metadata']['egfr_date'] = creatinine_obs.get('effectiveDateTime', 'N/A')
        
        if egfr_val is not None:
            inputs['egfr'] = egfr_val
            inputs['metadata']['egfr_effective'] = max(limits['min_egfr'], min(limits['max_egfr'], egfr_val))
            inputs['metadata']['egfr_source'] = egfr_source
        else:
            inputs['missing_fields'].append('eGFR')

        # 4. WBC
        wbc_list = raw_data.get('WBC', [])
        if wbc_list:
            wbc_obs = wbc_list[0]
            wbc_val = unit_converter.get_value_from_observation(wbc_obs, unit_converter.TARGET_UNITS['WBC'])
            if wbc_val is not None:
                inputs['wbc'] = wbc_val
                inputs['metadata']['wbc_effective'] = max(limits['min_wbc'], min(limits['max_wbc'], wbc_val))
                inputs['metadata']['wbc_date'] = wbc_obs.get('effectiveDateTime', 'N/A')
            else:
                inputs['missing_fields'].append('WBC')
        else:
            inputs['missing_fields'].append('WBC')

        # 5. Prior Bleeding
        conditions = raw_data.get('conditions', [])
        
        # Track if conditions list is empty (important for risk assessment)
        if not conditions:
            inputs['empty_fhir_resources'].append('Condition')
            inputs['metadata']['conditions_empty'] = True
        else:
            inputs['metadata']['conditions_empty'] = False
            inputs['metadata']['conditions_count'] = len(conditions)
        
        has_bleeding, evidence = condition_checker.check_prior_bleeding(conditions)
        inputs['prior_bleeding'] = has_bleeding
        inputs['metadata']['bleeding_evidence'] = evidence

        # 6. Oral Anticoagulation
        medications = raw_data.get('med_requests', [])
        
        # Track if medications list is empty (important for risk assessment)
        if not medications:
            inputs['empty_fhir_resources'].append('Medication')
            inputs['metadata']['medications_empty'] = True
        else:
            inputs['metadata']['medications_empty'] = False
            inputs['metadata']['medications_count'] = len(medications)
        
        has_anticoag = condition_checker.check_oral_anticoagulation(medications)
        inputs['oral_anticoag'] = has_anticoag

        # 7. ARC-HBR
        arc_details = condition_checker.check_arc_hbr_factors_detailed(raw_data, medications)
        inputs['arc_hbr_count'] = sum([
            arc_details['thrombocytopenia'], arc_details['bleeding_diathesis'],
            arc_details['liver_cirrhosis'], arc_details['active_malignancy'],
            arc_details['nsaids_corticosteroids'], arc_details.get('recent_major_surgery_trauma', False)
        ])
        inputs['metadata']['arc_details'] = arc_details
        
        return inputs

    @classmethod
    def calculate_pure_score(cls, inputs):
        """
        Calculates score from extracted inputs. 
        Only performs math. Does not handle IO or extractions.
        Uses coefficients from config.
        
        Args:
            inputs: Dictionary from extract_inputs
            
        Returns:
            Tuple (score, breakdown_dict)
        """
        coeffs = cls._get_scoring_coefficients()
        
        score = float(coeffs['base_score'])
        breakdown = {'base': coeffs['base_score']}
        
        # Age: (effective_age - threshold) × coefficient
        if inputs['age'] is not None:
            eff_age = inputs['metadata']['age_effective']
            if eff_age > coeffs['age_threshold']:
                s = (eff_age - coeffs['age_threshold']) * coeffs['age_coefficient']
                score += s
                breakdown['age'] = s
            else:
                breakdown['age'] = 0
        else:
            breakdown['age'] = 0

        # Hemoglobin: (threshold - effective_hb) × coefficient
        if inputs['hb'] is not None:
            eff_hb = inputs['metadata']['hb_effective']
            if eff_hb < coeffs['hb_threshold']:
                s = (coeffs['hb_threshold'] - eff_hb) * coeffs['hb_coefficient']
                score += s
                breakdown['hb'] = s
            else:
                breakdown['hb'] = 0
        else:
            breakdown['hb'] = 0

        # eGFR: (threshold - effective_egfr) × coefficient
        if inputs['egfr'] is not None:
            eff_egfr = inputs['metadata']['egfr_effective']
            if eff_egfr < coeffs['egfr_threshold']:
                s = (coeffs['egfr_threshold'] - eff_egfr) * coeffs['egfr_coefficient']
                score += s
                breakdown['egfr'] = s
            else:
                breakdown['egfr'] = 0
        else:
            breakdown['egfr'] = 0

        # WBC: (effective_wbc - threshold) × coefficient
        if inputs['wbc'] is not None:
            eff_wbc = inputs['metadata']['wbc_effective']
            if eff_wbc > coeffs['wbc_threshold']:
                s = (eff_wbc - coeffs['wbc_threshold']) * coeffs['wbc_coefficient']
                score += s
                breakdown['wbc'] = s
            else:
                breakdown['wbc'] = 0
        else:
            breakdown['wbc'] = 0

        # Binary Factors
        if inputs['prior_bleeding']:
            score += coeffs['bleeding_score']
            breakdown['bleeding'] = coeffs['bleeding_score']
        else:
            breakdown['bleeding'] = 0
            
        if inputs['oral_anticoag']:
            score += coeffs['anticoag_score']
            breakdown['anticoag'] = coeffs['anticoag_score']
        else:
            breakdown['anticoag'] = 0
            
        if inputs['arc_hbr_count'] > 0:
            score += coeffs['arc_hbr_score']
            breakdown['arc_hbr'] = coeffs['arc_hbr_score']
        else:
            breakdown['arc_hbr'] = 0
            
        return math.floor(score + 0.5), breakdown

    @classmethod
    def calculate_score(cls, raw_data, demographics):
        """
        Main entry point for PRECISE-HBR score calculation.
        Uses extract_inputs and calculate_pure_score.
        
        Returns:
            Tuple of (components_list, total_score)
        """
        inputs = cls.extract_inputs(raw_data, demographics)
        total_score, breakdown = cls.calculate_pure_score(inputs)
        
        # Reconstruct detailed components for UI
        components = []
        
        # Base
        components.append({
            "parameter": "PRECISE-HBR - Base Score",
            "value": "Fixed base score",
            "score": breakdown['base'],
            "date": "N/A",
            "description": f"Base score: {breakdown['base']} points (fixed)"
        })
        
        # Age
        if 'Age' in inputs['missing_fields']:
            components.append({
                "parameter": "PRECISE-HBR - Age",
                "value": "Unknown",
                "score": 0,
                "date": "N/A",
                "description": "Age not available"
            })
        else:
            age = inputs['age']
            eff_age = inputs['metadata']['age_effective']
            components.append({
                "parameter": "PRECISE-HBR - Age",
                "value": f"{age} years (effective: {eff_age})" if age != eff_age else f"{age} years",
                "score": math.floor(breakdown['age'] + 0.5),
                "raw_value": age,
                "date": "N/A",
                "description": f"Age score: {breakdown['age']:.2f}"
            })

        # Hemoglobin
        if 'Hemoglobin' in inputs['missing_fields']:
            components.append({
                "parameter": "PRECISE-HBR - Hemoglobin",
                "value": "Not available",
                "score": 0,
                "date": "N/A",
                "description": "Hemoglobin not available"
            })
        else:
            hb = inputs['hb']
            components.append({
                "parameter": "PRECISE-HBR - Hemoglobin",
                "value": f"{hb} g/dL",
                "score": math.floor(breakdown['hb'] + 0.5),
                "raw_value": hb,
                "date": inputs['metadata'].get('hb_date', 'N/A'),
                "is_outdated": cls._is_outdated(inputs['metadata'].get('hb_date', 'N/A')),
                "description": f"Hb score: {breakdown['hb']:.2f}"
            })
            
        # eGFR
        if 'eGFR' in inputs['missing_fields']:
            components.append({
                "parameter": "PRECISE-HBR - eGFR",
                "value": "Not available",
                "score": 0,
                "date": "N/A",
                "description": "eGFR not available"
            })
        else:
            egfr = inputs['egfr']
            components.append({
                "parameter": "PRECISE-HBR - eGFR",
                "value": f"{egfr} mL/min/1.73m²",
                "score": math.floor(breakdown['egfr'] + 0.5),
                "raw_value": egfr,
                "date": inputs['metadata'].get('egfr_date', 'N/A'),
                "is_outdated": cls._is_outdated(inputs['metadata'].get('egfr_date', 'N/A')),
                "description": f"eGFR score: {breakdown['egfr']:.2f}"
            })
            
        # WBC
        if 'WBC' in inputs['missing_fields']:
            components.append({
                "parameter": "PRECISE-HBR - White Blood Cell Count",
                "value": "Not available",
                "score": 0,
                "date": "N/A",
                "description": "WBC not available"
            })
        else:
            wbc = inputs['wbc']
            components.append({
                "parameter": "PRECISE-HBR - White Blood Cell Count",
                "value": f"{wbc} 10^9/L",
                "score": math.floor(breakdown['wbc'] + 0.5),
                "raw_value": wbc,
                "date": inputs['metadata'].get('wbc_date', 'N/A'),
                "is_outdated": cls._is_outdated(inputs['metadata'].get('wbc_date', 'N/A')),
                "description": f"WBC score: {breakdown['wbc']:.2f}"
            })
            
        # Bleeding
        components.append({
            "parameter": "PRECISE-HBR - Prior Bleeding",
            "value": "Yes" if inputs['prior_bleeding'] else "No",
            "score": breakdown['bleeding'],
            "is_present": inputs['prior_bleeding'],
            "description": f"Prior Bleeding: {breakdown['bleeding']}"
        })
        
        # Anticoag
        components.append({
            "parameter": "PRECISE-HBR - Oral Anticoagulation",
            "value": "Yes" if inputs['oral_anticoag'] else "No",
            "score": breakdown['anticoag'],
            "is_present": inputs['oral_anticoag'],
            "description": f"Anticoagulation: {breakdown['anticoag']}"
        })
        
        # ARC-HBR Details
        arc_details = inputs['metadata'].get('arc_details', {})
        
        components.append({
            "parameter": "PRECISE-HBR - Platelet Count",
            "value": "Yes" if arc_details.get('thrombocytopenia') else "No",
            "score": 0,
            "is_present": arc_details.get('thrombocytopenia', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Platelet count < 100x10^9/L"
        })
        
        components.append({
            "parameter": "PRECISE-HBR - Chronic Bleeding Diathesis",
            "value": "Yes" if arc_details.get('bleeding_diathesis') else "No",
            "score": 0,
            "is_present": arc_details.get('bleeding_diathesis', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "History of chronic bleeding diathesis"
        })
        
        components.append({
            "parameter": "PRECISE-HBR - Liver Cirrhosis",
            "value": "Yes" if arc_details.get('liver_cirrhosis') else "No",
            "score": 0,
            "is_present": arc_details.get('liver_cirrhosis', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Liver cirrhosis with portal hypertension"
        })
        
        components.append({
            "parameter": "PRECISE-HBR - Active Malignancy",
            "value": "Yes" if arc_details.get('active_malignancy') else "No",
            "score": 0,
            "is_present": arc_details.get('active_malignancy', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Active malignancy in past 12 months"
        })

        components.append({
            "parameter": "PRECISE-HBR - NSAIDs/Corticosteroids",
            "value": "Yes" if arc_details.get('nsaids_corticosteroids') else "No",
            "score": 0,
            "is_present": arc_details.get('nsaids_corticosteroids', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Chronic use of NSAIDs or corticosteroids"
        })

        components.append({
            "parameter": "PRECISE-HBR - Recent Major Surgery or Trauma",
            "value": "Yes" if arc_details.get('recent_major_surgery_trauma') else "No",
            "score": 0,
            "is_present": arc_details.get('recent_major_surgery_trauma', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Recent major surgery or trauma"
        })

        components.append({
            "parameter": "PRECISE-HBR - ARC-HBR Summary",
            "value": f"{inputs['arc_hbr_count']} factor(s)",
            "score": breakdown['arc_hbr'],
            "is_present": inputs['arc_hbr_count'] > 0,
            "description": f"ARC-HBR: {breakdown['arc_hbr']}"
        })

        # Build data warnings for missing FHIR resources
        data_warnings = []
        empty_resources = inputs.get('empty_fhir_resources', [])
        
        if 'Condition' in empty_resources:
            data_warnings.append({
                'type': 'missing_fhir_resource',
                'resource': 'Condition',
                'message': 'No Condition records found - Prior Bleeding History and ARC-HBR factors (bleeding diathesis, liver cirrhosis, active malignancy, recent major surgery or trauma) may be missed.',
                'affected_factors': ['Prior Bleeding', 'Bleeding Diathesis', 'Liver Cirrhosis', 'Active Malignancy', 'Recent Major Surgery or Trauma']
            })
        
        if 'Medication' in empty_resources:
            data_warnings.append({
                'type': 'missing_fhir_resource',
                'resource': 'Medication',
                'message': 'No Medication records found - Oral Anticoagulation status and NSAID/Corticosteroid use may be inaccurate.',
                'affected_factors': ['Oral Anticoagulation', 'NSAIDs/Corticosteroids']
            })

        logging.info(f"PRECISE-HBR calculation complete: {total_score}")
        if data_warnings:
            logging.warning(f"Data warnings: {[w['resource'] for w in data_warnings]} resources empty")
        
        return components, total_score, data_warnings


# Global instance
precise_hbr_calculator = PreciseHBRCalculator()


# Legacy functions for backward compatibility
def calculate_precise_hbr_score(raw_data, demographics):
    """Legacy function - calls the new calculator service"""
    return precise_hbr_calculator.calculate_score(raw_data, demographics)


def calculate_risk_components(raw_data, demographics):
    """Legacy function - calls PRECISE-HBR calculator"""
    return precise_hbr_calculator.calculate_score(raw_data, demographics)


def get_calculator_inputs(raw_data, demographics):
    """Utility to get inputs and check missing fields directly"""
    return precise_hbr_calculator.extract_inputs(raw_data, demographics)
