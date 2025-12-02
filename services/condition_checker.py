"""
Condition Checker Service
Handles checking for specific medical conditions in patient data
Supports SNOMED CT, ICD-10-CM, and Taiwan NHI Codes
"""
import logging
from services.config_loader import config_loader
from services.unit_conversion_service import unit_converter
from services.twcore_adapter import twcore_adapter


class ConditionCheckerService:
    """Service for checking medical conditions and risk factors"""
    
    # Default keywords for text-based matching (all lowercase for consistent comparison)
    BLEEDING_DIATHESIS_KEYWORDS = [
        'bleeding disorder', 'bleeding diathesis', 'hemorrhagic diathesis',
        'hemophilia', 'von willebrand', 'coagulation disorder'
    ]
    
    CANCER_KEYWORDS = [
        'cancer', 'malignancy', 'neoplasm', 'carcinoma', 'sarcoma', 'lymphoma', 'leukemia'
    ]
    
    CANCER_EXCLUSION_KEYWORDS = [
        'basal cell', 'squamous cell', 'skin cancer'
    ]
    
    @staticmethod
    def get_condition_text(condition):
        """
        Extract all text from a condition for text-based matching.
        """
        text_parts = []
        
        # Get text field
        if condition.get('code', {}).get('text'):
            text_parts.append(condition['code']['text'])
        
        # Get display text from codings
        for coding in condition.get('code', {}).get('coding', []):
            if coding.get('display'):
                text_parts.append(coding['display'])
        
        return ' '.join(text_parts)
    
    @staticmethod
    def resource_has_code(resource, system, code):
        """Checks if a resource's coding matches the given system and code."""
        for coding in resource.get('code', {}).get('coding', []):
            if coding.get('system') == system and coding.get('code') == code:
                return True
        return False
    
    @classmethod
    def _check_icd10_codes(cls, conditions, icd10_codes):
        """
        Helper to check for ICD-10 codes in conditions
        Returns tuple (found_boolean, found_display_text)
        """
        if not icd10_codes:
            return False, None
            
        for condition in conditions:
            diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
            if diagnosis_info['has_icd10']:
                code = diagnosis_info['icd10_code']
                # Check for exact match or prefix match (e.g., "I21" matches "I21.0")
                for target_code in icd10_codes:
                    if code == target_code or code.startswith(target_code + "."):
                        return True, diagnosis_info['icd10_display'] or f"ICD-10: {code}"
        return False, None

    @classmethod
    def check_bleeding_diathesis(cls, conditions):
        """
        Check for chronic bleeding diathesis using codes from configuration.
        Supports SNOMED CT and ICD-10-CM.
        
        Returns:
            Tuple of (has_condition, condition_info)
        """
        snomed_config = config_loader.get_snomed_codes('bleeding_diathesis')
        bleeding_diathesis_codes = snomed_config.get('specific_codes', ['64779008'])
        icd10_codes = snomed_config.get('icd10cm_codes', [])
        
        # 1. Check SNOMED codes
        for condition in conditions:
            for coding in condition.get('code', {}).get('coding', []):
                if (coding.get('system') == 'http://snomed.info/sct' and 
                    coding.get('code') in bleeding_diathesis_codes):
                    return True, coding.get('display', 'Bleeding diathesis')
        
        # 2. Check ICD-10 codes
        has_icd10, icd10_info = cls._check_icd10_codes(conditions, icd10_codes)
        if has_icd10:
            return True, icd10_info
            
        # 3. Check text for bleeding diathesis terms
        for condition in conditions:
            condition_text = cls.get_condition_text(condition).lower()
            for keyword in cls.BLEEDING_DIATHESIS_KEYWORDS:
                if keyword in condition_text:
                    return True, condition_text
        
        return False, None
    
    @classmethod
    def check_prior_bleeding(cls, conditions):
        """
        Check for prior bleeding history using codes from configuration.
        Supports SNOMED CT and ICD-10-CM.
        
        Returns:
            Tuple of (has_bleeding, list_of_bleeding_evidence)
        """
        snomed_config = config_loader.get_snomed_codes('prior_bleeding')
        prior_bleeding_codes = snomed_config.get('specific_codes', [])
        icd10_codes = snomed_config.get('icd10cm_codes', [])
        
        found_bleeding = []
        
        for condition in conditions:
            # 1. Check SNOMED codes
            for coding in condition.get('code', {}).get('coding', []):
                if (coding.get('system') == 'http://snomed.info/sct' and 
                    coding.get('code') in prior_bleeding_codes):
                    found_bleeding.append(coding.get('display', 'Prior bleeding'))
            
            # 2. Check ICD-10 codes
            diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
            if diagnosis_info['has_icd10']:
                code = diagnosis_info['icd10_code']
                for target_code in icd10_codes:
                    if code == target_code or code.startswith(target_code + "."):
                        found_bleeding.append(diagnosis_info['icd10_display'] or f"Prior bleeding (ICD-10: {code})")
                        break

            # 3. Check text for bleeding terms
            condition_text = cls.get_condition_text(condition).lower()
            bleeding_keywords = config_loader.get_bleeding_history_keywords()
            for keyword in bleeding_keywords:
                # Keywords from config may have mixed case, normalize for comparison
                if keyword.lower() in condition_text:
                    found_bleeding.append(condition_text)
                    break
        
        # Remove duplicates and empty strings
        found_bleeding = list(set([f for f in found_bleeding if f]))
        return len(found_bleeding) > 0, found_bleeding
    
    @classmethod
    def check_liver_cirrhosis_with_portal_hypertension(cls, conditions):
        """
        Check for liver cirrhosis with portal hypertension.
        Requires BOTH cirrhosis AND portal hypertension signs.
        Supports SNOMED CT and ICD-10-CM.
        
        Returns:
            Tuple of (has_condition, list_of_found_conditions)
        """
        snomed_config = config_loader.get_snomed_codes('liver_cirrhosis')
        
        cirrhosis_code = snomed_config.get('parent_code', '19943007')
        cirrhosis_keywords = snomed_config.get('cirrhosis_keywords', ['cirrhosis'])
        cirrhosis_icd10 = snomed_config.get('icd10cm_codes', [])
        
        pht_config = snomed_config.get('portal_hypertension_criteria', {})
        pht_criteria = pht_config.get('additional_criteria', ['ascites', 'portal hypertension', 
                                                              'esophageal varices', 'hepatic encephalopathy'])
        pht_codes = pht_config.get('snomed_codes', [])
        pht_icd10 = pht_config.get('icd10cm_codes', [])
        
        has_cirrhosis = False
        has_pht = False
        found_conditions = []
        
        for condition in conditions:
            condition_text = cls.get_condition_text(condition).lower()
            
            # Check SNOMED and Text
            for coding in condition.get('code', {}).get('coding', []):
                code = coding.get('code', '')
                system = coding.get('system', '')
                
                if system == 'http://snomed.info/sct' and code == cirrhosis_code:
                    has_cirrhosis = True
                    found_conditions.append(coding.get('display', 'Liver cirrhosis'))
                
                if system == 'http://snomed.info/sct' and code in pht_codes:
                    has_pht = True
                    found_conditions.append(coding.get('display', 'Portal hypertension'))
            
            for keyword in cirrhosis_keywords:
                if keyword in condition_text:
                    has_cirrhosis = True
                    found_conditions.append(f"Cirrhosis: {condition_text[:50]}...")
                    break
            
            for criteria in pht_criteria:
                if criteria in condition_text:
                    has_pht = True
                    found_conditions.append(f"Portal HTN sign: {criteria}")
                    break
            
            # Check ICD-10
            diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
            if diagnosis_info['has_icd10']:
                code = diagnosis_info['icd10_code']
                
                # Check Cirrhosis ICD-10
                for target in cirrhosis_icd10:
                    if code == target or code.startswith(target + "."):
                        has_cirrhosis = True
                        found_conditions.append(diagnosis_info['icd10_display'] or f"Liver cirrhosis (ICD-10: {code})")
                        break
                
                # Check Portal Hypertension ICD-10
                for target in pht_icd10:
                    if code == target or code.startswith(target + "."):
                        has_pht = True
                        found_conditions.append(diagnosis_info['icd10_display'] or f"Portal hypertension sign (ICD-10: {code})")
                        break
        
        return (has_cirrhosis and has_pht), list(set(found_conditions))
    
    @classmethod
    def check_active_cancer(cls, conditions):
        """
        Check for active malignant neoplastic disease.
        Excludes non-melanoma skin cancers.
        Supports SNOMED CT and ICD-10-CM.
        
        Returns:
            Tuple of (has_cancer, cancer_info)
        """
        snomed_config = config_loader.get_snomed_codes('active_cancer')
        malignancy_code = snomed_config.get('parent_code', '363346000')
        excluded_codes = snomed_config.get('exclude_codes', ['254637007', '254632001'])
        icd10_codes = snomed_config.get('icd10cm_codes', []) # e.g., C00-C97
        
        for condition in conditions:
            # Check clinical status
            clinical_status = condition.get('clinicalStatus', {})
            status_code = 'active' # Default to active if not specified (conservative)
            
            if isinstance(clinical_status, dict):
                for coding in clinical_status.get('coding', []):
                    if coding.get('system') == 'http://terminology.hl7.org/CodeSystem/condition-clinical':
                        status_code = coding.get('code')
                        break
            elif isinstance(clinical_status, str):
                status_code = clinical_status.lower()
            
            # Only consider active conditions
            if status_code not in ['active', 'recurrence', 'relapse']:
                continue
            
            # 1. Check SNOMED codes
            for coding in condition.get('code', {}).get('coding', []):
                if coding.get('system') == 'http://snomed.info/sct':
                    code = coding.get('code')
                    
                    # Exclude specific skin cancers
                    if code in excluded_codes:
                        continue
                    
                    # Include malignant neoplastic disease
                    if code == malignancy_code:
                        return True, coding.get('display', 'Active malignancy')
            
            # 2. Check ICD-10 codes
            diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
            if diagnosis_info['has_icd10']:
                code = diagnosis_info['icd10_code']
                # Check if code starts with any C code (Malignant neoplasms)
                # Assuming config has prefix list like ["C"] or ["C00", "C01"...]
                for target in icd10_codes:
                    if code.startswith(target):
                        return True, diagnosis_info['icd10_display'] or f"Active cancer (ICD-10: {code})"

            # 3. Check text for cancer terms
            condition_text = cls.get_condition_text(condition).lower()
            
            # Check if it's an excluded skin cancer
            if any(exclusion in condition_text for exclusion in cls.CANCER_EXCLUSION_KEYWORDS):
                continue
            
            # Check for cancer keywords
            for keyword in cls.CANCER_KEYWORDS:
                if keyword in condition_text:
                    return True, condition_text
        
        return False, None
    
    @classmethod
    def check_oral_anticoagulation(cls, medications):
        """
        Check for long-term oral anticoagulation therapy.
        Supports RxNorm and Taiwan NHI Codes.
        
        Returns:
            Boolean indicating if patient is on oral anticoagulants
        """
        med_config = config_loader.get_medication_keywords()
        oac_config = med_config.get('oral_anticoagulants', {})
        
        anticoagulant_keywords = (
            oac_config.get('generic_names', []) + 
            oac_config.get('brand_names', [])
        )
        target_nhi_codes = oac_config.get('nhi_codes', [])
        
        for med in medications:
            # Check NHI Codes
            nhi_info = twcore_adapter.extract_nhi_medication_code(med)
            if nhi_info['has_nhi_code']:
                code = nhi_info['nhi_code']
                # Check exact match or prefix match for NHI codes
                for target in target_nhi_codes:
                    if code == target or code.startswith(target):
                        logging.info(f"Found OAC via NHI code: {code}")
                        return True
            
            # Check text/keywords
            med_code = med.get('medicationCodeableConcept', {})
            med_text = str(med_code).lower()
            
            for anticoag in anticoagulant_keywords:
                if anticoag in med_text:
                    return True
        
        return False
    
    @classmethod
    def check_nsaids_or_corticosteroids(cls, medications):
        """
        Check for chronic use of NSAIDs or corticosteroids.
        Supports Keywords and Taiwan NHI Codes.
        
        Returns:
            Boolean indicating if patient is on these medications
        """
        med_config = config_loader.get_medication_keywords()
        nsaid_config = med_config.get('nsaids_corticosteroids', {})
        
        drug_keywords = (
            nsaid_config.get('nsaid_keywords', []) + 
            nsaid_config.get('corticosteroid_keywords', [])
        )
        target_nhi_codes = nsaid_config.get('nhi_codes', [])
        
        for med in medications:
            # Check NHI Codes
            nhi_info = twcore_adapter.extract_nhi_medication_code(med)
            if nhi_info['has_nhi_code']:
                code = nhi_info['nhi_code']
                # Check exact match or prefix match
                for target in target_nhi_codes:
                    if code == target or code.startswith(target):
                        logging.info(f"Found NSAID/Steroid via NHI code: {code}")
                        return True

            # Check text/keywords
            med_text = str(med.get('medicationCodeableConcept', {})).lower()
            for code in drug_keywords:
                if code in med_text:
                    return True
        
        return False
    
    @classmethod
    def check_thrombocytopenia(cls, raw_data):
        """
        Check for thrombocytopenia based on platelet count.
        Also checks ICD-10 codes for Thrombocytopenia.
        
        Returns:
            Boolean indicating if condition is met
        """
        snomed_config = config_loader.get_snomed_codes('thrombocytopenia')
        threshold = snomed_config.get('threshold', {}).get('value', 100)
        icd10_codes = snomed_config.get('icd10cm_codes', [])
        
        # 1. Check Lab Value
        platelets = raw_data.get('PLATELETS', [])
        if platelets:
            plt_obs = platelets[0]
            plt_val = unit_converter.get_value_from_observation(
                plt_obs, 
                unit_converter.TARGET_UNITS['PLATELETS']
            )
            if plt_val and plt_val < threshold:
                return True
        
        # 2. Check ICD-10 Diagnosis (D69.3, etc.)
        conditions = raw_data.get('conditions', [])
        has_icd10, _ = cls._check_icd10_codes(conditions, icd10_codes)
        if has_icd10:
            return True
            
        return False
    
    @classmethod
    def check_arc_hbr_factors_detailed(cls, raw_data, medications):
        """
        Check for individual ARC-HBR risk factors and return detailed breakdown.
        
        Returns:
            Dictionary with individual factor flags for UI display
        """
        conditions = raw_data.get('conditions', [])
        
        # Check each factor
        has_thrombocytopenia = cls.check_thrombocytopenia(raw_data)
        has_bleeding_diathesis, _ = cls.check_bleeding_diathesis(conditions)
        has_active_cancer, _ = cls.check_active_cancer(conditions)
        has_liver_condition, _ = cls.check_liver_cirrhosis_with_portal_hypertension(conditions)
        has_nsaids = cls.check_nsaids_or_corticosteroids(medications)
        
        # Determine if any factor is present
        has_any_factor = any([
            has_thrombocytopenia,
            has_bleeding_diathesis,
            has_active_cancer,
            has_liver_condition,
            has_nsaids
        ])
        
        return {
            'has_any_factor': has_any_factor,
            'thrombocytopenia': has_thrombocytopenia,
            'bleeding_diathesis': has_bleeding_diathesis,
            'active_malignancy': has_active_cancer,
            'liver_cirrhosis': has_liver_condition,
            'nsaids_corticosteroids': has_nsaids
        }


# Global instance
condition_checker = ConditionCheckerService()
