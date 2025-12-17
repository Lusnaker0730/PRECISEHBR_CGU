"""
PRECISE-HBR Calculator Service
Calculates PRECISE-HBR bleeding risk score
"""
import logging
from services.unit_conversion_service import unit_converter
from services.condition_checker import condition_checker
from datetime import datetime, timedelta
import re


class PreciseHBRCalculator:
    """Calculator for PRECISE-HBR bleeding risk score"""
    
    # Truncation limits for effective values
    MIN_AGE, MAX_AGE = 30, 80
    MIN_HB, MAX_HB = 5.0, 15.0
    MIN_EGFR, MAX_EGFR = 5, 100
    MAX_WBC = 15.0
    
    @staticmethod
    def _is_outdated(date_str):
        """Checks if the date is older than 3 months"""
        if not date_str or date_str == 'N/A':
            return False
            
        try:
            # Clean up date string
            date_str = str(date_str).strip()
            
            # Handle pure date "YYYY-MM-DD"
            if len(date_str) == 10 and '-' in date_str:
                 dt = datetime.strptime(date_str, "%Y-%m-%d")
            # Handle ISO format
            elif 'T' in date_str:
                # Simple truncation to seconds/handling Z
                # Replace Z with +00:00 for fromisoformat compatibility
                if date_str.endswith('Z'):
                    date_str = date_str[:-1] + '+00:00'
                dt = datetime.fromisoformat(date_str)
            else:
                return False
                
            # Compare with 3 months ago (90 days)
            # Handle timezone awareness
            if dt.tzinfo:
                now = datetime.now(dt.tzinfo)
            else:
                now = datetime.now()
                
            return (now - dt) > timedelta(days=90)
            
        except Exception as e:
            logging.warning(f"Error parsing date {date_str}: {e}")
            return False

    @classmethod
    def calculate_score(cls, raw_data, demographics):
        """
        Calculates PRECISE-HBR bleeding risk score using V5.0 methodology.
        
        Calculation Steps:
        1. Base score: Start with 2 points
        2. Add continuous variable scores (age, Hb, eGFR, WBC)
        3. Add categorical variable scores (bleeding history, anticoagulation, ARC-HBR)
        4. Round total to nearest integer
        
        Args:
            raw_data: Dictionary with FHIR observation data
            demographics: Dictionary with patient demographics
        
        Returns:
            Tuple of (components_list, total_score)
        """
        components = []
        base_score = 2
        total_score = base_score
        
        # Add base score component
        components.append({
            "parameter": "PRECISE-HBR - Base Score",
            "value": "Fixed base score",
            "score": base_score,
            "date": "N/A",
            "description": f"Base score: {base_score} points (fixed)"
        })
        
        # 1. Age Score
        age_component, age_score = cls._calculate_age_score(demographics)
        components.append(age_component)
        total_score += age_score
        
        # 2. Hemoglobin Score
        hb_component, hb_score = cls._calculate_hemoglobin_score(raw_data)
        components.append(hb_component)
        total_score += hb_score
        
        # 3. eGFR Score
        egfr_component, egfr_score = cls._calculate_egfr_score(raw_data, demographics)
        components.append(egfr_component)
        total_score += egfr_score
        
        # 4. WBC Score
        wbc_component, wbc_score = cls._calculate_wbc_score(raw_data)
        components.append(wbc_component)
        total_score += wbc_score
        
        # 5. Prior Bleeding History
        bleeding_component, bleeding_score = cls._calculate_bleeding_history_score(raw_data)
        components.append(bleeding_component)
        total_score += bleeding_score
        
        # 6. Oral Anticoagulation
        anticoag_component, anticoag_score = cls._calculate_anticoagulation_score(raw_data)
        components.append(anticoag_component)
        total_score += anticoag_score
        
        # 7. ARC-HBR Factors
        arc_components, arc_score = cls._calculate_arc_hbr_score(raw_data)
        components.extend(arc_components)
        total_score += arc_score
        
        # Round final score
        final_score = round(total_score)
        
        logging.info(f"PRECISE-HBR V5.0 calculation complete: {final_score}")
        
        return components, final_score
    
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
        inputs = {
            'age': None,
            'hb': None,
            'egfr': None,
            'wbc': None,
            'prior_bleeding': False,
            'oral_anticoag': False,
            'arc_hbr_count': 0,
            'missing_fields': [],
            'metadata': {}
        }
        
        # 1. Age
        age = demographics.get('age')
        if age is not None:
            inputs['age'] = age
            inputs['metadata']['age_effective'] = max(cls.MIN_AGE, min(cls.MAX_AGE, age))
        else:
            inputs['missing_fields'].append('Age')
            
        # 2. Hemoglobin
        hemoglobin_list = raw_data.get('HEMOGLOBIN', [])
        if hemoglobin_list:
            hb_obs = hemoglobin_list[0]
            hb_val = unit_converter.get_value_from_observation(hb_obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
            if hb_val is not None:
                inputs['hb'] = hb_val
                inputs['metadata']['hb_effective'] = max(cls.MIN_HB, min(cls.MAX_HB, hb_val))
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
            inputs['metadata']['egfr_effective'] = max(cls.MIN_EGFR, min(cls.MAX_EGFR, egfr_val))
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
                inputs['metadata']['wbc_effective'] = min(cls.MAX_WBC, wbc_val)
                inputs['metadata']['wbc_date'] = wbc_obs.get('effectiveDateTime', 'N/A')
            else:
                inputs['missing_fields'].append('WBC')
        else:
            inputs['missing_fields'].append('WBC')

        # 5. Prior Bleeding
        conditions = raw_data.get('conditions', [])
        has_bleeding, evidence = condition_checker.check_prior_bleeding(conditions)
        inputs['prior_bleeding'] = has_bleeding
        inputs['metadata']['bleeding_evidence'] = evidence

        # 6. Oral Anticoagulation
        medications = raw_data.get('med_requests', [])
        has_anticoag = condition_checker.check_oral_anticoagulation(medications)
        inputs['oral_anticoag'] = has_anticoag

        # 7. ARC-HBR
        arc_details = condition_checker.check_arc_hbr_factors_detailed(raw_data, medications)
        inputs['arc_hbr_count'] = sum([
            arc_details['thrombocytopenia'], arc_details['bleeding_diathesis'],
            arc_details['liver_cirrhosis'], arc_details['active_malignancy'],
            arc_details['nsaids_corticosteroids']
        ])
        inputs['metadata']['arc_details'] = arc_details
        
        return inputs

    @classmethod
    def calculate_pure_score(cls, inputs):
        """
        Calculates score from extracted inputs. 
        Only performs math. Does not handle IO or extractions.
        
        Args:
            inputs: Dictionary from extract_inputs
            
        Returns:
            Tuple (score, breakdown_dict)
        """
        score = 2.0 # Base score
        breakdown = {'base': 2.0}
        
        # Age
        if inputs['age'] is not None:
            eff_age = inputs['metadata']['age_effective']
            if eff_age > 30:
                s = (eff_age - 30) * 0.25
                score += s
                breakdown['age'] = s
            else:
                breakdown['age'] = 0
        else:
            breakdown['age'] = 0

        # Hb
        if inputs['hb'] is not None:
            eff_hb = inputs['metadata']['hb_effective']
            if eff_hb < 15:
                s = (15 - eff_hb) * 2.5
                score += s
                breakdown['hb'] = s
            else:
                breakdown['hb'] = 0
        else:
            breakdown['hb'] = 0

        # eGFR
        if inputs['egfr'] is not None:
            eff_egfr = inputs['metadata']['egfr_effective']
            if eff_egfr < 100:
                s = (100 - eff_egfr) * 0.05
                score += s
                breakdown['egfr'] = s
            else:
                breakdown['egfr'] = 0
        else:
            breakdown['egfr'] = 0

        # WBC
        if inputs['wbc'] is not None:
            eff_wbc = inputs['metadata']['wbc_effective']
            if eff_wbc > 3.0:
                s = (eff_wbc - 3.0) * 0.8
                score += s
                breakdown['wbc'] = s
            else:
                breakdown['wbc'] = 0
        else:
            breakdown['wbc'] = 0

        # Binary Factors
        if inputs['prior_bleeding']:
            score += 7
            breakdown['bleeding'] = 7
        else:
            breakdown['bleeding'] = 0
            
        if inputs['oral_anticoag']:
            score += 5
            breakdown['anticoag'] = 5
        else:
            breakdown['anticoag'] = 0
            
        if inputs['arc_hbr_count'] > 0:
            score += 3
            breakdown['arc_hbr'] = 3
        else:
            breakdown['arc_hbr'] = 0
            
        return round(score), breakdown

    @classmethod
    def calculate_score(cls, raw_data, demographics):
        """
        Orchestrator for calculation. Uses extract_inputs and calculate_pure_score.
        Maintains legacy return format but adds missing data handling potential.
        
        Returns:
            Tuple of (components_list, total_score, missing_fields)
            Note: Legacy callers might only unpack 2 values, so we might need to remain backward compatible
            or update callers if we change return signature.
            Strategy: Return (components, score) as before, but embed missing info in components or logs.
            Updating to Component-based return to match existing UI needs.
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
                "parameter": "PRECISE-HBR - Age", "value": "Unknown", "score": 0, "date": "N/A", "description": "Age not available"
            })
        else:
            age = inputs['age']
            eff_age = inputs['metadata']['age_effective']
            components.append({
                "parameter": "PRECISE-HBR - Age",
                "value": f"{age} years (effective: {eff_age})" if age != eff_age else f"{age} years",
                "score": round(breakdown['age']), # UI expects integer-like
                "raw_value": age,
                "date": "N/A",
                "description": f"Age score: {breakdown['age']:.2f}"
            })

        # Hemoglobin
        if 'Hemoglobin' in inputs['missing_fields']:
             components.append({
                "parameter": "PRECISE-HBR - Hemoglobin", "value": "Not available", "score": 0, "date": "N/A", "description": "Hemoglobin not available"
            })
        else:
            hb = inputs['hb']
            eff_hb = inputs['metadata']['hb_effective']
            components.append({
                "parameter": "PRECISE-HBR - Hemoglobin",
                "value": f"{hb} g/dL",
                "score": round(breakdown['hb']),
                "raw_value": hb,
                "raw_value": hb,
                "date": inputs['metadata'].get('hb_date', 'N/A'),
                "is_outdated": cls._is_outdated(inputs['metadata'].get('hb_date', 'N/A')),
                "description": f"Hb score: {breakdown['hb']:.2f}"
            })
            
        # eGFR
        if 'eGFR' in inputs['missing_fields']:
             components.append({
                "parameter": "PRECISE-HBR - eGFR", "value": "Not available", "score": 0, "date": "N/A", "description": "eGFR not available"
            })
        else:
            egfr = inputs['egfr']
            eff_egfr = inputs['metadata']['egfr_effective']
            components.append({
                "parameter": "PRECISE-HBR - eGFR",
                "value": f"{egfr} mL/min/1.73m²",
                "score": round(breakdown['egfr']),
                "raw_value": egfr,
                "raw_value": egfr,
                "date": inputs['metadata'].get('egfr_date', 'N/A'), 
                "is_outdated": cls._is_outdated(inputs['metadata'].get('egfr_date', 'N/A')),
                "description": f"eGFR score: {breakdown['egfr']:.2f}"
            })
            
        # WBC
        if 'WBC' in inputs['missing_fields']:
             components.append({
                "parameter": "PRECISE-HBR - White Blood Cell Count", "value": "Not available", "score": 0, "date": "N/A", "description": "WBC not available"
            })
        else:
            wbc = inputs['wbc']
            components.append({
                "parameter": "PRECISE-HBR - White Blood Cell Count",
                "value": f"{wbc} 10^9/L",
                "score": round(breakdown['wbc']),
                "raw_value": wbc,
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
        
        # ARC Summary and Details
        arc_details = inputs['metadata'].get('arc_details', {})
        
        # Add detailed ARC-HBR components (hidden from score sum but visible in UI)
        # 1. Thrombocytopenia
        components.append({
            "parameter": "PRECISE-HBR - Platelet Count",
            "value": "Yes" if arc_details.get('thrombocytopenia') else "No",
            "score": 0,
            "is_present": arc_details.get('thrombocytopenia', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Platelet count < 100x10^9/L"
        })
        
        # 2. Bleeding Diathesis
        components.append({
            "parameter": "PRECISE-HBR - Chronic Bleeding Diathesis",
            "value": "Yes" if arc_details.get('bleeding_diathesis') else "No",
            "score": 0,
            "is_present": arc_details.get('bleeding_diathesis', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "History of chronic bleeding diathesis"
        })
        
        # 3. Liver Cirrhosis
        components.append({
            "parameter": "PRECISE-HBR - Liver Cirrhosis",
            "value": "Yes" if arc_details.get('liver_cirrhosis') else "No",
            "score": 0,
            "is_present": arc_details.get('liver_cirrhosis', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Liver cirrhosis with portal hypertension"
        })
        
        # 4. Active Malignancy
        components.append({
            "parameter": "PRECISE-HBR - Active Malignancy",
            "value": "Yes" if arc_details.get('active_malignancy') else "No",
            "score": 0,
            "is_present": arc_details.get('active_malignancy', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Active malignancy in past 12 months"
        })

        # 5. NSAIDs/Corticosteroids (replaces recent surgery in general ARC lists but specific to this implementation?)
        # Checking extract_inputs logic... mapped from 'nsaids_corticosteroids'
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
            "parameter": "PRECISE-HBR - ARC-HBR Summary",
            "value": f"{inputs['arc_hbr_count']} factor(s)",
            "score": breakdown['arc_hbr'],
            "is_present": inputs['arc_hbr_count'] > 0,
            "description": f"ARC-HBR: {breakdown['arc_hbr']}"
        })

        return components, total_score


# Global instance
precise_hbr_calculator = PreciseHBRCalculator()


# Legacy function for backward compatibility
def calculate_precise_hbr_score(raw_data, demographics):
    """Legacy function - calls the new calculator service"""
    return precise_hbr_calculator.calculate_score(raw_data, demographics)


def calculate_risk_components(raw_data, demographics):
    """Legacy function - calls PRECISE-HBR calculator"""
    return precise_hbr_calculator.calculate_score(raw_data, demographics)

def get_calculator_inputs(raw_data, demographics):
    """New utility to get inputs and check missing fields directly"""
    return precise_hbr_calculator.extract_inputs(raw_data, demographics)

