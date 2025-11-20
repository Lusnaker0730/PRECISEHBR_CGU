"""
PRECISE-HBR Calculator Service
Calculates PRECISE-HBR bleeding risk score
"""
import logging
from services.unit_conversion_service import unit_converter
from services.condition_checker import condition_checker


class PreciseHBRCalculator:
    """Calculator for PRECISE-HBR bleeding risk score"""
    
    # Truncation limits for effective values
    MIN_AGE, MAX_AGE = 30, 80
    MIN_HB, MAX_HB = 5.0, 15.0
    MIN_EGFR, MAX_EGFR = 5, 100
    MAX_WBC = 15.0
    
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
    def _calculate_age_score(cls, demographics):
        """Calculate age score component"""
        age = demographics.get('age')
        if not age:
            return {
                "parameter": "PRECISE-HBR - Age",
                "value": "Unknown",
                "score": 0,
                "raw_value": None,
                "date": "N/A",
                "description": "Age not available"
            }, 0
        
        effective_age = max(cls.MIN_AGE, min(cls.MAX_AGE, age))
        
        if effective_age > 30:
            age_score_raw = (effective_age - 30) * 0.25
            age_score = round(age_score_raw)
            logging.info(f"Age score: ({effective_age} - 30) × 0.25 = {age_score_raw:.2f}")
        else:
            age_score_raw = 0
            age_score = 0
        
        return {
            "parameter": "PRECISE-HBR - Age",
            "value": f"{age} years (effective: {effective_age})" if age != effective_age else f"{age} years",
            "score": age_score,
            "raw_value": age,
            "date": "N/A",
            "description": f"Age score: ({effective_age} - 30) × 0.25 = {age_score}" if effective_age > 30 
                          else f"Age {effective_age} ≤ 30, score = 0"
        }, age_score_raw
    
    @classmethod
    def _calculate_hemoglobin_score(cls, raw_data):
        """Calculate hemoglobin score component"""
        hemoglobin_list = raw_data.get('HEMOGLOBIN', [])
        if not hemoglobin_list:
            return {
                "parameter": "PRECISE-HBR - Hemoglobin",
                "value": "Not available",
                "score": 0,
                "raw_value": None,
                "date": "N/A",
                "description": "Hemoglobin not available"
            }, 0
        
        hb_obs = hemoglobin_list[0]
        hb_val = unit_converter.get_value_from_observation(
            hb_obs, 
            unit_converter.TARGET_UNITS['HEMOGLOBIN']
        )
        
        if not hb_val:
            return {
                "parameter": "PRECISE-HBR - Hemoglobin",
                "value": "Not available",
                "score": 0,
                "raw_value": None,
                "date": "N/A",
                "description": "Hemoglobin not available"
            }, 0
        
        hb_unit = unit_converter.TARGET_UNITS['HEMOGLOBIN']['unit']
        hb_date = hb_obs.get('effectiveDateTime', 'N/A')
        effective_hb = max(cls.MIN_HB, min(cls.MAX_HB, hb_val))
        
        if effective_hb < 15:
            hb_score_raw = (15 - effective_hb) * 2.5
            hb_score = round(hb_score_raw)
            logging.info(f"Hemoglobin score: (15 - {effective_hb}) × 2.5 = {hb_score_raw:.2f}")
        else:
            hb_score_raw = 0
            hb_score = 0
        
        return {
            "parameter": "PRECISE-HBR - Hemoglobin",
            "value": f"{hb_val} {hb_unit} (effective: {effective_hb})" if hb_val != effective_hb 
                    else f"{hb_val} {hb_unit}",
            "score": hb_score,
            "raw_value": hb_val,
            "date": hb_date,
            "description": f"Hemoglobin score: (15 - {effective_hb}) × 2.5 = {hb_score}" if effective_hb < 15 
                          else f"Hb {effective_hb} ≥ 15, score = 0"
        }, hb_score_raw
    
    @classmethod
    def _calculate_egfr_score(cls, raw_data, demographics):
        """Calculate eGFR score component"""
        egfr_list = raw_data.get('EGFR', [])
        creatinine_list = raw_data.get('CREATININE', [])
        
        egfr_val = None
        egfr_source = ""
        egfr_date = "N/A"
        
        # Try direct eGFR first
        if egfr_list:
            egfr_obs = egfr_list[0]
            egfr_val = unit_converter.get_value_from_observation(
                egfr_obs, 
                unit_converter.TARGET_UNITS['EGFR']
            )
            egfr_source = "Direct eGFR"
            egfr_date = egfr_obs.get('effectiveDateTime', 'N/A')
        
        # Calculate from creatinine if needed
        elif creatinine_list and demographics.get('age') and demographics.get('gender'):
            creatinine_obs = creatinine_list[0]
            creatinine_val = unit_converter.get_value_from_observation(
                creatinine_obs, 
                unit_converter.TARGET_UNITS['CREATININE']
            )
            if creatinine_val:
                calculated_egfr, reason = unit_converter.calculate_egfr(
                    creatinine_val, 
                    demographics['age'], 
                    demographics['gender']
                )
                if calculated_egfr:
                    egfr_val = calculated_egfr
                    egfr_source = reason
                    egfr_date = creatinine_obs.get('effectiveDateTime', 'N/A')
        
        if not egfr_val:
            return {
                "parameter": "PRECISE-HBR - eGFR",
                "value": "Not available",
                "score": 0,
                "raw_value": None,
                "date": "N/A",
                "description": "eGFR not available"
            }, 0
        
        effective_egfr = max(cls.MIN_EGFR, min(cls.MAX_EGFR, egfr_val))
        
        if effective_egfr < 100:
            egfr_score_raw = (100 - effective_egfr) * 0.05
            egfr_score = round(egfr_score_raw)
            logging.info(f"eGFR score: (100 - {effective_egfr}) × 0.05 = {egfr_score_raw:.2f}")
        else:
            egfr_score_raw = 0
            egfr_score = 0
        
        return {
            "parameter": "PRECISE-HBR - eGFR",
            "value": f"{egfr_val} mL/min/1.73m² (effective: {effective_egfr}) ({egfr_source})" 
                    if egfr_val != effective_egfr 
                    else f"{egfr_val} mL/min/1.73m² ({egfr_source})",
            "score": egfr_score,
            "raw_value": egfr_val,
            "date": egfr_date,
            "description": f"eGFR score: (100 - {effective_egfr}) × 0.05 = {egfr_score}" if effective_egfr < 100 
                          else f"eGFR {effective_egfr} ≥ 100, score = 0"
        }, egfr_score_raw
    
    @classmethod
    def _calculate_wbc_score(cls, raw_data):
        """Calculate WBC score component"""
        wbc_list = raw_data.get('WBC', [])
        if not wbc_list:
            return {
                "parameter": "PRECISE-HBR - White Blood Cell Count",
                "value": "Not available",
                "score": 0,
                "raw_value": None,
                "date": "N/A",
                "description": "WBC count not available"
            }, 0
        
        wbc_obs = wbc_list[0]
        wbc_val = unit_converter.get_value_from_observation(
            wbc_obs, 
            unit_converter.TARGET_UNITS['WBC']
        )
        
        if not wbc_val:
            return {
                "parameter": "PRECISE-HBR - White Blood Cell Count",
                "value": "Not available",
                "score": 0,
                "raw_value": None,
                "date": "N/A",
                "description": "WBC count not available"
            }, 0
        
        wbc_unit = unit_converter.TARGET_UNITS['WBC']['unit']
        wbc_date = wbc_obs.get('effectiveDateTime', 'N/A')
        effective_wbc = min(cls.MAX_WBC, wbc_val)
        
        if effective_wbc > 3.0:
            wbc_score_raw = (effective_wbc - 3.0) * 0.8
            wbc_score = round(wbc_score_raw)
            logging.info(f"WBC score: ({effective_wbc} - 3.0) × 0.8 = {wbc_score_raw:.2f}")
        else:
            wbc_score_raw = 0
            wbc_score = 0
        
        return {
            "parameter": "PRECISE-HBR - White Blood Cell Count",
            "value": f"{wbc_val} {wbc_unit} (effective: {effective_wbc})" if wbc_val != effective_wbc 
                    else f"{wbc_val} {wbc_unit}",
            "score": wbc_score,
            "raw_value": wbc_val,
            "date": wbc_date,
            "description": f"WBC score: ({effective_wbc} - 3.0) × 0.8 = {wbc_score}" if effective_wbc > 3.0 
                          else f"WBC {effective_wbc} ≤ 3.0, score = 0"
        }, wbc_score_raw
    
    @classmethod
    def _calculate_bleeding_history_score(cls, raw_data):
        """Calculate prior bleeding history score"""
        conditions = raw_data.get('conditions', [])
        has_bleeding, bleeding_evidence = condition_checker.check_prior_bleeding(conditions)
        
        bleeding_score = 7 if has_bleeding else 0
        logging.info(f"Previous bleeding score: {'Yes' if has_bleeding else 'No'} = {bleeding_score} points")
        
        return {
            "parameter": "PRECISE-HBR - Prior Bleeding",
            "value": "Yes" if has_bleeding else "No",
            "score": bleeding_score,
            "is_present": has_bleeding,
            "date": "N/A",
            "description": f"Previous bleeding: {'Yes' if has_bleeding else 'No'} = {bleeding_score} points. "
                          f"Found: {', '.join(bleeding_evidence) if bleeding_evidence else 'None detected'}"
        }, bleeding_score
    
    @classmethod
    def _calculate_anticoagulation_score(cls, raw_data):
        """Calculate oral anticoagulation score"""
        medications = raw_data.get('med_requests', [])
        has_anticoagulation = condition_checker.check_oral_anticoagulation(medications)
        
        anticoag_score = 5 if has_anticoagulation else 0
        logging.info(f"Oral anticoagulation score: {'Yes' if has_anticoagulation else 'No'} = {anticoag_score} points")
        
        return {
            "parameter": "PRECISE-HBR - Oral Anticoagulation",
            "value": "Yes" if has_anticoagulation else "No",
            "score": anticoag_score,
            "is_present": has_anticoagulation,
            "date": "N/A",
            "description": f"Long-term oral anticoagulation: {'Yes' if has_anticoagulation else 'No'} = {anticoag_score} points"
        }, anticoag_score
    
    @classmethod
    def _calculate_arc_hbr_score(cls, raw_data):
        """Calculate ARC-HBR factors score and components"""
        medications = raw_data.get('med_requests', [])
        arc_hbr_details = condition_checker.check_arc_hbr_factors_detailed(raw_data, medications)
        has_arc_factors = arc_hbr_details['has_any_factor']
        
        arc_hbr_score = 3 if has_arc_factors else 0
        logging.info(f"ARC-HBR conditions score: {'Yes' if has_arc_factors else 'No'} = {arc_hbr_score} points")
        
        components = []
        
        # Individual ARC-HBR elements
        components.append({
            "parameter": "PRECISE-HBR - Platelet Count",
            "value": "Yes" if arc_hbr_details['thrombocytopenia'] else "No",
            "score": 0,
            "is_present": arc_hbr_details['thrombocytopenia'],
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Platelet count <100 ×10⁹/L"
        })
        
        components.append({
            "parameter": "PRECISE-HBR - Chronic Bleeding Diathesis",
            "value": "Yes" if arc_hbr_details['bleeding_diathesis'] else "No",
            "score": 0,
            "is_present": arc_hbr_details['bleeding_diathesis'],
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Chronic bleeding diathesis"
        })
        
        components.append({
            "parameter": "PRECISE-HBR - Liver Cirrhosis",
            "value": "Yes" if arc_hbr_details['liver_cirrhosis'] else "No",
            "score": 0,
            "is_present": arc_hbr_details['liver_cirrhosis'],
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Liver cirrhosis with portal hypertension"
        })
        
        components.append({
            "parameter": "PRECISE-HBR - Active Malignancy",
            "value": "Yes" if arc_hbr_details['active_malignancy'] else "No",
            "score": 0,
            "is_present": arc_hbr_details['active_malignancy'],
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Active malignancy"
        })
        
        components.append({
            "parameter": "PRECISE-HBR - NSAIDs/Corticosteroids",
            "value": "Yes" if arc_hbr_details['nsaids_corticosteroids'] else "No",
            "score": 0,
            "is_present": arc_hbr_details['nsaids_corticosteroids'],
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Chronic use of nsaids or corticosteroids"
        })
        
        # Summary component
        arc_hbr_count = sum([
            arc_hbr_details['thrombocytopenia'],
            arc_hbr_details['bleeding_diathesis'],
            arc_hbr_details['liver_cirrhosis'],
            arc_hbr_details['active_malignancy'],
            arc_hbr_details['nsaids_corticosteroids']
        ])
        
        components.append({
            "parameter": "PRECISE-HBR - ARC-HBR Summary",
            "value": f"{arc_hbr_count} factor(s) present" if has_arc_factors else "None detected",
            "score": arc_hbr_score,
            "is_present": has_arc_factors,
            "date": "N/A",
            "description": f"ARC-HBR Elements ≥1: {'Yes' if has_arc_factors else 'No'} = {arc_hbr_score} points"
        })
        
        return components, arc_hbr_score


# Global instance
precise_hbr_calculator = PreciseHBRCalculator()


# Legacy function for backward compatibility
def calculate_precise_hbr_score(raw_data, demographics):
    """Legacy function - calls the new calculator service"""
    return precise_hbr_calculator.calculate_score(raw_data, demographics)


def calculate_risk_components(raw_data, demographics):
    """Legacy function - calls PRECISE-HBR calculator"""
    return precise_hbr_calculator.calculate_score(raw_data, demographics)

