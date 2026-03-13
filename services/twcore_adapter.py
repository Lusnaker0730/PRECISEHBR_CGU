"""
TW Core IG Adapter Service
Taiwan Core Implementation Guide (TW Core IG) Adapter
Supports Taiwan-specific FHIR profiles and coding systems

Reference: https://twcore.mohw.gov.tw/ig/twcore/
"""
import datetime as dt
import logging
import re


class TWCoreAdapter:
    """
    Adapter for Taiwan Core Implementation Guide (TW Core IG)
    
    Supports:
    1. Chinese name format (text field in Patient.name)
    2. Taiwan NHI medication codes (健保藥品代碼)
    3. ICD-10-CM diagnosis codes
    """
    
    # Taiwan-specific coding systems
    CODING_SYSTEMS = {
        'nhi_medication': 'https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw',
        'icd10cm': 'http://hl7.org/fhir/sid/icd-10-cm',
        'icd10': 'http://hl7.org/fhir/sid/icd-10',
        'tw_patient_id': 'http://www.moi.gov.tw/',  # 身分證字號
        'tw_resident_id': 'http://terminology.hl7.org/CodeSystem/v2-0203',  # 居留證
        'medical_record_number': 'https://www.tph.mohw.gov.tw/',  # 病歷號
    }
    
    @classmethod
    def extract_patient_demographics_twcore(cls, patient_resource):
        """
        Extract patient demographics following TW Core IG Patient Profile.

        TW Core Patient Profile supports:
        - Chinese names in text field
        - Taiwan ID: identifier.system = "http://www.moi.gov.tw/"
        - Resident ID: identifier with type code "PPN"
        - Medical Record Number: identifier with type code "MR"

        Args:
            patient_resource: FHIR Patient resource following TW Core IG

        Returns:
            Dictionary with demographics including Chinese name support
        """
        demographics = {
            "name": "Unknown",
            "name_chinese": None,
            "name_english": None,
            "gender": None,
            "age": None,
            "birthDate": None,
            "taiwan_id": None,
            "medical_record_number": None,
            "identifiers": []
        }

        if not patient_resource:
            return demographics

        cls._extract_names(patient_resource, demographics)
        cls._extract_identifiers(patient_resource, demographics)
        demographics["gender"] = patient_resource.get("gender")
        cls._extract_birth_date_and_age(patient_resource, demographics)

        return demographics

    @classmethod
    def _extract_names(cls, patient_resource, demographics):
        """Extract Chinese and English names from patient resource.
        
        Prioritizes names by 'use' field:
        1. 'official' - Legal name
        2. 'usual' - Commonly used name
        3. First available name if no official/usual found
        """
        names = patient_resource.get("name", [])
        if not names:
            return
        
        # Sort names by priority: official first, then usual, then others
        def name_priority(name_data):
            use = name_data.get("use", "")
            if use == "official":
                return 0
            elif use == "usual":
                return 1
            elif use == "old":
                return 99  # Old names should be last
            else:
                return 2
        
        sorted_names = sorted(names, key=name_priority)
        
        # Extract names: collect both Chinese and English from all entries
        for name_data in sorted_names:
            text = name_data.get("text")
            use = name_data.get("use", "unknown")

            if text:
                if cls._contains_chinese(text):
                    if not demographics["name_chinese"]:
                        demographics["name_chinese"] = text
                        demographics["name"] = text
                        logging.debug(f"Extracted Chinese name (use={use}) from TW Core IG profile")
                else:
                    if not demographics["name_english"]:
                        demographics["name_english"] = text
                        if not demographics["name_chinese"]:
                            demographics["name"] = text
                        logging.debug(f"Extracted English name (use={use}): {text}")
            elif name_data.get("family") or name_data.get("given"):
                if not demographics["name_english"]:
                    english_name = " ".join(
                        name_data.get("given", []) + [name_data.get("family", "")]
                    ).strip()
                    demographics["name_english"] = english_name
                    if not demographics["name_chinese"]:
                        demographics["name"] = english_name
                    logging.debug(f"Extracted constructed name (use={use}): {english_name}")

    @classmethod
    def _extract_identifiers(cls, patient_resource, demographics):
        """Extract Taiwan ID, Resident ID, and Medical Record Number."""
        for identifier in patient_resource.get("identifier", []):
            system = identifier.get("system", "")
            value = identifier.get("value", "")
            id_type = identifier.get("type", {})

            demographics["identifiers"].append({
                "system": system,
                "value": value,
                "type": id_type
            })

            type_code = cls._get_identifier_type_code(id_type)

            if "moi.gov.tw" in system:
                demographics["taiwan_id"] = value
                logging.debug("Extracted Taiwan ID: %s********", value[:1] if value else "")
            elif type_code == "PPN":
                demographics["taiwan_id"] = value
                logging.debug("Extracted Resident ID: %s********", value[:2] if value else "")

            is_medical_record = (
                type_code == "MR" or
                "tph.mohw.gov.tw" in system or
                "hospital" in system.lower()
            )
            if is_medical_record:
                demographics["medical_record_number"] = value
                logging.debug("Extracted Medical Record Number: %s", value)

    @classmethod
    def _get_identifier_type_code(cls, id_type):
        """Extract the first type code from an identifier type."""
        if not isinstance(id_type, dict):
            return None
        for coding in id_type.get("coding", []):
            code = coding.get("code")
            if code:
                return code
        return None

    @classmethod
    def _extract_birth_date_and_age(cls, patient_resource, demographics):
        """Extract birth date and calculate age."""
        birth_date_str = patient_resource.get("birthDate")
        if not birth_date_str:
            return

        demographics["birthDate"] = birth_date_str
        try:
            birth_date = dt.datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            today = dt.date.today()
            had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
            demographics["age"] = today.year - birth_date.year - (0 if had_birthday else 1)
        except (ValueError, TypeError):
            pass
    
    @classmethod
    def _contains_chinese(cls, text):
        """Check if text contains Chinese characters"""
        if not text:
            return False
        # Chinese character Unicode ranges: \u4e00-\u9fff (CJK Unified Ideographs)
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    @classmethod
    def extract_nhi_medication_code(cls, medication_resource):
        """
        Extract Taiwan NHI (National Health Insurance) medication code.

        NHI Code System: https://info.nhi.gov.tw/INAE3000/INAE3000S01
        FHIR System URL: https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw

        Args:
            medication_resource: FHIR MedicationRequest or Medication resource

        Returns:
            Dictionary with NHI code information
        """
        nhi_info = {
            "has_nhi_code": False,
            "nhi_code": None,
            "medication_name": None,
            "all_codes": []
        }

        if not medication_resource:
            return nhi_info

        med_concept = medication_resource.get('medicationCodeableConcept', {})

        if not med_concept:
            med_ref = medication_resource.get('medicationReference', {})
            if med_ref:
                logging.info("Medication reference found: %s", med_ref.get('reference'))
            return nhi_info

        nhi_info['medication_name'] = med_concept.get('text')

        for coding in med_concept.get('coding', []):
            system = coding.get('system', '')
            code = coding.get('code', '')
            display = coding.get('display', '')

            nhi_info['all_codes'].append({
                'system': system,
                'code': code,
                'display': display
            })

            if cls._is_nhi_code(system, code):
                nhi_info['has_nhi_code'] = True
                nhi_info['nhi_code'] = code
                if display:
                    nhi_info['medication_name'] = display
                logging.info("Found NHI medication code: %s - %s", code, display)

        return nhi_info

    @classmethod
    def _is_nhi_code(cls, system, code):
        """Check if code is a Taiwan NHI medication code."""
        if 'medication-nhi-tw' in system or 'nhi.gov.tw' in system:
            return True
        if code and len(code) == 12 and code.isalnum():
            return True
        return False
    
    @classmethod
    def extract_icd10_diagnosis(cls, condition_resource):
        """
        Extract ICD-10-CM diagnosis codes from Condition resource.

        ICD-10-CM System: http://hl7.org/fhir/sid/icd-10-cm
        ICD-10 System: http://hl7.org/fhir/sid/icd-10

        Args:
            condition_resource: FHIR Condition resource

        Returns:
            Dictionary with ICD-10 diagnosis information
        """
        diagnosis_info = {
            "has_icd10": False,
            "icd10_code": None,
            "icd10_display": None,
            "condition_text": None,
            "clinical_status": None,
            "all_codes": []
        }

        if not condition_resource:
            return diagnosis_info

        code_element = condition_resource.get('code', {})
        diagnosis_info['condition_text'] = code_element.get('text')
        diagnosis_info['clinical_status'] = cls._extract_clinical_status(condition_resource)

        for coding in code_element.get('coding', []):
            system = coding.get('system', '')
            code = coding.get('code', '')
            display = coding.get('display', '')

            diagnosis_info['all_codes'].append({
                'system': system,
                'code': code,
                'display': display
            })

            if 'icd-10' in system.lower():
                diagnosis_info['has_icd10'] = True
                diagnosis_info['icd10_code'] = code
                diagnosis_info['icd10_display'] = display or diagnosis_info['condition_text']
                code_type = "ICD-10-CM" if 'icd-10-cm' in system.lower() else "ICD-10"
                logging.info("Found %s code: %s - %s", code_type, code, display)

        return diagnosis_info

    @classmethod
    def _extract_clinical_status(cls, condition_resource):
        """Extract the first clinical status code from a condition."""
        clinical_status = condition_resource.get('clinicalStatus', {})
        if not isinstance(clinical_status, dict):
            return None
        for coding in clinical_status.get('coding', []):
            code = coding.get('code')
            if code:
                return code
        return None
    
    @classmethod
    def search_nhi_medication_by_code(cls, medications, nhi_code):
        """
        Search for medication by NHI code in a list of medication resources.

        Args:
            medications: List of FHIR MedicationRequest or Medication resources
            nhi_code: Taiwan NHI medication code to search for

        Returns:
            List of matching medications with resource and nhi_info
        """
        results = []
        for med in medications:
            nhi_info = cls.extract_nhi_medication_code(med)
            if nhi_info['has_nhi_code'] and nhi_info['nhi_code'] == nhi_code:
                results.append({'resource': med, 'nhi_info': nhi_info})
        return results

    @classmethod
    def search_conditions_by_icd10(cls, conditions, icd10_code_pattern):
        """
        Search for conditions by ICD-10 code pattern.

        Args:
            conditions: List of FHIR Condition resources
            icd10_code_pattern: ICD-10 code or pattern (e.g., "I21" for MI)

        Returns:
            List of matching conditions with resource and diagnosis_info
        """
        results = []
        for condition in conditions:
            diagnosis_info = cls.extract_icd10_diagnosis(condition)
            icd10_code = diagnosis_info.get('icd10_code')
            if diagnosis_info['has_icd10'] and icd10_code and icd10_code.startswith(icd10_code_pattern):
                results.append({'resource': condition, 'diagnosis_info': diagnosis_info})
        return results

    @classmethod
    def validate_taiwan_id(cls, taiwan_id):
        """
        Validate Taiwan National ID format: 1 letter + 9 digits (e.g., A123456789).

        Args:
            taiwan_id: Taiwan ID string

        Returns:
            Boolean indicating if format is valid
        """
        if not taiwan_id or len(taiwan_id) != 10:
            return False
        return bool(re.match(r'^[A-Z][0-9]{9}$', taiwan_id))
    
    @classmethod
    def get_twcore_compatible_patient_resource(cls, demographics):
        """
        Create a TW Core IG compatible Patient resource from demographics.

        Args:
            demographics: Dictionary with patient demographics

        Returns:
            Dictionary representing FHIR Patient resource following TW Core IG
        """
        patient_resource = {
            "resourceType": "Patient",
            "meta": {
                "profile": [
                    "https://twcore.mohw.gov.tw/ig/twcore/StructureDefinition/Patient-twcore"
                ]
            },
            "identifier": [],
            "name": [],
            "gender": demographics.get("gender"),
            "birthDate": demographics.get("birthDate")
        }

        cls._add_names_to_resource(demographics, patient_resource)
        cls._add_identifiers_to_resource(demographics, patient_resource)

        return patient_resource

    @classmethod
    def _add_names_to_resource(cls, demographics, patient_resource):
        """Add Chinese and English names to patient resource."""
        if demographics.get("name_chinese"):
            patient_resource["name"].append({
                "text": demographics["name_chinese"],
                "use": "official"
            })

        english_name = demographics.get("name_english")
        if english_name:
            parts = english_name.split()
            if len(parts) >= 2:
                patient_resource["name"].append({
                    "use": "official",
                    "family": parts[-1],
                    "given": parts[:-1]
                })

    @classmethod
    def _add_identifiers_to_resource(cls, demographics, patient_resource):
        """Add Taiwan ID and Medical Record Number to patient resource."""
        v2_system = "http://terminology.hl7.org/CodeSystem/v2-0203"

        if demographics.get("taiwan_id"):
            patient_resource["identifier"].append({
                "system": "http://www.moi.gov.tw/",
                "type": {
                    "coding": [{
                        "system": v2_system,
                        "code": "NNxxx",
                        "display": "National ID"
                    }]
                },
                "value": demographics["taiwan_id"]
            })

        if demographics.get("medical_record_number"):
            patient_resource["identifier"].append({
                "system": "https://www.tph.mohw.gov.tw/",
                "type": {
                    "coding": [{
                        "system": v2_system,
                        "code": "MR",
                        "display": "Medical record number"
                    }]
                },
                "value": demographics["medical_record_number"]
            })


    @classmethod
    def get_patient_demographics(cls, patient_resource, use_twcore=True):
        """
        Extract key demographics from a FHIR Patient resource.

        Supports Taiwan Core IG (TW Core IG) for Taiwan-specific fields:
        - Chinese name support (text field)
        - Taiwan ID (National ID) / Resident ID
        - Medical Record Number

        Args:
            patient_resource: FHIR Patient resource dictionary
            use_twcore: If True, use TW Core IG adapter for enhanced Taiwan support

        Returns:
            Dictionary with name, gender, age, birthDate, and Taiwan-specific fields
        """
        if use_twcore:
            return cls.extract_patient_demographics_twcore(patient_resource)

        import datetime as dt

        demographics = {
            "name": "Unknown",
            "gender": None,
            "age": None,
            "birthDate": None,
        }

        if not patient_resource:
            return demographics

        # Extract name
        name_list = patient_resource.get("name")
        if name_list:
            name_data = name_list[0]
            if name_data.get("text"):
                demographics["name"] = name_data["text"]
            else:
                name_parts = name_data.get("given", []) + [name_data.get("family", "")]
                demographics["name"] = " ".join(name_parts).strip()

        demographics["gender"] = patient_resource.get("gender")

        # Calculate age from birthDate
        birth_date_str = patient_resource.get("birthDate")
        if birth_date_str:
            demographics["birthDate"] = birth_date_str
            try:
                birth_date = dt.datetime.strptime(birth_date_str, "%Y-%m-%d").date()
                today = dt.date.today()
                age = today.year - birth_date.year
                if (today.month, today.day) < (birth_date.month, birth_date.day):
                    age -= 1
                demographics["age"] = age
            except (ValueError, TypeError):
                pass

        return demographics


# Global instance
twcore_adapter = TWCoreAdapter()

