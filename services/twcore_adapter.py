"""
TW Core IG Adapter Service
Taiwan Core Implementation Guide (TW Core IG) Adapter
Supports Taiwan-specific FHIR profiles and coding systems

Reference: https://twcore.mohw.gov.tw/ig/twcore/
"""
import logging
import re
from services.config_loader import config_loader


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
        Extract patient demographics following TW Core IG Patient Profile
        
        TW Core Patient Profile supports:
        - Chinese names in text field
        - Taiwan ID (身分證字號): identifier.system = "http://www.moi.gov.tw/"
        - Resident ID (居留證): identifier with type = "http://terminology.hl7.org/CodeSystem/v2-0203#PPN"
        - Medical Record Number (病歷號): identifier with hospital-specific system
        
        Args:
            patient_resource: FHIR Patient resource following TW Core IG
        
        Returns:
            Dictionary with demographics including Chinese name support
        """
        demographics = {
            "name": "Unknown",
            "name_chinese": None,  # Chinese name
            "name_english": None,  # English name
            "gender": None,
            "age": None,
            "birthDate": None,
            "taiwan_id": None,  # National ID or Resident ID
            "medical_record_number": None,  # Medical Record Number
            "identifiers": []  # All identifiers
        }
        
        if not patient_resource:
            return demographics
        
        # === 1. Extract Chinese Name (TW Core IG specific) ===
        if patient_resource.get("name"):
            for name_data in patient_resource["name"]:
                # TW Core IG: Chinese name in 'text' field
                if name_data.get("text"):
                    # Check if it's Chinese (contains Chinese characters)
                    # Check if it's Chinese (contains Chinese characters)
                    if cls._contains_chinese(name_data["text"]):
                        demographics["name_chinese"] = name_data["text"]
                        demographics["name"] = name_data["text"]  # Set as primary name
                        logging.debug(f"Extracted Chinese name from TW Core IG profile")
                    else:
                        demographics["name_english"] = name_data["text"]
                        if not demographics["name_chinese"]:
                            demographics["name"] = name_data["text"]
                
                # Also support standard FHIR structure
                elif name_data.get("family") or name_data.get("given"):
                    english_name = " ".join(name_data.get("given", []) + [name_data.get("family", "")]).strip()
                    demographics["name_english"] = english_name
                    if not demographics["name_chinese"]:
                        demographics["name"] = english_name
        
        # === 2. Extract Taiwan ID and Medical Record Number ===
        if patient_resource.get("identifier"):
            for identifier in patient_resource["identifier"]:
                system = identifier.get("system", "")
                value = identifier.get("value", "")
                id_type = identifier.get("type", {})
                
                demographics["identifiers"].append({
                    "system": system,
                    "value": value,
                    "type": id_type
                })
                
                # Taiwan National ID (身分證字號)
                if "moi.gov.tw" in system:
                    demographics["taiwan_id"] = value
                    logging.debug(f"Extracted Taiwan ID: {value[:1]}********")  # Mask for privacy
                
                # Resident Certificate Number (居留證號碼)
                elif isinstance(id_type, dict) and id_type.get("coding"):
                    for coding in id_type["coding"]:
                        if coding.get("code") == "PPN":  # Passport number / Resident ID
                            demographics["taiwan_id"] = value
                            logging.debug(f"Extracted Resident ID: {value[:2]}********")
                
                # Medical Record Number (病歷號)
                # Check for MR type code or hospital system
                is_medical_record = False
                if isinstance(id_type, dict) and id_type.get("coding"):
                    for coding in id_type["coding"]:
                        if coding.get("code") == "MR":  # Medical Record Number type
                            is_medical_record = True
                            break
                
                if is_medical_record or "tph.mohw.gov.tw" in system or "hospital" in system.lower():
                    demographics["medical_record_number"] = value
                    logging.debug(f"Extracted Medical Record Number: {value}")
        
        # === 3. Extract Gender ===
        demographics["gender"] = patient_resource.get("gender")
        
        # === 4. Extract Birth Date and Calculate Age ===
        if patient_resource.get("birthDate"):
            demographics["birthDate"] = patient_resource["birthDate"]
            try:
                import datetime as dt
                birth_date = dt.datetime.strptime(patient_resource["birthDate"], "%Y-%m-%d").date()
                today = dt.date.today()
                demographics["age"] = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            except (ValueError, TypeError):
                pass
        
        return demographics
    
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
        Extract Taiwan NHI (National Health Insurance) medication code
        
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
        
        # Extract from medicationCodeableConcept
        med_concept = medication_resource.get('medicationCodeableConcept', {})
        
        if not med_concept:
            # Try medicationReference if medicationCodeableConcept is not present
            med_ref = medication_resource.get('medicationReference', {})
            if med_ref:
                logging.info(f"Medication reference found: {med_ref.get('reference')}")
        
        # Check text field for medication name
        if med_concept.get('text'):
            nhi_info['medication_name'] = med_concept['text']
        
        # Check coding for NHI code
        codings = med_concept.get('coding', [])
        for coding in codings:
            system = coding.get('system', '')
            code = coding.get('code', '')
            display = coding.get('display', '')
            
            nhi_info['all_codes'].append({
                'system': system,
                'code': code,
                'display': display
            })
            
            # Taiwan NHI medication code
            if 'medication-nhi-tw' in system or 'nhi.gov.tw' in system:
                nhi_info['has_nhi_code'] = True
                nhi_info['nhi_code'] = code
                if display:
                    nhi_info['medication_name'] = display
                logging.info(f"Found NHI medication code: {code} - {display}")
            
            # Also check for alternative NHI code patterns (12-digit codes)
            elif code and len(code) == 12 and code.isalnum():
                nhi_info['has_nhi_code'] = True
                nhi_info['nhi_code'] = code
                if display:
                    nhi_info['medication_name'] = display
                logging.info(f"Found potential NHI code (12-digit): {code}")
        
        return nhi_info
    
    @classmethod
    def extract_icd10_diagnosis(cls, condition_resource):
        """
        Extract ICD-10-CM diagnosis codes from Condition resource
        
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
        
        # Extract condition text
        code_element = condition_resource.get('code', {})
        if code_element.get('text'):
            diagnosis_info['condition_text'] = code_element['text']
        
        # Extract clinical status
        clinical_status = condition_resource.get('clinicalStatus', {})
        if isinstance(clinical_status, dict):
            for coding in clinical_status.get('coding', []):
                if coding.get('code'):
                    diagnosis_info['clinical_status'] = coding['code']
                    break
        
        # Extract ICD-10 codes
        codings = code_element.get('coding', [])
        for coding in codings:
            system = coding.get('system', '')
            code = coding.get('code', '')
            display = coding.get('display', '')
            
            diagnosis_info['all_codes'].append({
                'system': system,
                'code': code,
                'display': display
            })
            
            # ICD-10-CM or ICD-10
            if 'icd-10' in system.lower():
                diagnosis_info['has_icd10'] = True
                diagnosis_info['icd10_code'] = code
                diagnosis_info['icd10_display'] = display or diagnosis_info['condition_text']
                
                # Determine if it's ICD-10-CM or ICD-10
                if 'icd-10-cm' in system.lower():
                    logging.info(f"Found ICD-10-CM code: {code} - {display}")
                else:
                    logging.info(f"Found ICD-10 code: {code} - {display}")
        
        return diagnosis_info
    
    @classmethod
    def search_nhi_medication_by_code(cls, medications, nhi_code):
        """
        Search for medication by NHI code in a list of medication resources
        
        Args:
            medications: List of FHIR MedicationRequest or Medication resources
            nhi_code: Taiwan NHI medication code to search for
        
        Returns:
            List of matching medications
        """
        matching_medications = []
        
        for med in medications:
            nhi_info = cls.extract_nhi_medication_code(med)
            if nhi_info['has_nhi_code'] and nhi_info['nhi_code'] == nhi_code:
                matching_medications.append({
                    'resource': med,
                    'nhi_info': nhi_info
                })
        
        return matching_medications
    
    @classmethod
    def search_conditions_by_icd10(cls, conditions, icd10_code_pattern):
        """
        Search for conditions by ICD-10 code pattern
        
        Args:
            conditions: List of FHIR Condition resources
            icd10_code_pattern: ICD-10 code or pattern (e.g., "I21" for MI)
        
        Returns:
            List of matching conditions
        """
        matching_conditions = []
        
        for condition in conditions:
            diagnosis_info = cls.extract_icd10_diagnosis(condition)
            if diagnosis_info['has_icd10']:
                icd10_code = diagnosis_info['icd10_code']
                # Check if code starts with pattern (e.g., I21.* matches I21.0, I21.1, etc.)
                if icd10_code and icd10_code.startswith(icd10_code_pattern):
                    matching_conditions.append({
                        'resource': condition,
                        'diagnosis_info': diagnosis_info
                    })
        
        return matching_conditions
    
    @classmethod
    def validate_taiwan_id(cls, taiwan_id):
        """
        Validate Taiwan National ID (身分證字號) format
        
        Format: 1 letter + 9 digits (e.g., A123456789)
        
        Args:
            taiwan_id: Taiwan ID string
        
        Returns:
            Boolean indicating if format is valid
        """
        if not taiwan_id or len(taiwan_id) != 10:
            return False
        
        # Check format: 1 letter + 9 digits
        if not re.match(r'^[A-Z][0-9]{9}$', taiwan_id):
            return False
        
        # TODO: Add checksum validation if needed
        # (Taiwan ID has a specific checksum algorithm)
        
        return True
    
    @classmethod
    def get_twcore_compatible_patient_resource(cls, demographics):
        """
        Create a TW Core IG compatible Patient resource from demographics
        
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
        
        # Add Chinese name
        if demographics.get("name_chinese"):
            patient_resource["name"].append({
                "text": demographics["name_chinese"],
                "use": "official"
            })
        
        # Add English name if available
        if demographics.get("name_english"):
            # Parse English name
            parts = demographics["name_english"].split()
            if len(parts) >= 2:
                patient_resource["name"].append({
                    "use": "official",
                    "family": parts[-1],
                    "given": parts[:-1]
                })
        
        # Add Taiwan ID
        if demographics.get("taiwan_id"):
            patient_resource["identifier"].append({
                "system": "http://www.moi.gov.tw/",
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "NNxxx",  # National ID
                        "display": "National ID"
                    }]
                },
                "value": demographics["taiwan_id"]
            })
        
        # Add Medical Record Number
        if demographics.get("medical_record_number"):
            patient_resource["identifier"].append({
                "system": "https://www.tph.mohw.gov.tw/",
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "MR",
                        "display": "Medical record number"
                    }]
                },
                "value": demographics["medical_record_number"]
            })
        
        return patient_resource


# Global instance
twcore_adapter = TWCoreAdapter()

