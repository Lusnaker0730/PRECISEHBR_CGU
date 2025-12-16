import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.tradeoff_model_calculator import TradeoffModelCalculator
from services.config_loader import config_loader

class TestTradeoffModelSafety(unittest.TestCase):
    
    def setUp(self):
        # Mock config loader to return consistent thresholds
        self.mock_config = {
            'risk_factor_thresholds': {
                'age_threshold': 65,
                'hemoglobin_ranges': {'moderate': {'min': 11, 'max': 13}, 'severe': {'max': 11}},
                'egfr_ranges': {'moderate': {'min': 30, 'max': 60}, 'severe': {'max': 30}}
            },
            'baseline_event_rates': {
                'bleeding_rate_percent': 2.5,
                'thrombotic_rate_percent': 2.5
            }
        }
        
    def test_missing_data_behavior(self):
        """Test how the model handles missing data (None/Empty)"""
        
        # Case 1: All Data Missing (Empty inputs)
        raw_data = {} 
        demographics = {} # No age
        tradeoff_data = {} # No clinical flags
        
        # Patch config first
        with patch('services.config_loader.config_loader.get_tradeoff_config', return_value=self.mock_config):
            active_factors, missing_data = TradeoffModelCalculator.detect_tradeoff_factors(raw_data, demographics, tradeoff_data)
            
        print(f"\nMissing Data Active Factors: {active_factors}, Missing: {missing_data}")
        
        # Assertions
        self.assertEqual(len(active_factors), 0, "Should detect no factors if data is missing")
        self.assertIn('Age', missing_data)
        self.assertIn('Hemoglobin', missing_data)
        self.assertIn('eGFR', missing_data)
        
        # This confirms the "Silent Failure" / "Underestimation" risk.
        # If age was missing, 'age_ge_65' is False.
        # If Hb was missing, 'hemoglobin_lt_11' is False.
        
    def test_high_risk_patient(self):
        """Test a high risk patient to confirm detection works when data IS present"""
        raw_data = {
            'HEMOGLOBIN': [{'valueQuantity': {'value': 10.0, 'unit': 'g/dL'}}], # Severe anemia
            'EGFR': [{'valueQuantity': {'value': 25.0, 'unit': 'mL/min/1.73m2'}}] # Severe renal failure
        }
        demographics = {'age': 75} # Elderly
        tradeoff_data = {'diabetes': True}
        
        with patch('services.config_loader.config_loader.get_tradeoff_config', return_value=self.mock_config):
            active_factors, _ = TradeoffModelCalculator.detect_tradeoff_factors(raw_data, demographics, tradeoff_data)
            
        print(f"High Risk Active Factors: {active_factors}")
        
        self.assertTrue(active_factors.get('age_ge_65'))
        self.assertTrue(active_factors.get('hemoglobin_lt_11'))
        self.assertTrue(active_factors.get('egfr_lt_30'))
        self.assertTrue(active_factors.get('diabetes'))

if __name__ == '__main__':
    unittest.main()
