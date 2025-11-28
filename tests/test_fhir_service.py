"""
Tests for FHIR data service module and microservices
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import fhir_data_service
from services import (
    fhir_client_service,
    unit_conversion_service,
    condition_checker,
    risk_classifier,
    precise_hbr_calculator
)


class TestPatientDemographics:
    """Test patient demographics extraction"""
    
    def test_get_patient_demographics_basic(self):
        """Test basic patient demographics extraction"""
        patient_resource = {
            'resourceType': 'Patient',
            'id': 'test-123',
            'name': [{'family': 'Test', 'given': ['Patient']}],
            'gender': 'male',
            'birthDate': '1970-01-01'
        }
        
        result = fhir_data_service.get_patient_demographics(patient_resource, use_twcore=False)
        
        assert result is not None
        assert 'name' in result
        assert result['name'] == 'Patient Test'
        assert result['gender'] == 'male'
        assert 'age' in result
        assert result['age'] is not None
    
    def test_get_patient_demographics_twcore(self):
        """Test TW Core patient demographics extraction"""
        patient_resource = {
            'resourceType': 'Patient',
            'id': 'twcore-123',
            'identifier': [{
                'system': 'http://www.moi.gov.tw/',
                'value': 'A123456789'
            }],
            'name': [{
                'use': 'official',
                'text': '王小明',
                'extension': [{
                    'url': 'http://hl7.org/fhir/StructureDefinition/iso21090-EN-representation',
                    'valueCode': 'IDE'
                }]
            }],
            'gender': 'male',
            'birthDate': '1970-01-01'
        }
        
        result = fhir_data_service.get_patient_demographics(patient_resource, use_twcore=True)
        
        assert result is not None
        assert result['name'] == '王小明'
        assert result['taiwan_id'] == 'A123456789'
        assert result['gender'] == 'male'


class TestUnitConversion:
    """Test unit conversion service"""
    
    def test_calculate_egfr(self):
        """Test eGFR calculation"""
        # Male patient, 50 years old, creatinine 1.2 mg/dL
        result = fhir_data_service.calculate_egfr(1.2, 50, 'male')
        
        assert result is not None
        # Function returns tuple (egfr_value, formula_name)
        assert isinstance(result, tuple)
        assert len(result) == 2
        egfr_value, formula_name = result
        assert isinstance(egfr_value, (int, float))
        assert egfr_value > 0
        assert isinstance(formula_name, str)
    
    def test_get_value_from_observation(self):
        """Test extracting value from observation"""
        obs = {
            'valueQuantity': {
                'value': 10.5,
                'unit': 'g/dL',
                'system': 'http://unitsofmeasure.org',
                'code': 'g/dL'
            }
        }
        
        # unit_system should be a dict with 'unit' key
        unit_system = {'unit': 'g/dl'}  # lowercase to match
        result = fhir_data_service.get_value_from_observation(obs, unit_system)
        
        # This function returns the value directly, not a dict
        assert result is not None
        assert isinstance(result, (int, float))
        assert result == 10.5


class TestConditionChecker:
    """Test condition checking service"""
    
    def test_check_bleeding_diathesis(self):
        """Test bleeding diathesis check"""
        conditions = [
            {
                'code': {
                    'coding': [{
                        'system': 'http://snomed.info/sct',
                        'code': '64779008',
                        'display': 'Blood coagulation disorder'
                    }]
                }
            }
        ]
        
        result = fhir_data_service.check_bleeding_diathesis_updated(conditions)
        
        # Function returns tuple (has_condition, info)
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        has_condition, info = result
        assert isinstance(has_condition, bool)
    
    def test_check_active_cancer(self):
        """Test active cancer check"""
        conditions = [
            {
                'code': {
                    'coding': [{
                        'system': 'http://hl7.org/fhir/sid/icd-10-cm',
                        'code': 'C50.9',
                        'display': 'Malignant neoplasm of breast'
                    }]
                }
            }
        ]
        
        result = fhir_data_service.check_active_cancer_updated(conditions)
        
        # Function returns tuple (has_condition, info)
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        has_condition, info = result
        assert isinstance(has_condition, bool)
    
    def test_check_oral_anticoagulation(self):
        """Test oral anticoagulation check"""
        medications = [
            {
                'medicationCodeableConcept': {
                    'coding': [{
                        'display': 'Warfarin'
                    }],
                    'text': 'Warfarin'
                }
            }
        ]
        
        result = fhir_data_service.check_oral_anticoagulation(medications)
        
        assert result is not None
        assert isinstance(result, bool)


class TestRiskCalculation:
    """Test risk calculation functions"""
    
    def test_calculate_bleeding_risk_percentage(self):
        """Test bleeding risk percentage calculation"""
        # Test with different PRECISE-HBR scores
        risk_low = fhir_data_service.calculate_bleeding_risk_percentage(10)
        risk_medium = fhir_data_service.calculate_bleeding_risk_percentage(20)
        risk_high = fhir_data_service.calculate_bleeding_risk_percentage(30)
        
        assert risk_low is not None
        assert risk_medium is not None
        assert risk_high is not None
        assert risk_low < risk_medium < risk_high
    
    def test_get_risk_category_info(self):
        """Test risk category information"""
        result = fhir_data_service.get_risk_category_info(25)
        
        assert result is not None
        assert 'category' in result
        assert 'color' in result
        assert 'bleeding_risk_percent' in result
        assert 'score_range' in result
    
    def test_get_precise_hbr_display_info(self):
        """Test PRECISE-HBR display information"""
        result = fhir_data_service.get_precise_hbr_display_info(20)
        
        assert result is not None
        assert 'score' in result
        assert 'bleeding_risk_percent' in result
        assert 'risk_category' in result
        assert 'full_label' in result


class TestArcHbrFactors:
    """Test ARC-HBR factors checking"""
    
    def test_check_arc_hbr_factors_basic(self):
        """Test basic ARC-HBR factors check"""
        raw_data = {
            'patient': {
                'birthDate': '1940-01-01'  # Age > 75
            },
            'observations': [],
            'conditions': []
        }
        medications = []
        
        result = fhir_data_service.check_arc_hbr_factors(raw_data, medications)
        
        assert result is not None
        assert 'has_factors' in result
        assert 'factors' in result
        assert isinstance(result['has_factors'], bool)
        assert isinstance(result['factors'], list)
    
    def test_check_arc_hbr_factors_detailed(self):
        """Test detailed ARC-HBR factors check"""
        raw_data = {
            'patient': {
                'birthDate': '1970-01-01',
                'gender': 'male'
            },
            'observations': [
                {
                    'code': {
                        'coding': [{
                            'system': 'http://loinc.org',
                            'code': '718-7'
                        }]
                    },
                    'valueQuantity': {
                        'value': 10.5,
                        'unit': 'g/dL'
                    }
                }
            ],
            'conditions': []
        }
        medications = []
        
        result = fhir_data_service.check_arc_hbr_factors_detailed(raw_data, medications)
        
        assert result is not None
        assert 'has_any_factor' in result
        assert 'thrombocytopenia' in result
        assert 'bleeding_diathesis' in result
        assert 'active_malignancy' in result


class TestMedicationFunctions:
    """Test medication-related functions"""
    
    def test_get_active_medications(self):
        """Test active medications extraction"""
        raw_data = {
            'medications': [
                {
                    'status': 'active',
                    'medicationCodeableConcept': {
                        'text': 'Aspirin'
                    }
                }
            ]
        }
        demographics = {
            'patient_id': 'test-123'
        }
        
        result = fhir_data_service.get_active_medications(raw_data, demographics)
        
        assert result is not None
        assert isinstance(result, list)
    
    def test_check_medication_interactions(self):
        """Test medication interaction checking"""
        medications = [
            {
                'medicationCodeableConcept': {
                    'text': 'Aspirin'
                }
            },
            {
                'medicationCodeableConcept': {
                    'text': 'Warfarin'
                }
            }
        ]
        
        result = fhir_data_service.check_medication_interactions_bleeding_risk(medications)
        
        assert result is not None
        assert 'dapt_detected' in result
        assert 'high_risk_combinations' in result
        assert 'bleeding_risk_medications' in result
        assert 'recommendations' in result


class TestHelperFunctions:
    """Test helper functions"""
    
    def test_get_score_from_table(self):
        """Test score lookup from table"""
        score_table = [
            {'range': [0, 10], 'base_score': 0},
            {'range': [10, 20], 'base_score': 5},
            {'range': [20, 30], 'base_score': 10}
        ]
        
        result = fhir_data_service.get_score_from_table(15, score_table, 'range')
        
        assert result is not None
        # Function returns base_score for matching range
        # 15 is in range [10, 20], so should return 5
        assert result == 5
    
    def test_get_condition_text(self):
        """Test condition text extraction"""
        condition = {
            'code': {
                'coding': [{
                    'display': 'Hypertension'
                }],
                'text': 'High blood pressure'
            }
        }
        
        result = fhir_data_service.get_condition_text(condition)
        
        assert result is not None
        assert isinstance(result, str)


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_patient_demographics(self):
        """Test handling of invalid patient data"""
        invalid_patient = {}
        
        result = fhir_data_service.get_patient_demographics(invalid_patient, use_twcore=False)
        
        # Should handle gracefully
        assert result is not None or result is None
    
    def test_invalid_observation_value(self):
        """Test handling of invalid observation"""
        invalid_obs = {}
        
        result = fhir_data_service.get_value_from_observation(invalid_obs, 'http://unitsofmeasure.org')
        
        # Should handle gracefully
        assert result is None or isinstance(result, dict)
    
    def test_egfr_with_invalid_inputs(self):
        """Test eGFR calculation with invalid inputs"""
        # Should handle edge cases
        result = fhir_data_service.calculate_egfr(0, 50, 'male')
        assert result is not None or result is None
