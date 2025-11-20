"""
Unit Tests for TW Core IG Adapter
Tests Taiwan-specific FHIR functionality
"""
import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.twcore_adapter import twcore_adapter, TWCoreAdapter


class TestTWCorePatient(unittest.TestCase):
    """Test TW Core IG Patient Profile support"""
    
    def test_chinese_name_extraction(self):
        """測試中文姓名提取"""
        patient = {
            "resourceType": "Patient",
            "name": [{"text": "陳加玲", "use": "official"}],
            "gender": "female",
            "birthDate": "1990-05-15"
        }
        
        demographics = twcore_adapter.extract_patient_demographics_twcore(patient)
        
        self.assertEqual(demographics['name_chinese'], "陳加玲")
        self.assertEqual(demographics['name'], "陳加玲")
        self.assertIsNone(demographics['name_english'])
        self.assertEqual(demographics['gender'], "female")
        self.assertIsNotNone(demographics['age'])
    
    def test_english_name_extraction(self):
        """測試英文姓名提取"""
        patient = {
            "resourceType": "Patient",
            "name": [{"text": "John Smith", "use": "official"}],
            "gender": "male",
            "birthDate": "1985-03-20"
        }
        
        demographics = twcore_adapter.extract_patient_demographics_twcore(patient)
        
        self.assertEqual(demographics['name_english'], "John Smith")
        self.assertEqual(demographics['name'], "John Smith")
        self.assertIsNone(demographics['name_chinese'])
    
    def test_mixed_names(self):
        """測試中英文混合姓名"""
        patient = {
            "resourceType": "Patient",
            "name": [
                {"text": "王小明", "use": "official"},
                {"text": "Wang Xiao Ming", "use": "official"}
            ],
            "gender": "male",
            "birthDate": "1980-01-01"
        }
        
        demographics = twcore_adapter.extract_patient_demographics_twcore(patient)
        
        # Chinese name should be primary
        self.assertEqual(demographics['name_chinese'], "王小明")
        self.assertEqual(demographics['name'], "王小明")
        self.assertEqual(demographics['name_english'], "Wang Xiao Ming")
    
    def test_taiwan_id_extraction(self):
        """測試身分證字號提取"""
        patient = {
            "resourceType": "Patient",
            "identifier": [
                {
                    "system": "http://www.moi.gov.tw/",
                    "type": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "NNxxx",
                            "display": "身分證字號"
                        }]
                    },
                    "value": "A123456789"
                }
            ],
            "name": [{"text": "測試病患"}]
        }
        
        demographics = twcore_adapter.extract_patient_demographics_twcore(patient)
        
        self.assertEqual(demographics['taiwan_id'], "A123456789")
    
    def test_medical_record_number_extraction(self):
        """測試病歷號提取"""
        patient = {
            "resourceType": "Patient",
            "identifier": [
                {
                    "system": "https://www.tph.mohw.gov.tw/",
                    "type": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical record number"
                        }]
                    },
                    "value": "MR20230001"
                }
            ],
            "name": [{"text": "測試病患"}]
        }
        
        demographics = twcore_adapter.extract_patient_demographics_twcore(patient)
        
        self.assertEqual(demographics['medical_record_number'], "MR20230001")


class TestTWCoreNHIMedication(unittest.TestCase):
    """Test Taiwan NHI Medication Code support"""
    
    def test_nhi_code_extraction(self):
        """測試健保藥品代碼提取"""
        medication = {
            "resourceType": "MedicationRequest",
            "medicationCodeableConcept": {
                "coding": [{
                    "system": "https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw",
                    "code": "AC45856100",
                    "display": "立普妥膜衣錠10毫克"
                }],
                "text": "立普妥膜衣錠10毫克"
            }
        }
        
        nhi_info = twcore_adapter.extract_nhi_medication_code(medication)
        
        self.assertTrue(nhi_info['has_nhi_code'])
        self.assertEqual(nhi_info['nhi_code'], "AC45856100")
        self.assertEqual(nhi_info['medication_name'], "立普妥膜衣錠10毫克")
    
    def test_12_digit_nhi_code(self):
        """測試 12 位數健保代碼辨識"""
        medication = {
            "medicationCodeableConcept": {
                "coding": [{
                    "system": "http://example.org/medication",
                    "code": "ABC123456789",  # 12-digit alphanumeric
                    "display": "測試藥品"
                }]
            }
        }
        
        nhi_info = twcore_adapter.extract_nhi_medication_code(medication)
        
        self.assertTrue(nhi_info['has_nhi_code'])
        self.assertEqual(nhi_info['nhi_code'], "ABC123456789")
    
    def test_search_nhi_medication(self):
        """測試健保藥品搜尋"""
        medications = [
            {
                "medicationCodeableConcept": {
                    "coding": [{
                        "system": "https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw",
                        "code": "AC45856100",
                        "display": "立普妥膜衣錠10毫克"
                    }]
                }
            },
            {
                "medicationCodeableConcept": {
                    "coding": [{
                        "system": "https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw",
                        "code": "BC22819100",
                        "display": "普萊維膜衣錠75毫克"
                    }]
                }
            }
        ]
        
        # Search for specific NHI code
        results = twcore_adapter.search_nhi_medication_by_code(medications, "AC45856100")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['nhi_info']['nhi_code'], "AC45856100")
        self.assertEqual(results[0]['nhi_info']['medication_name'], "立普妥膜衣錠10毫克")


class TestTWCoreICD10(unittest.TestCase):
    """Test ICD-10-CM diagnosis code support"""
    
    def test_icd10_extraction(self):
        """測試 ICD-10 診斷代碼提取"""
        condition = {
            "resourceType": "Condition",
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"
                }]
            },
            "code": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "I21.0",
                    "display": "ST elevation myocardial infarction of anterior wall"
                }],
                "text": "急性前壁心肌梗塞"
            }
        }
        
        diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
        
        self.assertTrue(diagnosis_info['has_icd10'])
        self.assertEqual(diagnosis_info['icd10_code'], "I21.0")
        self.assertEqual(diagnosis_info['condition_text'], "急性前壁心肌梗塞")
        self.assertEqual(diagnosis_info['clinical_status'], "active")
    
    def test_icd10_search(self):
        """測試 ICD-10 診斷搜尋"""
        conditions = [
            {
                "code": {
                    "coding": [{
                        "system": "http://hl7.org/fhir/sid/icd-10-cm",
                        "code": "I21.0",
                        "display": "STEMI of anterior wall"
                    }],
                    "text": "急性前壁心肌梗塞"
                }
            },
            {
                "code": {
                    "coding": [{
                        "system": "http://hl7.org/fhir/sid/icd-10-cm",
                        "code": "I21.1",
                        "display": "STEMI of inferior wall"
                    }],
                    "text": "急性下壁心肌梗塞"
                }
            },
            {
                "code": {
                    "coding": [{
                        "system": "http://hl7.org/fhir/sid/icd-10-cm",
                        "code": "I50.9",
                        "display": "Heart failure, unspecified"
                    }],
                    "text": "心臟衰竭"
                }
            }
        ]
        
        # Search for all MI conditions (I21.*)
        mi_results = twcore_adapter.search_conditions_by_icd10(conditions, "I21")
        
        self.assertEqual(len(mi_results), 2)
        
        # Search for heart failure (I50.*)
        hf_results = twcore_adapter.search_conditions_by_icd10(conditions, "I50")
        
        self.assertEqual(len(hf_results), 1)
        self.assertEqual(hf_results[0]['diagnosis_info']['icd10_code'], "I50.9")


class TestTWCoreTaiwanID(unittest.TestCase):
    """Test Taiwan ID validation"""
    
    def test_valid_taiwan_id(self):
        """測試有效的身分證字號"""
        valid_ids = ["A123456789", "B234567890", "Z987654321"]
        
        for taiwan_id in valid_ids:
            self.assertTrue(
                twcore_adapter.validate_taiwan_id(taiwan_id),
                f"{taiwan_id} should be valid"
            )
    
    def test_invalid_taiwan_id_format(self):
        """測試無效的身分證字號格式"""
        invalid_ids = [
            "123456789",      # Missing letter
            "AB12345678",     # Two letters
            "A12345678",      # Too short
            "A1234567890",    # Too long
            "a123456789",     # Lowercase letter
            "A12345678A",     # Letter at end
        ]
        
        for taiwan_id in invalid_ids:
            self.assertFalse(
                twcore_adapter.validate_taiwan_id(taiwan_id),
                f"{taiwan_id} should be invalid"
            )


class TestTWCoreResourceGeneration(unittest.TestCase):
    """Test TW Core IG compatible resource generation"""
    
    def test_generate_patient_resource(self):
        """測試產生 TW Core IG 相容的 Patient 資源"""
        demographics = {
            "name_chinese": "王小明",
            "name_english": "Wang Xiao Ming",
            "gender": "male",
            "birthDate": "1985-03-20",
            "taiwan_id": "A123456789",
            "medical_record_number": "MR20230001"
        }
        
        patient_resource = twcore_adapter.get_twcore_compatible_patient_resource(demographics)
        
        # Check resource type and profile
        self.assertEqual(patient_resource['resourceType'], "Patient")
        self.assertIn("https://twcore.mohw.gov.tw/ig/twcore/StructureDefinition/Patient-twcore", 
                     patient_resource['meta']['profile'])
        
        # Check name
        self.assertEqual(len(patient_resource['name']), 2)  # Chinese and English
        self.assertEqual(patient_resource['name'][0]['text'], "王小明")
        
        # Check identifiers
        identifiers = patient_resource['identifier']
        self.assertGreater(len(identifiers), 0)
        
        # Check Taiwan ID
        taiwan_id_found = False
        for identifier in identifiers:
            if "moi.gov.tw" in identifier['system']:
                self.assertEqual(identifier['value'], "A123456789")
                taiwan_id_found = True
        self.assertTrue(taiwan_id_found, "Taiwan ID should be in identifiers")
        
        # Check demographics
        self.assertEqual(patient_resource['gender'], "male")
        self.assertEqual(patient_resource['birthDate'], "1985-03-20")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)

