"""
Unit Tests for Condition Checker Service
Tests integration of ICD-10 and NHI Code checking
"""
import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.condition_checker import condition_checker
from services.config_loader import config_loader

class TestConditionCheckerConfigIntegration(unittest.TestCase):
    """Test that ConditionChecker uses the updated configuration"""
    
    def setUp(self):
        # Mock raw data structure
        self.empty_raw_data = {
            'conditions': [],
            'med_requests': [],
            'PLATELETS': []
        }

    def test_config_has_new_fields(self):
        """Test that configuration loaded has the new fields"""
        # Check bleeding_diathesis codes
        snomed_config = config_loader.get_snomed_codes('bleeding_diathesis')
        self.assertIn('icd10cm_codes', snomed_config)
        self.assertIn('D66', snomed_config['icd10cm_codes'])
        
        # Check medication keywords
        med_config = config_loader.get_medication_keywords()
        self.assertIn('nhi_codes', med_config['oral_anticoagulants'])
        self.assertIn('B023', med_config['oral_anticoagulants']['nhi_codes'])

    def test_check_bleeding_diathesis_icd10(self):
        """Test detecting bleeding diathesis via ICD-10"""
        conditions = [{
            "resourceType": "Condition",
            "code": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "D66",
                    "display": "Hereditary factor VIII deficiency"
                }]
            }
        }]
        
        has_condition, info = condition_checker.check_bleeding_diathesis(conditions)
        self.assertTrue(has_condition)
        self.assertIn("Hereditary factor VIII deficiency", info)

    def test_check_prior_bleeding_icd10(self):
        """Test detecting prior bleeding via ICD-10"""
        conditions = [{
            "resourceType": "Condition",
            "code": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "K92.2",
                    "display": "Gastrointestinal hemorrhage, unspecified"
                }]
            }
        }]
        
        has_condition, evidence = condition_checker.check_prior_bleeding(conditions)
        self.assertTrue(has_condition)
        # evidence is a list
        self.assertTrue(any("Gastrointestinal hemorrhage" in e for e in evidence))

    def test_check_active_cancer_icd10(self):
        """Test detecting active cancer via ICD-10"""
        conditions = [{
            "resourceType": "Condition",
            "clinicalStatus": {
                "coding": [{"code": "active", "system": "http://terminology.hl7.org/CodeSystem/condition-clinical"}]
            },
            "code": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": "C18.9", # Colon cancer
                    "display": "Malignant neoplasm of colon, unspecified"
                }]
            }
        }]
        
        has_condition, info = condition_checker.check_active_cancer(conditions)
        self.assertTrue(has_condition)
        self.assertIn("Malignant neoplasm", info)

    def test_check_oral_anticoagulation_nhi(self):
        """Test detecting OAC via NHI code"""
        medications = [{
            "resourceType": "MedicationRequest",
            "medicationCodeableConcept": {
                "coding": [{
                    "system": "https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw",
                    "code": "B023", # In our mock config as OAC
                    "display": "Warfarin 5mg"
                }]
            }
        }]
        
        result = condition_checker.check_oral_anticoagulation(medications)
        self.assertTrue(result)

    def test_check_nsaids_nhi(self):
        """Test detecting NSAIDs via NHI code"""
        medications = [{
            "resourceType": "MedicationRequest",
            "medicationCodeableConcept": {
                "coding": [{
                    "system": "https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw",
                    "code": "AC36", # In our mock config as NSAID
                    "display": "Ibuprofen"
                }]
            }
        }]
        
        result = condition_checker.check_nsaids_or_corticosteroids(medications)
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main(verbosity=2)

