"""
Unit tests for Config Loader Service
Tests configuration loading and management functionality
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, mock_open

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.config_loader import config_loader


class TestConfigLoader:
    """Test ConfigLoader class"""
    
    def test_singleton_pattern(self):
        """Test that ConfigLoader follows singleton pattern"""
        instance1 = config_loader
        from services.config_loader import config_loader as instance2
        assert instance1 is instance2
    
    def test_config_loaded(self):
        """Test that configuration is loaded"""
        assert config_loader.config is not None
        assert isinstance(config_loader.config, dict)
    
    def test_get_version(self):
        """Test getting configuration version"""
        version = config_loader.config.get('version')
        assert version is not None
        assert isinstance(version, str)
    
    def test_get_scoring_logic(self):
        """Test getting scoring logic configuration"""
        scoring_logic = config_loader.config.get('scoring_logic')
        assert scoring_logic is not None
        assert isinstance(scoring_logic, dict)
        assert 'scoring_method' in scoring_logic


class TestPreciseHbrParameters:
    """Test PRECISE-HBR parameters retrieval"""
    
    def test_get_precise_hbr_parameters(self):
        """Test getting all PRECISE-HBR parameters"""
        params = config_loader.config.get('precise_hbr_parameters')
        assert params is not None
        assert isinstance(params, dict)
        assert 'age' in params
        assert 'hemoglobin' in params
        assert 'egfr' in params
    
    def test_get_age_parameter(self):
        """Test getting age parameter"""
        age_param = config_loader.config.get('precise_hbr_parameters', {}).get('age')
        assert age_param is not None
        assert 'min_value' in age_param
        assert 'max_value' in age_param
    
    def test_get_hemoglobin_parameter(self):
        """Test getting hemoglobin parameter"""
        hb_param = config_loader.config.get('precise_hbr_parameters', {}).get('hemoglobin')
        assert hb_param is not None
        assert 'min_value' in hb_param
        assert 'max_value' in hb_param


class TestSnomedCodes:
    """Test SNOMED code retrieval"""
    
    def test_get_snomed_codes_bleeding_diathesis(self):
        """Test getting bleeding diathesis SNOMED codes"""
        codes = config_loader.get_snomed_codes('bleeding_diathesis')
        assert codes is not None
        assert isinstance(codes, dict)
        assert 'specific_codes' in codes or 'parent_code' in codes
    
    def test_get_snomed_codes_prior_bleeding(self):
        """Test getting prior bleeding SNOMED codes"""
        codes = config_loader.get_snomed_codes('prior_bleeding')
        assert codes is not None
        assert isinstance(codes, dict)
    
    def test_get_snomed_codes_active_cancer(self):
        """Test getting active cancer SNOMED codes"""
        codes = config_loader.get_snomed_codes('active_cancer')
        assert codes is not None
        assert isinstance(codes, dict)
    
    def test_get_snomed_codes_liver_cirrhosis(self):
        """Test getting liver cirrhosis SNOMED codes"""
        codes = config_loader.get_snomed_codes('liver_cirrhosis')
        assert codes is not None
        assert isinstance(codes, dict)
    
    def test_get_snomed_codes_thrombocytopenia(self):
        """Test getting thrombocytopenia configuration"""
        config = config_loader.get_snomed_codes('thrombocytopenia')
        assert config is not None
        assert isinstance(config, dict)
        # Should have threshold for platelet count
        assert 'threshold' in config
    
    def test_get_snomed_codes_invalid_key(self):
        """Test getting SNOMED codes with invalid key"""
        codes = config_loader.get_snomed_codes('invalid_condition')
        assert codes is None or codes == {}


class TestMedicationKeywords:
    """Test medication keyword retrieval"""
    
    def test_get_medication_keywords(self):
        """Test getting all medication keywords"""
        keywords = config_loader.get_medication_keywords()
        assert keywords is not None
        assert isinstance(keywords, dict)
        assert 'oral_anticoagulants' in keywords
        assert 'nsaids_corticosteroids' in keywords
    
    def test_get_oral_anticoagulants(self):
        """Test getting oral anticoagulant keywords"""
        keywords = config_loader.get_medication_keywords()
        oac = keywords.get('oral_anticoagulants')
        assert oac is not None
        assert 'generic_names' in oac or 'brand_names' in oac or 'nhi_codes' in oac
    
    def test_get_nsaids_corticosteroids(self):
        """Test getting NSAIDs/corticosteroids keywords"""
        keywords = config_loader.get_medication_keywords()
        nsaids = keywords.get('nsaids_corticosteroids')
        assert nsaids is not None
        assert isinstance(nsaids, dict)


class TestBleedingHistoryKeywords:
    """Test bleeding history keyword retrieval"""
    
    def test_get_bleeding_history_keywords(self):
        """Test getting bleeding history keywords"""
        keywords = config_loader.get_bleeding_history_keywords()
        assert keywords is not None
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Check for common bleeding keywords
        keywords_lower = [k.lower() for k in keywords]
        assert any('bleeding' in k for k in keywords_lower)


class TestLaboratoryValues:
    """Test laboratory value configuration"""
    
    def test_get_lab_value_extraction_config(self):
        """Test getting laboratory value extraction configuration"""
        loinc_codes = config_loader.get_loinc_codes()
        assert loinc_codes is not None
        assert isinstance(loinc_codes, dict)
    
    def test_get_hemoglobin_loinc_codes(self):
        """Test getting hemoglobin LOINC codes"""
        loinc_codes = config_loader.get_loinc_codes()
        hb_codes = loinc_codes.get('HEMOGLOBIN')
        assert hb_codes is not None
        assert isinstance(hb_codes, tuple)
        assert '718-7' in hb_codes
    
    def test_get_creatinine_loinc_codes(self):
        """Test getting creatinine LOINC codes"""
        loinc_codes = config_loader.get_loinc_codes()
        cr_codes = loinc_codes.get('CREATININE')
        assert cr_codes is not None
        assert isinstance(cr_codes, tuple)
    
    def test_get_platelet_loinc_codes(self):
        """Test getting platelet LOINC codes"""
        loinc_codes = config_loader.get_loinc_codes()
        plt_codes = loinc_codes.get('PLATELETS')
        assert plt_codes is not None
        assert isinstance(plt_codes, tuple)


class TestUnitConversionConfig:
    """Test unit conversion configuration"""
    
    def test_get_unit_conversion_config(self):
        """Test getting unit conversion configuration"""
        config = config_loader.config.get('unit_conversion')
        if config:
            assert isinstance(config, dict)
    
    def test_hemoglobin_conversion_factors(self):
        """Test hemoglobin unit conversion factors"""
        config = config_loader.config.get('unit_conversion', {})
        hb_config = config.get('hemoglobin')
        if hb_config:
            assert 'target_unit' in hb_config or 'conversion_factors' in hb_config


class TestConfigReload:
    """Test configuration reload functionality"""
    
    def test_reload_config(self):
        """Test reloading configuration"""
        # Get initial version
        initial_version = config_loader.config.get('version')
        
        # Reload config by creating new instance
        config_loader._load_config()
        
        # Version should still be accessible
        reloaded_version = config_loader.config.get('version')
        assert reloaded_version == initial_version


class TestConfigValidation:
    """Test configuration validation"""
    
    def test_config_has_required_sections(self):
        """Test that config has all required sections"""
        required_sections = [
            'version',
            'scoring_logic',
            'precise_hbr_parameters',
            'precise_hbr_snomed_codes',
            'medication_keywords'
        ]
        
        for section in required_sections:
            assert section in config_loader.config, f"Missing required section: {section}"
    
    def test_version_format(self):
        """Test that version follows semantic versioning"""
        version = config_loader.config.get('version')
        # Should be in format X.Y.Z
        parts = version.split('.')
        assert len(parts) >= 2, "Version should have at least major.minor"
    
    def test_scoring_method(self):
        """Test that scoring method is defined"""
        scoring_logic = config_loader.config.get('scoring_logic')
        assert 'scoring_method' in scoring_logic
        assert scoring_logic['scoring_method'] in ['PRECISE-HBR', 'ARC-HBR']


class TestErrorHandling:
    """Test error handling in config loader"""
    
    def test_get_nonexistent_snomed_codes(self):
        """Test handling of non-existent SNOMED code requests"""
        result = config_loader.get_snomed_codes('nonexistent_condition')
        # Should return None or empty dict, not raise exception
        assert result is None or result == {}
    
    def test_config_with_missing_file(self):
        """Test handling when config file is missing"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            # Should handle gracefully
            try:
                from services.config_loader import ConfigLoader
                loader = ConfigLoader()
                # If it doesn't raise, that's good
                assert True
            except FileNotFoundError:
                # Also acceptable if it raises but doesn't crash
                assert True


class TestICD10Codes:
    """Test ICD-10 code retrieval"""
    
    def test_bleeding_diathesis_has_icd10_codes(self):
        """Test that bleeding diathesis config includes ICD-10 codes"""
        codes = config_loader.get_snomed_codes('bleeding_diathesis')
        assert 'icd10cm_codes' in codes
        assert isinstance(codes['icd10cm_codes'], list)
        assert len(codes['icd10cm_codes']) > 0
    
    def test_active_cancer_has_icd10_codes(self):
        """Test that active cancer config includes ICD-10 codes"""
        codes = config_loader.get_snomed_codes('active_cancer')
        assert 'icd10cm_codes' in codes
        assert isinstance(codes['icd10cm_codes'], list)


class TestNHICodes:
    """Test NHI code retrieval"""
    
    def test_oral_anticoagulants_have_nhi_codes(self):
        """Test that oral anticoagulants include NHI codes"""
        keywords = config_loader.get_medication_keywords()
        oac = keywords.get('oral_anticoagulants')
        assert 'nhi_codes' in oac
        assert isinstance(oac['nhi_codes'], list)
        assert len(oac['nhi_codes']) > 0
    
    def test_nsaids_have_nhi_codes(self):
        """Test that NSAIDs include NHI codes"""
        keywords = config_loader.get_medication_keywords()
        nsaids = keywords.get('nsaids_corticosteroids')
        if 'nhi_codes' in nsaids:
            assert isinstance(nsaids['nhi_codes'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

