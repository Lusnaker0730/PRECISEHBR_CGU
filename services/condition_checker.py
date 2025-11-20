"""
Condition Checker Service
Handles checking for specific medical conditions in patient data
"""
import logging
from services.config_loader import config_loader
from services.unit_conversion_service import unit_converter


class ConditionCheckerService:
    """Service for checking medical conditions and risk factors"""
    
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
    def check_bleeding_diathesis(cls, conditions):
        """
        Check for chronic bleeding diathesis using codes from configuration.
        
        Returns:
            Tuple of (has_condition, condition_info)
        """
        snomed_config = config_loader.get_snomed_codes('bleeding_diathesis')
        bleeding_diathesis_codes = snomed_config.get('specific_codes', ['64779008'])
        
        for condition in conditions:
            # Check SNOMED codes
            for coding in condition.get('code', {}).get('coding', []):
                if (coding.get('system') == 'http://snomed.info/sct' and 
                    coding.get('code') in bleeding_diathesis_codes):
                    return True, coding.get('display', 'Bleeding diathesis')
            
            # Check text for bleeding diathesis terms
            condition_text = cls.get_condition_text(condition).lower()
            bleeding_keywords = ['bleeding disorder', 'bleeding diathesis', 'hemorrhagic diathesis', 
                               'hemophilia', 'von willebrand', 'coagulation disorder']
            for keyword in bleeding_keywords:
                if keyword in condition_text:
                    return True, condition_text
        
        return False, None
    
    @classmethod
    def check_prior_bleeding(cls, conditions):
        """
        Check for prior bleeding history using codes from configuration.
        
        Returns:
            Tuple of (has_bleeding, list_of_bleeding_evidence)
        """
        snomed_config = config_loader.get_snomed_codes('prior_bleeding')
        prior_bleeding_codes = snomed_config.get('specific_codes', [])
        
        found_bleeding = []
        
        for condition in conditions:
            # Check SNOMED codes
            for coding in condition.get('code', {}).get('coding', []):
                if (coding.get('system') == 'http://snomed.info/sct' and 
                    coding.get('code') in prior_bleeding_codes):
                    found_bleeding.append(coding.get('display', 'Prior bleeding'))
            
            # Check text for bleeding terms
            condition_text = cls.get_condition_text(condition).lower()
            bleeding_keywords = ['hemorrhage', 'bleeding', 'hemarthrosis', 'hematuria', 'hemothorax',
                               'hemopericardium', 'hemoperitoneum', 'retroperitoneal hematoma']
            for keyword in bleeding_keywords:
                if keyword in condition_text:
                    found_bleeding.append(condition_text)
                    break
        
        return len(found_bleeding) > 0, found_bleeding
    
    @classmethod
    def check_liver_cirrhosis_with_portal_hypertension(cls, conditions):
        """
        Check for liver cirrhosis with portal hypertension.
        Requires BOTH cirrhosis AND portal hypertension signs.
        
        Returns:
            Tuple of (has_condition, list_of_found_conditions)
        """
        snomed_config = config_loader.get_snomed_codes('liver_cirrhosis')
        
        cirrhosis_code = snomed_config.get('parent_code', '19943007')
        cirrhosis_keywords = snomed_config.get('cirrhosis_keywords', ['cirrhosis'])
        
        pht_config = snomed_config.get('portal_hypertension_criteria', {})
        pht_criteria = pht_config.get('additional_criteria', ['ascites', 'portal hypertension', 
                                                              'esophageal varices', 'hepatic encephalopathy'])
        pht_codes = pht_config.get('snomed_codes', [])
        
        has_cirrhosis = False
        has_pht = False
        found_conditions = []
        
        for condition in conditions:
            condition_text = cls.get_condition_text(condition).lower()
            
            # Check for liver cirrhosis SNOMED code
            for coding in condition.get('code', {}).get('coding', []):
                code = coding.get('code', '')
                system = coding.get('system', '')
                
                if system == 'http://snomed.info/sct' and code == cirrhosis_code:
                    has_cirrhosis = True
                    found_conditions.append(coding.get('display', 'Liver cirrhosis'))
                
                if system == 'http://snomed.info/sct' and code in pht_codes:
                    has_pht = True
                    found_conditions.append(coding.get('display', 'Portal hypertension'))
            
            # Check text
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
        
        return (has_cirrhosis and has_pht), found_conditions
    
    @classmethod
    def check_active_cancer(cls, conditions):
        """
        Check for active malignant neoplastic disease.
        Excludes non-melanoma skin cancers.
        
        Returns:
            Tuple of (has_cancer, cancer_info)
        """
        snomed_config = config_loader.get_snomed_codes('active_cancer')
        malignancy_code = snomed_config.get('parent_code', '363346000')
        excluded_codes = snomed_config.get('exclude_codes', ['254637007', '254632001'])
        
        for condition in conditions:
            # Check clinical status
            clinical_status = condition.get('clinicalStatus', {})
            if isinstance(clinical_status, dict):
                status_code = None
                for coding in clinical_status.get('coding', []):
                    if coding.get('system') == 'http://terminology.hl7.org/CodeSystem/condition-clinical':
                        status_code = coding.get('code')
                        break
            else:
                status_code = str(clinical_status).lower()
            
            # Only consider active conditions
            if status_code != 'active':
                continue
            
            # Check SNOMED codes
            for coding in condition.get('code', {}).get('coding', []):
                if coding.get('system') == 'http://snomed.info/sct':
                    code = coding.get('code')
                    
                    # Exclude specific skin cancers
                    if code in excluded_codes:
                        continue
                    
                    # Include malignant neoplastic disease
                    if code == malignancy_code:
                        return True, coding.get('display', 'Active malignancy')
            
            # Check text for cancer terms (but still require active status)
            condition_text = cls.get_condition_text(condition).lower()
            cancer_keywords = ['cancer', 'malignancy', 'neoplasm', 'carcinoma', 'sarcoma', 'lymphoma', 'leukemia']
            exclusion_keywords = ['basal cell', 'squamous cell', 'skin cancer']
            
            # Check if it's an excluded skin cancer
            if any(exclusion in condition_text for exclusion in exclusion_keywords):
                continue
            
            # Check for cancer keywords
            for keyword in cancer_keywords:
                if keyword in condition_text:
                    return True, condition_text
        
        return False, None
    
    @classmethod
    def check_oral_anticoagulation(cls, medications):
        """
        Check for long-term oral anticoagulation therapy.
        
        Returns:
            Boolean indicating if patient is on oral anticoagulants
        """
        med_config = config_loader.get_medication_keywords()
        oac_config = med_config.get('oral_anticoagulants', {})
        
        anticoagulant_codes = (
            oac_config.get('generic_names', []) + 
            oac_config.get('brand_names', [])
        )
        
        for med in medications:
            med_code = med.get('medicationCodeableConcept', {})
            med_text = str(med_code).lower()
            
            for anticoag in anticoagulant_codes:
                if anticoag in med_text:
                    return True
        
        return False
    
    @classmethod
    def check_nsaids_or_corticosteroids(cls, medications):
        """
        Check for chronic use of NSAIDs or corticosteroids.
        
        Returns:
            Boolean indicating if patient is on these medications
        """
        med_config = config_loader.get_medication_keywords()
        nsaid_config = med_config.get('nsaids_corticosteroids', {})
        
        drug_codes = (
            nsaid_config.get('nsaid_keywords', []) + 
            nsaid_config.get('corticosteroid_keywords', [])
        )
        
        for med in medications:
            med_text = str(med.get('medicationCodeableConcept', {})).lower()
            for code in drug_codes:
                if code in med_text:
                    return True
        
        return False
    
    @classmethod
    def check_thrombocytopenia(cls, raw_data):
        """
        Check for thrombocytopenia based on platelet count.
        
        Returns:
            Boolean indicating if platelet count is below threshold
        """
        snomed_config = config_loader.get_snomed_codes('thrombocytopenia')
        threshold = snomed_config.get('threshold', {}).get('value', 100)
        
        platelets = raw_data.get('PLATELETS', [])
        if platelets:
            plt_obs = platelets[0]
            plt_val = unit_converter.get_value_from_observation(
                plt_obs, 
                unit_converter.TARGET_UNITS['PLATELETS']
            )
            if plt_val and plt_val < threshold:
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

