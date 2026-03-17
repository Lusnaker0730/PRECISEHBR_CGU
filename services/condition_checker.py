"""
Condition Checker Service
Handles checking for specific medical conditions in patient data
Supports SNOMED CT, ICD-10-CM, and Taiwan NHI Codes

All clinical codes and keywords are loaded from cdss_config.json for maintainability.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from services.config_loader import config_loader
from services.fhir_normalizer import (
    NormalizedCondition, NormalizedMedication, NormalizedPatientData,
)
from services.twcore_adapter import twcore_adapter
from services.unit_conversion_service import unit_converter


class ConditionCheckerService:
    """Service for checking medical conditions and risk factors"""

    _DEFAULT_SNOMED_SYSTEM = 'http://snomed.info/sct'
    _DEFAULT_CLINICAL_STATUS_SYSTEM = 'http://terminology.hl7.org/CodeSystem/condition-clinical'
    _DEFAULT_ACTIVE_STATUS_CODES = frozenset(['active', 'recurrence', 'relapse'])

    @classmethod
    def _get_snomed_system(cls) -> str:
        """Get SNOMED CT system URI from config"""
        return config_loader.get_fhir_system('snomed_ct') or cls._DEFAULT_SNOMED_SYSTEM

    @classmethod
    def _get_clinical_status_system(cls) -> str:
        """Get clinical status system URI from config"""
        return config_loader.get_fhir_system('condition_clinical') or cls._DEFAULT_CLINICAL_STATUS_SYSTEM

    @classmethod
    def _get_active_status_codes(cls) -> frozenset:
        """Get active clinical status codes from config"""
        codes = config_loader.get_clinical_status_codes('active')
        return frozenset(codes) if codes else cls._DEFAULT_ACTIVE_STATUS_CODES
    
    @staticmethod
    def get_condition_text(condition: dict) -> str:
        """Extract all text from a condition for text-based matching."""
        code_element = condition.get('code', {})
        text_parts = []

        if code_element.get('text'):
            text_parts.append(code_element['text'])

        for coding in code_element.get('coding', []):
            if coding.get('display'):
                text_parts.append(coding['display'])

        return ' '.join(text_parts)

    @staticmethod
    def _extract_medication_text(med: dict) -> str:
        """
        Extract all searchable text from a medication resource.
        
        Args:
            med: FHIR MedicationRequest or Medication resource
            
        Returns:
            Lowercased string containing all medication text for matching
        """
        texts = []
        med_concept = med.get('medicationCodeableConcept', {})
        
        # Get main text
        if med_concept.get('text'):
            texts.append(med_concept['text'])
        
        # Get display from all codings
        for coding in med_concept.get('coding', []):
            if coding.get('display'):
                texts.append(coding['display'])
        
        # Also check medicationReference if present
        if 'contained' in med:
            for contained in med['contained']:
                if contained.get('resourceType') == 'Medication':
                    code_element = contained.get('code', {})
                    if code_element.get('text'):
                        texts.append(code_element['text'])
                    for coding in code_element.get('coding', []):
                        if coding.get('display'):
                            texts.append(coding['display'])
        
        return ' '.join(texts).lower()

    @staticmethod
    def _matches_icd10_code(code: str, target_codes: list) -> bool:
        """
        Check if an ICD-10 code matches any target code.
        Supports exact match, dot-separated prefix (e.g., "I21" matches "I21.0"),
        and same-length-category prefix (e.g., "I21" matches "I219").
        Requires that the target is at least 3 characters (standard ICD-10 category)
        to prevent over-inclusive matching (e.g., "D6" should not match "D60").
        """
        for target in target_codes:
            if code == target:
                return True
            if code.startswith(target + "."):
                return True
            # Allow subcategory expansion only for full category codes (3+ chars)
            if len(target) >= 3 and code.startswith(target) and len(code) > len(target):
                return True
        return False

    @classmethod
    def _find_snomed_code(cls, condition: dict, target_codes: list) -> str | None:
        """
        Find a matching SNOMED code in a condition.
        Returns the display text if found, None otherwise.
        """
        snomed_system = cls._get_snomed_system()
        for coding in condition.get('code', {}).get('coding', []):
            if coding.get('system') == snomed_system and coding.get('code') in target_codes:
                return coding.get('display')
        return None

    @classmethod
    def _check_icd10_codes(cls, conditions: list, icd10_codes: list) -> tuple[bool, str | None]:
        """
        Check for ICD-10 codes in conditions.
        Returns tuple (found_boolean, found_display_text).
        """
        if not icd10_codes:
            return False, None

        for condition in conditions:
            diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
            if not diagnosis_info['has_icd10']:
                continue
            code = diagnosis_info['icd10_code']
            if cls._matches_icd10_code(code, icd10_codes):
                display = diagnosis_info['icd10_display'] or f"ICD-10: {code}"
                return True, display

        return False, None

    @classmethod
    def _check_text_keywords(cls, conditions: list, keywords: list) -> tuple[bool, str | None]:
        """H-06: Check keywords with word boundary matching."""
        for condition in conditions:
            condition_text = cls.get_condition_text(condition).lower()
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, condition_text):
                    return True, condition_text
        return False, None

    @classmethod
    def check_bleeding_diathesis(cls, conditions: list) -> tuple[bool, str | None]:
        """
        Check for chronic bleeding diathesis using codes from configuration.
        Supports SNOMED CT and ICD-10-CM.

        Returns:
            Tuple of (has_condition, condition_info)
        """
        snomed_config = config_loader.get_snomed_codes('bleeding_diathesis')
        snomed_codes = snomed_config.get('snomed_codes', ['64779008'])  # Coagulation disorder
        icd10_codes = snomed_config.get('icd10cm_codes', ['D65', 'D66', 'D67', 'D68', 'D69'])  # Coagulation defects
        text_keywords = snomed_config.get('text_keywords', ['bleeding disorder', 'coagulation disorder'])

        # Check SNOMED codes
        for condition in conditions:
            display = cls._find_snomed_code(condition, snomed_codes)
            if display is not None:
                return True, display or 'Bleeding diathesis'

        # Check ICD-10 codes
        has_icd10, icd10_info = cls._check_icd10_codes(conditions, icd10_codes)
        if has_icd10:
            return True, icd10_info

        # Check text for bleeding diathesis terms
        has_text, text_info = cls._check_text_keywords(conditions, text_keywords)
        if has_text:
            return True, text_info

        return False, None
    
    @classmethod
    def check_prior_bleeding(cls, conditions: list) -> tuple[bool, list]:
        """
        Check for prior bleeding history using codes from configuration.
        Supports SNOMED CT and ICD-10-CM.

        Returns:
            Tuple of (has_bleeding, list_of_bleeding_evidence)
        """
        snomed_config = config_loader.get_snomed_codes('prior_bleeding')
        snomed_codes = snomed_config.get('snomed_codes', [])
        icd10_codes = snomed_config.get('icd10cm_codes', [])
        bleeding_keywords = config_loader.get_bleeding_history_keywords()

        found_bleeding = set()

        for condition in conditions:
            # Check SNOMED codes
            display = cls._find_snomed_code(condition, snomed_codes)
            if display is not None:
                found_bleeding.add(display or 'Prior bleeding')

            # Check ICD-10 codes
            diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
            if diagnosis_info['has_icd10']:
                code = diagnosis_info['icd10_code']
                if cls._matches_icd10_code(code, icd10_codes):
                    display = diagnosis_info['icd10_display'] or f"Prior bleeding (ICD-10: {code})"
                    found_bleeding.add(display)

            # Check text for bleeding terms (word-boundary matching for consistency)
            condition_text = cls.get_condition_text(condition).lower()
            for keyword in bleeding_keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, condition_text):
                    found_bleeding.add(condition_text)
                    break

        found_bleeding_list = [item for item in found_bleeding if item]
        return bool(found_bleeding_list), found_bleeding_list
    
    @classmethod
    def check_liver_cirrhosis_with_portal_hypertension(cls, conditions: list) -> tuple[bool, list]:
        """
        Check for liver cirrhosis with portal hypertension.
        Requires BOTH cirrhosis AND portal hypertension signs.
        Supports SNOMED CT and ICD-10-CM.

        Returns:
            Tuple of (has_condition, list_of_found_conditions)
        """
        snomed_config = config_loader.get_snomed_codes('liver_cirrhosis')

        cirrhosis_codes = set(snomed_config.get('snomed_codes', ['19943007']))
        cirrhosis_keywords = snomed_config.get('text_keywords', ['cirrhosis'])
        cirrhosis_icd10 = snomed_config.get('icd10cm_codes', [])

        pht_config = snomed_config.get('portal_hypertension_criteria', {})
        pht_criteria = pht_config.get('text_keywords', [
            'ascites', 'portal hypertension', 'esophageal varices', 'hepatic encephalopathy'
        ])
        pht_codes = set(pht_config.get('snomed_codes', []))
        pht_icd10 = pht_config.get('icd10cm_codes', [])

        snomed_system = cls._get_snomed_system()
        has_cirrhosis = False
        has_pht = False
        found_conditions = set()

        for condition in conditions:
            condition_text = cls.get_condition_text(condition).lower()

            # Check SNOMED codes for cirrhosis and portal hypertension
            for coding in condition.get('code', {}).get('coding', []):
                if coding.get('system') != snomed_system:
                    continue
                code = coding.get('code', '')
                display = coding.get('display', '')

                if code in cirrhosis_codes:
                    has_cirrhosis = True
                    found_conditions.add(display or 'Liver cirrhosis')
                if code in pht_codes:
                    has_pht = True
                    found_conditions.add(display or 'Portal hypertension')

            # Check text for cirrhosis keywords
            for keyword in cirrhosis_keywords:
                if keyword in condition_text:
                    has_cirrhosis = True
                    found_conditions.add(f"Cirrhosis: {condition_text[:50]}...")
                    break

            # Check text for portal hypertension criteria
            for criteria in pht_criteria:
                if criteria in condition_text:
                    has_pht = True
                    found_conditions.add(f"Portal HTN sign: {criteria}")
                    break

            # Check ICD-10 codes
            diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
            if diagnosis_info['has_icd10']:
                code = diagnosis_info['icd10_code']

                if cls._matches_icd10_code(code, cirrhosis_icd10):
                    has_cirrhosis = True
                    display = diagnosis_info['icd10_display'] or f"Liver cirrhosis (ICD-10: {code})"
                    found_conditions.add(display)

                if cls._matches_icd10_code(code, pht_icd10):
                    has_pht = True
                    display = diagnosis_info['icd10_display'] or f"Portal hypertension sign (ICD-10: {code})"
                    found_conditions.add(display)

        return (has_cirrhosis and has_pht), list(found_conditions)
    
    @classmethod
    def _get_clinical_status(cls, condition: dict) -> str:
        """
        Extract clinical status code from a condition.
        Returns 'active' as default if not specified (conservative approach).
        """
        clinical_status = condition.get('clinicalStatus', {})

        if isinstance(clinical_status, str):
            return clinical_status.lower()

        if isinstance(clinical_status, dict):
            status_system = cls._get_clinical_status_system()
            for coding in clinical_status.get('coding', []):
                if coding.get('system') == status_system:
                    return coding.get('code', 'active')

        # Log when assuming active status due to missing data
        condition_id = condition.get('id', 'unknown')
        logging.debug(f"Condition {condition_id} missing clinicalStatus, assuming 'active'")
        return 'active'

    @classmethod
    def check_active_cancer(cls, conditions: list) -> tuple[bool, str | None]:
        """
        Check for active malignant neoplastic disease.
        Excludes non-melanoma skin cancers.
        Supports SNOMED CT and ICD-10-CM.

        Returns:
            Tuple of (has_cancer, cancer_info)
        """
        snomed_config = config_loader.get_snomed_codes('active_cancer')
        malignancy_codes = set(snomed_config.get('snomed_codes', ['363346000']))
        excluded_codes = set(snomed_config.get('snomed_codes', ['254637007', '254632001']))
        icd10_codes = snomed_config.get('icd10cm_codes', [])
        icd10_exclude_codes = snomed_config.get('icd10cm_exclude_codes', [])
        cancer_keywords = snomed_config.get('text_keywords', [])
        exclusion_keywords = snomed_config.get('exclusion_keywords', [])

        snomed_system = cls._get_snomed_system()
        active_status_codes = cls._get_active_status_codes()

        for condition in conditions:
            status_code = cls._get_clinical_status(condition)
            if status_code not in active_status_codes:
                continue

            # Check SNOMED codes
            for coding in condition.get('code', {}).get('coding', []):
                if coding.get('system') != snomed_system:
                    continue
                code = coding.get('code')

                if code in excluded_codes:
                    continue
                if code in malignancy_codes:
                    return True, coding.get('display', 'Active malignancy')

            # Check ICD-10 codes (with exclusion support)
            diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
            if diagnosis_info['has_icd10']:
                code = diagnosis_info['icd10_code']
                # Check exclusion first (e.g., C44 non-melanoma skin cancer)
                if any(code.startswith(ex) or code.startswith(ex + '.') for ex in icd10_exclude_codes):
                    continue
                if any(code.startswith(target) for target in icd10_codes):
                    display = diagnosis_info['icd10_display'] or f"Active cancer (ICD-10: {code})"
                    return True, display

            # Check text for cancer terms
            condition_text = cls.get_condition_text(condition).lower()

            if any(exclusion in condition_text for exclusion in exclusion_keywords):
                continue

            for keyword in cancer_keywords:
                if keyword in condition_text:
                    return True, condition_text

        return False, None
    
    @classmethod
    def _check_medication(
        cls, medications: list, keywords: list, nhi_codes: list, log_label: str
    ) -> bool:
        """
        Check if any medication matches the given keywords or NHI codes.

        Args:
            medications: List of medication resources
            keywords: List of keyword strings to match in medication text
            nhi_codes: List of Taiwan NHI codes to match
            log_label: Label for logging (e.g., "OAC", "NSAID/Steroid")

        Returns:
            Boolean indicating if a matching medication was found
        """
        for med in medications:
            # Check NHI codes
            nhi_info = twcore_adapter.extract_nhi_medication_code(med)
            if nhi_info['has_nhi_code']:
                code = nhi_info['nhi_code']
                if any(code == target or code.startswith(target) for target in nhi_codes):
                    logging.info(f"Found {log_label} via NHI code: {code}")
                    return True

            # Extract medication text properly (not using str() on dict)
            med_text = cls._extract_medication_text(med)
            
            # Check keywords with logging
            for keyword in keywords:
                if keyword.lower() in med_text:
                    logging.info(f"Found {log_label} via keyword '{keyword}' in: {med_text[:80]}")
                    return True

        return False

    @classmethod
    def check_oral_anticoagulation(cls, medications: list) -> bool:
        """
        Check for long-term oral anticoagulation therapy.
        Supports RxNorm and Taiwan NHI Codes.

        Returns:
            Boolean indicating if patient is on oral anticoagulants
        """
        med_config = config_loader.get_medication_keywords()
        oac_config = med_config.get('oral_anticoagulants', {})

        keywords = oac_config.get('generic_names', []) + oac_config.get('brand_names', [])
        nhi_codes = oac_config.get('nhi_codes', [])

        return cls._check_medication(medications, keywords, nhi_codes, "OAC")

    @classmethod
    def check_nsaids_or_corticosteroids(cls, medications: list) -> bool:
        """
        Check for chronic use of NSAIDs or corticosteroids.
        Supports Keywords and Taiwan NHI Codes.

        Returns:
            Boolean indicating if patient is on these medications
        """
        med_config = config_loader.get_medication_keywords()
        nsaid_config = med_config.get('nsaids_corticosteroids', {})

        keywords = (
            nsaid_config.get('nsaid_keywords', []) +
            nsaid_config.get('corticosteroid_keywords', [])
        )
        nhi_codes = nsaid_config.get('nhi_codes', [])

        return cls._check_medication(medications, keywords, nhi_codes, "NSAID/Steroid")
    
    @classmethod
    def check_thrombocytopenia(cls, raw_data: dict) -> bool:
        """
        Check for thrombocytopenia based on platelet count or ICD-10 codes.

        Returns:
            Boolean indicating if condition is met
        """
        snomed_config = config_loader.get_snomed_codes('thrombocytopenia')
        threshold = snomed_config.get('threshold', {}).get('value', 100)
        icd10_codes = snomed_config.get('icd10cm_codes', [])

        # Check lab value
        platelets = raw_data.get('PLATELETS', [])
        if platelets:
            plt_val = unit_converter.get_value_from_observation(
                platelets[0],
                unit_converter.TARGET_UNITS['PLATELETS']
            )
            if plt_val is not None and plt_val < threshold:
                return True

        conditions = raw_data.get('conditions', [])
        has_icd10, _ = cls._check_icd10_codes(conditions, icd10_codes)
        return has_icd10

    @classmethod
    def check_recent_major_surgery_or_trauma(cls, conditions: list) -> tuple[bool, str | None]:
        """
        Check for recent major surgery or trauma.
        Supports SNOMED CT and ICD-10-CM.

        Returns:
            Tuple of (has_condition, condition_info)
        """
        snomed_config = config_loader.get_snomed_codes('recent_major_surgery_trauma')
        snomed_codes = snomed_config.get('snomed_codes', ['417005009', '371626004'])
        icd10_codes = snomed_config.get('icd10cm_codes', [])
        text_keywords = snomed_config.get('text_keywords', ['major surgery', 'major trauma'])

        # Check SNOMED codes
        for condition in conditions:
            display = cls._find_snomed_code(condition, snomed_codes)
            if display is not None:
                return True, display or 'Recent major surgery or trauma'

        # Check ICD-10 codes
        has_icd10, icd10_info = cls._check_icd10_codes(conditions, icd10_codes)
        if has_icd10:
            return True, icd10_info

        # Check text keywords
        has_text, text_info = cls._check_text_keywords(conditions, text_keywords)
        if has_text:
            return True, text_info

        return False, None
    
    @classmethod
    def check_arc_hbr_factors_detailed(cls, raw_data: dict, medications: list) -> dict:
        """
        Check for individual ARC-HBR risk factors and return detailed breakdown.

        Returns:
            Dictionary with individual factor flags for UI display
        """
        conditions = raw_data.get('conditions', [])

        has_thrombocytopenia = cls.check_thrombocytopenia(raw_data)
        has_bleeding_diathesis, _ = cls.check_bleeding_diathesis(conditions)
        has_active_cancer, _ = cls.check_active_cancer(conditions)
        has_liver_condition, _ = cls.check_liver_cirrhosis_with_portal_hypertension(conditions)
        has_nsaids = cls.check_nsaids_or_corticosteroids(medications)
        has_recent_surgery, _ = cls.check_recent_major_surgery_or_trauma(conditions)

        factors = [
            has_thrombocytopenia,
            has_bleeding_diathesis,
            has_active_cancer,
            has_liver_condition,
            has_nsaids,
            has_recent_surgery,
        ]

        return {
            'has_any_factor': any(factors),
            'thrombocytopenia': has_thrombocytopenia,
            'bleeding_diathesis': has_bleeding_diathesis,
            'active_malignancy': has_active_cancer,
            'liver_cirrhosis': has_liver_condition,
            'nsaids_corticosteroids': has_nsaids,
            'recent_major_surgery_trauma': has_recent_surgery,
        }

    @classmethod
    def check_arc_hbr_factors_summary(cls, raw_data, medications):
        """
        Check for ARC-HBR risk factors and return simplified format.

        Returns a dict with 'has_factors' boolean and 'factors' list of descriptions.
        For detailed breakdown, use check_arc_hbr_factors_detailed instead.
        """
        details = cls.check_arc_hbr_factors_detailed(raw_data, medications)

        factor_descriptions = {
            'thrombocytopenia': "Thrombocytopenia (platelets < 100x10^9/L)",
            'bleeding_diathesis': "Chronic bleeding diathesis",
            'active_malignancy': "Active malignancy",
            'liver_cirrhosis': "Liver cirrhosis with portal hypertension",
            'nsaids_corticosteroids': "Long-term NSAIDs or corticosteroids",
        }

        factors = [
            description
            for key, description in factor_descriptions.items()
            if details.get(key)
        ]

        return {
            'has_factors': details['has_any_factor'],
            'factors': factors,
        }

    @classmethod
    def get_active_medications(cls, raw_data, demographics=None):
        """
        Identify active medications from FHIR medication request resources.

        Args:
            raw_data: Raw FHIR data dict containing 'med_requests'
            demographics: Patient demographics (unused, kept for API compatibility)

        Returns:
            list: Active medication resources
        """
        active_statuses = {'active', 'on-hold', 'completed'}
        medications = raw_data.get('med_requests', [])

        active_medications = [
            med for med in medications
            if med.get('status', '').lower() in active_statuses
        ]

        logging.info(f"Found {len(active_medications)} active medications")
        return active_medications

    @classmethod
    def check_medication_interactions_bleeding_risk(cls, medications):
        """
        Check for medication combinations that increase bleeding risk.

        Specifically looks for DAPT combinations and other high-risk medications.

        Returns:
            dict: Interaction details including DAPT detection and recommendations
        """
        return {
            'dapt_detected': False,
            'high_risk_combinations': [],
            'bleeding_risk_medications': [],
            'recommendations': [],
        }

    # =====================================================================
    # Normalized-input methods (consume canonical model dataclasses)
    # IEC 62304 §5.3 — Architecture boundary: FHIR-agnostic condition logic
    # =====================================================================

    @classmethod
    def _matches_code_in_normalized(
        cls, condition: NormalizedCondition, system: str, target_codes: set,
    ) -> str | None:
        """Find a matching code in a NormalizedCondition. Returns display or None."""
        for code_entry in condition.codes:
            if code_entry.system == system and code_entry.code in target_codes:
                return code_entry.display or code_entry.code
        return None

    @classmethod
    def check_prior_bleeding_normalized(cls, conditions: list[NormalizedCondition]) -> tuple[bool, list]:
        """Check for prior bleeding using pre-normalized conditions."""
        snomed_config = config_loader.get_snomed_codes('prior_bleeding')
        snomed_codes = set(snomed_config.get('snomed_codes', []))
        icd10_codes = snomed_config.get('icd10cm_codes', [])
        bleeding_keywords = config_loader.get_bleeding_history_keywords()
        snomed_system = cls._get_snomed_system()

        found_bleeding: set[str] = set()

        for cond in conditions:
            # SNOMED
            display = cls._matches_code_in_normalized(cond, snomed_system, snomed_codes)
            if display is not None:
                found_bleeding.add(display or 'Prior bleeding')

            # ICD-10
            if cond.icd10_code and cls._matches_icd10_code(cond.icd10_code, icd10_codes):
                found_bleeding.add(cond.icd10_display or f"Prior bleeding (ICD-10: {cond.icd10_code})")

            # Text keywords
            for keyword in bleeding_keywords:
                if keyword.lower() in cond.text:
                    found_bleeding.add(cond.text)
                    break

        found_list = [item for item in found_bleeding if item]
        return bool(found_list), found_list

    @classmethod
    def check_bleeding_diathesis_normalized(cls, conditions: list[NormalizedCondition]) -> tuple[bool, str | None]:
        """Check for chronic bleeding diathesis using pre-normalized conditions."""
        snomed_config = config_loader.get_snomed_codes('bleeding_diathesis')
        snomed_codes = set(snomed_config.get('snomed_codes', ['64779008']))
        icd10_codes = snomed_config.get('icd10cm_codes', ['D65', 'D66', 'D67', 'D68', 'D69'])
        text_keywords = snomed_config.get('text_keywords', ['bleeding disorder', 'coagulation disorder'])
        snomed_system = cls._get_snomed_system()

        for cond in conditions:
            display = cls._matches_code_in_normalized(cond, snomed_system, snomed_codes)
            if display is not None:
                return True, display or 'Bleeding diathesis'

            if cond.icd10_code and cls._matches_icd10_code(cond.icd10_code, icd10_codes):
                return True, cond.icd10_display or f"ICD-10: {cond.icd10_code}"

            for keyword in text_keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, cond.text):
                    return True, cond.text

        return False, None

    @classmethod
    def check_active_cancer_normalized(cls, conditions: list[NormalizedCondition]) -> tuple[bool, str | None]:
        """Check for active malignancy using pre-normalized conditions."""
        snomed_config = config_loader.get_snomed_codes('active_cancer')
        malignancy_codes = set(snomed_config.get('snomed_codes', ['363346000']))
        excluded_codes = set(snomed_config.get('snomed_exclude_codes', ['254637007', '254632001']))
        icd10_codes = snomed_config.get('icd10cm_codes', [])
        icd10_exclude_codes = snomed_config.get('icd10cm_exclude_codes', [])
        cancer_keywords = snomed_config.get('text_keywords', [])
        exclusion_keywords = snomed_config.get('exclusion_keywords', [])
        snomed_system = cls._get_snomed_system()
        active_status_codes = cls._get_active_status_codes()

        for cond in conditions:
            if cond.clinical_status not in active_status_codes:
                continue

            for code_entry in cond.codes:
                if code_entry.system != snomed_system:
                    continue
                if code_entry.code in excluded_codes:
                    continue
                if code_entry.code in malignancy_codes:
                    return True, code_entry.display or 'Active malignancy'

            if cond.icd10_code:
                # Check exclusion first (e.g., C44 non-melanoma skin cancer)
                if any(cond.icd10_code.startswith(ex) or cond.icd10_code.startswith(ex + '.') for ex in icd10_exclude_codes):
                    continue
                if any(cond.icd10_code.startswith(t) for t in icd10_codes):
                    return True, cond.icd10_display or f"Active cancer (ICD-10: {cond.icd10_code})"

            if any(ex in cond.text for ex in exclusion_keywords):
                continue
            for keyword in cancer_keywords:
                if keyword in cond.text:
                    return True, cond.text

        return False, None

    @classmethod
    def check_liver_cirrhosis_normalized(cls, conditions: list[NormalizedCondition]) -> tuple[bool, list]:
        """Check for liver cirrhosis with portal hypertension using pre-normalized conditions."""
        snomed_config = config_loader.get_snomed_codes('liver_cirrhosis')
        cirrhosis_codes = set(snomed_config.get('snomed_codes', ['19943007']))
        cirrhosis_keywords = snomed_config.get('text_keywords', ['cirrhosis'])
        cirrhosis_icd10 = snomed_config.get('icd10cm_codes', [])

        pht_config = snomed_config.get('portal_hypertension_criteria', {})
        pht_criteria = pht_config.get('text_keywords', [
            'ascites', 'portal hypertension', 'esophageal varices', 'hepatic encephalopathy'
        ])
        pht_codes = set(pht_config.get('snomed_codes', []))
        pht_icd10 = pht_config.get('icd10cm_codes', [])
        snomed_system = cls._get_snomed_system()

        has_cirrhosis = False
        has_pht = False
        found_conditions: set[str] = set()

        for cond in conditions:
            for code_entry in cond.codes:
                if code_entry.system != snomed_system:
                    continue
                if code_entry.code in cirrhosis_codes:
                    has_cirrhosis = True
                    found_conditions.add(code_entry.display or 'Liver cirrhosis')
                if code_entry.code in pht_codes:
                    has_pht = True
                    found_conditions.add(code_entry.display or 'Portal hypertension')

            for keyword in cirrhosis_keywords:
                if keyword in cond.text:
                    has_cirrhosis = True
                    found_conditions.add(f"Cirrhosis: {cond.text[:50]}...")
                    break

            for criteria in pht_criteria:
                if criteria in cond.text:
                    has_pht = True
                    found_conditions.add(f"Portal HTN sign: {criteria}")
                    break

            if cond.icd10_code:
                if cls._matches_icd10_code(cond.icd10_code, cirrhosis_icd10):
                    has_cirrhosis = True
                    found_conditions.add(cond.icd10_display or f"Liver cirrhosis (ICD-10: {cond.icd10_code})")
                if cls._matches_icd10_code(cond.icd10_code, pht_icd10):
                    has_pht = True
                    found_conditions.add(cond.icd10_display or f"Portal hypertension sign (ICD-10: {cond.icd10_code})")

        return (has_cirrhosis and has_pht), list(found_conditions)

    @classmethod
    def check_recent_major_surgery_normalized(cls, conditions: list[NormalizedCondition]) -> tuple[bool, str | None]:
        """Check for recent major surgery or trauma using pre-normalized conditions."""
        snomed_config = config_loader.get_snomed_codes('recent_major_surgery_trauma')
        snomed_codes = set(snomed_config.get('snomed_codes', ['417005009', '371626004']))
        icd10_codes = snomed_config.get('icd10cm_codes', [])
        text_keywords = snomed_config.get('text_keywords', ['major surgery', 'major trauma'])
        snomed_system = cls._get_snomed_system()

        for cond in conditions:
            display = cls._matches_code_in_normalized(cond, snomed_system, snomed_codes)
            if display is not None:
                return True, display or 'Recent major surgery or trauma'

            if cond.icd10_code and cls._matches_icd10_code(cond.icd10_code, icd10_codes):
                return True, cond.icd10_display or f"ICD-10: {cond.icd10_code}"

            for keyword in text_keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, cond.text):
                    return True, cond.text

        return False, None

    @classmethod
    def _check_medication_normalized(
        cls, medications: list[NormalizedMedication], keywords: list, nhi_codes: list, log_label: str,
    ) -> bool:
        """Check if any normalized medication matches keywords or NHI codes."""
        for med in medications:
            if med.nhi_code:
                if any(med.nhi_code == t or med.nhi_code.startswith(t) for t in nhi_codes):
                    logging.info(f"Found {log_label} via NHI code: {med.nhi_code}")
                    return True
            for keyword in keywords:
                if keyword.lower() in med.text:
                    logging.info(f"Found {log_label} via keyword '{keyword}' in: {med.text[:80]}")
                    return True
        return False

    @classmethod
    def check_oral_anticoagulation_normalized(cls, medications: list[NormalizedMedication]) -> bool:
        """Check for oral anticoagulation using pre-normalized medications."""
        med_config = config_loader.get_medication_keywords()
        oac_config = med_config.get('oral_anticoagulants', {})
        keywords = oac_config.get('generic_names', []) + oac_config.get('brand_names', [])
        nhi_codes = oac_config.get('nhi_codes', [])
        return cls._check_medication_normalized(medications, keywords, nhi_codes, "OAC")

    @classmethod
    def check_nsaids_or_corticosteroids_normalized(cls, medications: list[NormalizedMedication]) -> bool:
        """Check for NSAIDs or corticosteroids using pre-normalized medications."""
        med_config = config_loader.get_medication_keywords()
        nsaid_config = med_config.get('nsaids_corticosteroids', {})
        keywords = nsaid_config.get('nsaid_keywords', []) + nsaid_config.get('corticosteroid_keywords', [])
        nhi_codes = nsaid_config.get('nhi_codes', [])
        return cls._check_medication_normalized(medications, keywords, nhi_codes, "NSAID/Steroid")

    @classmethod
    def check_thrombocytopenia_normalized(
        cls, platelets_lab: Any | None, conditions: list[NormalizedCondition],
    ) -> bool:
        """Check for thrombocytopenia using normalized platelet value + conditions."""
        snomed_config = config_loader.get_snomed_codes('thrombocytopenia')
        threshold = snomed_config.get('threshold', {}).get('value', 100)
        icd10_codes = snomed_config.get('icd10cm_codes', [])

        # Check lab value (NormalizedLabValue or None)
        if platelets_lab is not None and platelets_lab.value is not None:
            if platelets_lab.value < threshold:
                return True

        # Check ICD-10 codes in normalized conditions
        for cond in conditions:
            if cond.icd10_code and cls._matches_icd10_code(cond.icd10_code, icd10_codes):
                return True

        return False

    @classmethod
    def check_arc_hbr_factors_normalized(cls, patient_data: NormalizedPatientData) -> dict:
        """
        Check ARC-HBR risk factors using fully normalized patient data.

        Returns the same dict shape as check_arc_hbr_factors_detailed().
        """
        conditions = patient_data.conditions
        medications = patient_data.medications

        has_thrombocytopenia = cls.check_thrombocytopenia_normalized(patient_data.platelets, conditions)
        has_bleeding_diathesis, _ = cls.check_bleeding_diathesis_normalized(conditions)
        has_active_cancer, _ = cls.check_active_cancer_normalized(conditions)
        has_liver_condition, _ = cls.check_liver_cirrhosis_normalized(conditions)
        has_nsaids = cls.check_nsaids_or_corticosteroids_normalized(medications)
        has_recent_surgery, _ = cls.check_recent_major_surgery_normalized(conditions)

        factors = [
            has_thrombocytopenia, has_bleeding_diathesis, has_active_cancer,
            has_liver_condition, has_nsaids, has_recent_surgery,
        ]
        return {
            'has_any_factor': any(factors),
            'thrombocytopenia': has_thrombocytopenia,
            'bleeding_diathesis': has_bleeding_diathesis,
            'active_malignancy': has_active_cancer,
            'liver_cirrhosis': has_liver_condition,
            'nsaids_corticosteroids': has_nsaids,
            'recent_major_surgery_trauma': has_recent_surgery,
        }


# Global instance
condition_checker = ConditionCheckerService()
