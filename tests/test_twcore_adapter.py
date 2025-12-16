
import unittest
from datetime import date, timedelta
from services.twcore_adapter import TWCoreAdapter

class TestTWCoreAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = TWCoreAdapter()

    # --- 1. Test extract_patient_demographics_twcore ---

    def test_extract_patient_demographics_invalid_date(self):
        """Test invalid birth date handling"""
        patient = {
            "resourceType": "Patient",
            "birthDate": "invalid-date"
        }
        dem = self.adapter.extract_patient_demographics_twcore(patient)
        self.assertIsNone(dem["age"])

    def test_extract_patient_demographics_basic(self):
        """Test basic extraction of gender, birthDate, and Age calculation"""
        birth_year = date.today().year - 30
        patient = {
            "resourceType": "Patient",
            "gender": "male",
            "birthDate": f"{birth_year}-01-01"
        }
        dem = self.adapter.extract_patient_demographics_twcore(patient)
        self.assertEqual(dem["gender"], "male")
        self.assertEqual(dem["age"], 30)
        self.assertEqual(dem["birthDate"], f"{birth_year}-01-01")

    def test_extract_patient_demographics_chinese_name(self):
        """Test extraction of Chinese name from text field"""
        patient = {
            "resourceType": "Patient",
            "name": [
                {"text": "王大明", "use": "official"}
            ]
        }
        dem = self.adapter.extract_patient_demographics_twcore(patient)
        self.assertEqual(dem["name_chinese"], "王大明")
        self.assertEqual(dem["name"], "王大明")
        self.assertIsNone(dem["name_english"])

    def test_extract_patient_demographics_english_name(self):
        """Test extraction of English name from family/given"""
        patient = {
            "resourceType": "Patient",
            "name": [
                {"family": "Doe", "given": ["John"], "text": "John Doe"}
            ]
        }
        dem = self.adapter.extract_patient_demographics_twcore(patient)
        self.assertEqual(dem["name_english"], "John Doe")
        self.assertEqual(dem["name"], "John Doe")
        self.assertIsNone(dem["name_chinese"])

    def test_extract_patient_demographics_mixed_names(self):
        """Test when both Chinese text and English parts exist"""
        patient = {
            "resourceType": "Patient",
            "name": [
                {"text": "王小美", "use": "official"},
                {"family": "Wang", "given": ["Xiao-Mei"], "use": "official"}
            ]
        }
        dem = self.adapter.extract_patient_demographics_twcore(patient)
        self.assertEqual(dem["name_chinese"], "王小美")
        self.assertEqual(dem["name"], "王小美") # Prefer Chinese as primary if available
        # The logic iterates names. If first is Chinese, it sets it.
        # Then second is English parts.
        
        # Let's verify specific behavior: 
        # Loop 1: text="王小美" -> name_chinese="王小美", name="王小美"
        # Loop 2: family="Wang" -> name_english="Xiao-Mei Wang". 
        # name remains "王小美" because name_chinese is set.
        self.assertEqual(dem["name_english"], "Xiao-Mei Wang")

    def test_extract_taiwan_id(self):
        """Test extraction of Taiwan National ID"""
        patient = {
            "resourceType": "Patient",
            "identifier": [
                {
                    "system": "http://www.moi.gov.tw/",
                    "value": "A123456789"
                }
            ]
        }
        dem = self.adapter.extract_patient_demographics_twcore(patient)
        self.assertEqual(dem["taiwan_id"], "A123456789")

    def test_extract_resident_id(self):
        """Test extraction of Resident ID via PPN code"""
        patient = {
            "resourceType": "Patient",
            "identifier": [
                {
                    "type": {
                        "coding": [{"code": "PPN", "system": "http://terminology.hl7.org/CodeSystem/v2-0203"}]
                    },
                    "value": "RC12345678"
                }
            ]
        }
        dem = self.adapter.extract_patient_demographics_twcore(patient)
        self.assertEqual(dem["taiwan_id"], "RC12345678")

    def test_extract_medical_record_number(self):
        """Test extraction of MRN"""
        patient = {
            "resourceType": "Patient",
            "identifier": [
                {
                    "type": {
                        "coding": [{"code": "MR"}]
                    },
                    "value": "MRN-001"
                }
            ]
        }
        dem = self.adapter.extract_patient_demographics_twcore(patient)
        self.assertEqual(dem["medical_record_number"], "MRN-001")

        # Test alternative system match
        patient2 = {
            "resourceType": "Patient",
            "identifier": [
                {
                    "system": "https://www.tph.mohw.gov.tw/",
                    "value": "MRN-002"
                }
            ]
        }
        dem2 = self.adapter.extract_patient_demographics_twcore(patient2)
        self.assertEqual(dem2["medical_record_number"], "MRN-002")

    def test_extract_demographics_empty(self):
        """Test empty input"""
        dem = self.adapter.extract_patient_demographics_twcore(None)
        self.assertEqual(dem["name"], "Unknown")
        self.assertIsNone(dem["age"])

        dem = self.adapter.extract_patient_demographics_twcore({})
        self.assertEqual(dem["name"], "Unknown")

    # --- 2. Test _contains_chinese ---

    def test_contains_chinese(self):
        self.assertTrue(self.adapter._contains_chinese("王"))
        self.assertTrue(self.adapter._contains_chinese("ABC王"))
        self.assertFalse(self.adapter._contains_chinese("ABC"))
        self.assertFalse(self.adapter._contains_chinese(""))
        self.assertFalse(self.adapter._contains_chinese(None))

    # --- 3. Test extract_nhi_medication_code ---

    def test_extract_nhi_medication_code_standard(self):
        """Test NHI code extraction from standard coding"""
        med = {
            "resourceType": "MedicationRequest",
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw",
                        "code": "AC12345678",
                        "display": "Aspirin"
                    }
                ]
            }
        }
        info = self.adapter.extract_nhi_medication_code(med)
        self.assertTrue(info["has_nhi_code"])
        self.assertEqual(info["nhi_code"], "AC12345678")
        self.assertEqual(info["medication_name"], "Aspirin")

    def test_extract_nhi_medication_code_pattern(self):
        """Test NHI code extraction from 12-digit pattern"""
        med = {
            "resourceType": "MedicationRequest",
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://other.system/rx",
                        "code": "A01234567890", # 12 alphanumeric chars
                        "display": "Drug X"
                    }
                ]
            }
        }
        info = self.adapter.extract_nhi_medication_code(med)
        self.assertTrue(info["has_nhi_code"])
        self.assertEqual(info["nhi_code"], "A01234567890")

    def test_extract_nhi_medication_reference(self):
        """Test extraction via medicationReference fallback"""
        med = {
            "resourceType": "MedicationRequest",
            "medicationReference": {"reference": "Medication/123"}
        }
        with self.assertLogs(level='INFO') as cm:
            self.adapter.extract_nhi_medication_code(med)
            self.assertTrue(any("Medication reference found" in o for o in cm.output))

    # --- 4. Test extract_icd10_diagnosis ---

    def test_extract_icd10_diagnosis(self):
        condition = {
            "resourceType": "Condition",
            "code": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/sid/icd-10-cm",
                        "code": "I21.0",
                        "display": "Acute transmural MI"
                    }
                ],
                "text": "Heart Attack"
            },
            "clinicalStatus": {
                "coding": [{"code": "active"}]
            }
        }
        info = self.adapter.extract_icd10_diagnosis(condition)
        self.assertTrue(info["has_icd10"])
        self.assertEqual(info["icd10_code"], "I21.0")
        self.assertEqual(info["condition_text"], "Heart Attack")
        self.assertEqual(info["clinical_status"], "active")

    # --- 5. Test search_nhi_medication_by_code ---

    def test_search_nhi_medication_by_code(self):
        meds = [
            {"medicationCodeableConcept": {"coding": [{"system": "nhi.gov.tw", "code": "A"}]}},
             {"medicationCodeableConcept": {"coding": [{"system": "nhi.gov.tw", "code": "B"}]}},
        ]
        results = self.adapter.search_nhi_medication_by_code(meds, "A")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['nhi_info']['nhi_code'], "A")

    # --- 6. Test search_conditions_by_icd10 ---

    def test_search_conditions_by_icd10(self):
        conditions = [
            {"code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "I21.0"}]}},
            {"code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "I25.1"}]}},
            {"code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "I21.9"}]}},
        ]
        results = self.adapter.search_conditions_by_icd10(conditions, "I21")
        self.assertEqual(len(results), 2) # I21.0 and I21.9

    # --- 7. Test validate_taiwan_id ---

    def test_validate_taiwan_id(self):
        self.assertTrue(self.adapter.validate_taiwan_id("A123456789"))
        self.assertFalse(self.adapter.validate_taiwan_id("A12345678")) # Too short
        self.assertFalse(self.adapter.validate_taiwan_id("1234567890")) # No letter
        self.assertFalse(self.adapter.validate_taiwan_id("AA23456789")) # Two letters
        self.assertFalse(self.adapter.validate_taiwan_id(None))

    # --- 8. Test get_twcore_compatible_patient_resource ---

    def test_get_twcore_compatible_patient_resource(self):
        demographics = {
            "name_chinese": "陳小明",
            "name_english": "Xiao-Ming Chen",
            "gender": "male",
            "birthDate": "1990-01-01",
            "taiwan_id": "A123456789",
            "medical_record_number": "MRN-999"
        }
        resource = self.adapter.get_twcore_compatible_patient_resource(demographics)
        
        self.assertEqual(resource["resourceType"], "Patient")
        self.assertEqual(resource["gender"], "male")
        
        # Check Chinese Name
        chinese_name_entry = next((n for n in resource["name"] if n.get("text") == "陳小明"), None)
        self.assertIsNotNone(chinese_name_entry)
        
        # Check English Name
        english_name_entry = next((n for n in resource["name"] if n.get("family") == "Chen"), None)
        self.assertIsNotNone(english_name_entry)
        
        # Check IDs
        tw_id = next((i for i in resource["identifier"] if i.get("value") == "A123456789"), None)
        self.assertIsNotNone(tw_id)
        self.assertIn("moi.gov.tw", tw_id["system"])
        
        mrn = next((i for i in resource["identifier"] if i.get("value") == "MRN-999"), None)
        self.assertIsNotNone(mrn)


if __name__ == '__main__':
    unittest.main()
