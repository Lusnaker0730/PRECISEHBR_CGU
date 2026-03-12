"""
Unit Tests for Unit Conversion Service

Tests for laboratory value unit conversions and eGFR calculations.
"""
import pytest
from services.unit_conversion_service import UnitConversionService, unit_converter



pytestmark = [
    pytest.mark.requirement("SRS-003"),
    pytest.mark.risk("RISK-003"),
    pytest.mark.design("SDS-003"),
]

class TestGetValueFromObservation:
    """Tests for get_value_from_observation method"""
    
    def test_returns_none_for_none_input(self):
        """Should return None for None observation"""
        result = unit_converter.get_value_from_observation(None, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result is None
    
    def test_returns_none_for_non_dict_input(self):
        """Should return None for non-dictionary observation"""
        result = unit_converter.get_value_from_observation("invalid", unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result is None
    
    def test_returns_none_for_missing_value_quantity(self):
        """Should return None when valueQuantity is missing"""
        obs = {'status': 'final'}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result is None
    
    def test_returns_none_for_null_value(self):
        """Should return None when value is null"""
        obs = {'valueQuantity': {'value': None, 'unit': 'g/dL'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result is None
    
    def test_returns_none_for_non_numeric_value(self):
        """Should return None when value is not numeric"""
        obs = {'valueQuantity': {'value': 'twelve', 'unit': 'g/dL'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result is None


class TestHemoglobinConversion:
    """Tests for Hemoglobin unit conversions"""
    
    def test_direct_match_g_dl(self):
        """Should return value directly when unit matches target"""
        obs = {'valueQuantity': {'value': 12.5, 'unit': 'g/dL'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result == 12.5
    
    def test_case_insensitive_match(self):
        """Should match units case-insensitively"""
        obs = {'valueQuantity': {'value': 12.5, 'unit': 'G/DL'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result == 12.5
    
    def test_convert_g_l_to_g_dl(self):
        """Should convert g/L to g/dL (factor: 0.1)"""
        obs = {'valueQuantity': {'value': 120, 'unit': 'g/L'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result == 12.0
    
    def test_convert_mmol_l_to_g_dl(self):
        """Should convert mmol/L to g/dL (factor: 1.61135)"""
        obs = {'valueQuantity': {'value': 7.5, 'unit': 'mmol/L'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result == pytest.approx(12.085, rel=0.01)
    
    def test_returns_none_for_unknown_unit(self):
        """Should return None for unknown unit"""
        obs = {'valueQuantity': {'value': 12.5, 'unit': 'unknown_unit'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result is None


class TestCreatinineConversion:
    """Tests for Creatinine unit conversions"""
    
    def test_direct_match_mg_dl(self):
        """Should return value directly when unit matches target"""
        obs = {'valueQuantity': {'value': 1.2, 'unit': 'mg/dL'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['CREATININE'])
        assert result == 1.2
    
    def test_convert_umol_l_to_mg_dl(self):
        """Should convert µmol/L to mg/dL (factor: 0.0113)"""
        obs = {'valueQuantity': {'value': 100, 'unit': 'umol/L'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['CREATININE'])
        assert result == pytest.approx(1.13, rel=0.01)


class TestWBCConversion:
    """Tests for WBC unit conversions"""
    
    def test_direct_match(self):
        """Should return value directly when unit matches target"""
        obs = {'valueQuantity': {'value': 8.5, 'unit': '10*9/L'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['WBC'])
        assert result == 8.5
    
    def test_convert_k_ul(self):
        """Should convert K/µL to 10^9/L (factor: 1.0)"""
        obs = {'valueQuantity': {'value': 8.5, 'unit': 'K/uL'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['WBC'])
        assert result == 8.5
    
    def test_convert_cells_per_ul(self):
        """Should convert /µL to 10^9/L (factor: 0.001)"""
        obs = {'valueQuantity': {'value': 8500, 'unit': '/uL'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['WBC'])
        assert result == 8.5


class TestEGFRConversion:
    """Tests for eGFR unit conversions"""
    
    def test_standard_format(self):
        """Should handle standard eGFR unit format"""
        obs = {'valueQuantity': {'value': 85, 'unit': 'mL/min/1.73m2'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['EGFR'])
        assert result == 85
    
    def test_cerner_format(self):
        """Should handle Cerner-style eGFR unit format"""
        obs = {'valueQuantity': {'value': 85, 'unit': 'mL/min/{1.73_m2}'}}
        result = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['EGFR'])
        assert result == 85


class TestCalculateEGFR:
    """Tests for eGFR calculation using CKD-EPI 2021"""
    
    def test_healthy_male(self):
        """Should calculate correct eGFR for healthy male"""
        egfr, method = unit_converter.calculate_egfr(1.0, 50, 'male')
        assert method == "CKD-EPI 2021"
        # Expected ~93 mL/min/1.73m² for 50yo male with Cr 1.0
        assert 88 <= egfr <= 98
    
    def test_healthy_female(self):
        """Should calculate correct eGFR for healthy female"""
        egfr, method = unit_converter.calculate_egfr(0.8, 50, 'female')
        assert method == "CKD-EPI 2021"
        # Expected ~99 mL/min/1.73m² for 50yo female with Cr 0.8
        assert 88 <= egfr <= 104
    
    def test_elderly_patient(self):
        """Should calculate lower eGFR for elderly patient"""
        egfr_young, _ = unit_converter.calculate_egfr(1.0, 30, 'male')
        egfr_old, _ = unit_converter.calculate_egfr(1.0, 80, 'male')
        assert egfr_old < egfr_young
    
    def test_elevated_creatinine(self):
        """Should calculate lower eGFR for elevated creatinine"""
        egfr_normal, _ = unit_converter.calculate_egfr(1.0, 50, 'male')
        egfr_elevated, _ = unit_converter.calculate_egfr(2.0, 50, 'male')
        assert egfr_elevated < egfr_normal
    
    def test_returns_integer(self):
        """eGFR should be returned as integer (clinical standard)"""
        egfr, _ = unit_converter.calculate_egfr(1.0, 50, 'male')
        assert isinstance(egfr, int)


class TestEGFRValidation:
    """Tests for eGFR input validation"""
    
    def test_none_creatinine(self):
        """Should return error for None creatinine"""
        egfr, error = unit_converter.calculate_egfr(None, 50, 'male')
        assert egfr is None
        assert "Creatinine" in error
    
    def test_none_age(self):
        """Should return error for None age"""
        egfr, error = unit_converter.calculate_egfr(1.0, None, 'male')
        assert egfr is None
        assert "Age" in error
    
    def test_none_gender(self):
        """Should return error for None gender"""
        egfr, error = unit_converter.calculate_egfr(1.0, 50, None)
        assert egfr is None
        assert "Gender" in error
    
    def test_invalid_gender(self):
        """Should return error for invalid gender"""
        egfr, error = unit_converter.calculate_egfr(1.0, 50, 'other')
        assert egfr is None
        assert "Invalid gender" in error
    
    def test_negative_creatinine(self):
        """Should return error for negative creatinine"""
        egfr, error = unit_converter.calculate_egfr(-1.0, 50, 'male')
        assert egfr is None
        assert "positive" in error
    
    def test_creatinine_below_minimum(self):
        """Should return error for creatinine below minimum"""
        egfr, error = unit_converter.calculate_egfr(0.05, 50, 'male')
        assert egfr is None
        assert "below minimum" in error
    
    def test_creatinine_above_maximum(self):
        """Should return error for creatinine above maximum"""
        egfr, error = unit_converter.calculate_egfr(35.0, 50, 'male')
        assert egfr is None
        assert "exceeds maximum" in error
    
    def test_age_below_adult(self):
        """Should return error for pediatric age"""
        egfr, error = unit_converter.calculate_egfr(1.0, 15, 'male')
        assert egfr is None
        assert "adult" in error.lower()
    
    def test_age_above_maximum(self):
        """Should return error for unrealistic age"""
        egfr, error = unit_converter.calculate_egfr(1.0, 150, 'male')
        assert egfr is None
        assert "exceeds maximum" in error


class TestValidateEGFRInputs:
    """Tests for validate_egfr_inputs method"""
    
    def test_valid_inputs(self):
        """Should return True for valid inputs"""
        is_valid, error = unit_converter.validate_egfr_inputs(1.0, 50, 'male')
        assert is_valid is True
        assert error is None
    
    def test_boundary_values(self):
        """Should accept boundary values"""
        # Minimum valid creatinine
        is_valid, _ = unit_converter.validate_egfr_inputs(0.1, 50, 'female')
        assert is_valid is True
        
        # Maximum valid creatinine
        is_valid, _ = unit_converter.validate_egfr_inputs(30.0, 50, 'male')
        assert is_valid is True
        
        # Minimum adult age
        is_valid, _ = unit_converter.validate_egfr_inputs(1.0, 18, 'male')
        assert is_valid is True
        
        # Maximum age
        is_valid, _ = unit_converter.validate_egfr_inputs(1.0, 120, 'female')
        assert is_valid is True
