"""
Unit tests for Risk Classifier Service
Tests risk classification and bleeding risk calculation
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.risk_classifier import risk_classifier


class TestRiskClassification:
    """Test risk classification based on PRECISE-HBR score"""
    
    def test_classify_low_risk(self):
        """Test classification of low risk patient"""
        result = risk_classifier.get_risk_category_info(15)
        assert result is not None
        assert 'category' in result
        assert 'color' in result
        assert 'Not high bleeding risk' in result['category']
    
    def test_classify_moderate_risk(self):
        """Test classification of moderate risk patient"""
        result = risk_classifier.get_risk_category_info(24)
        assert result is not None
        assert result['category'] == 'HBR'
    
    def test_classify_high_risk(self):
        """Test classification of high risk patient"""
        result = risk_classifier.get_risk_category_info(28)
        assert result is not None
        assert result['category'] == 'Very HBR'
    
    def test_classify_boundary_score_23(self):
        """Test classification at HBR threshold (23)"""
        result = risk_classifier.get_risk_category_info(23)
        assert result is not None
        # Score 23 is the threshold for HBR
        assert result['category'] == 'HBR'
    
    def test_classify_boundary_score_27(self):
        """Test classification at very high HBR threshold (27)"""
        result = risk_classifier.get_risk_category_info(27)
        assert result is not None
        # Score 27 is the threshold for very high HBR
        assert result['category'] == 'Very HBR'
    
    def test_classify_zero_score(self):
        """Test classification with zero score"""
        result = risk_classifier.get_risk_category_info(0)
        assert result is not None
        assert 'Not high bleeding risk' in result['category']
    
    def test_classify_very_high_score(self):
        """Test classification with very high score"""
        result = risk_classifier.get_risk_category_info(50)
        assert result is not None
        assert result['category'] == 'Very HBR'


class TestBleedingRiskPercentage:
    """Test bleeding risk percentage calculation"""
    
    def test_bleeding_risk_low_score(self):
        """Test bleeding risk percentage for low score"""
        result = risk_classifier.calculate_bleeding_risk_percentage(15)
        assert result is not None
        assert isinstance(result, (int, float, str))
        # Low score should have low bleeding risk
        if isinstance(result, (int, float)):
            assert result < 5.0
    
    def test_bleeding_risk_moderate_score(self):
        """Test bleeding risk percentage for moderate score"""
        result = risk_classifier.calculate_bleeding_risk_percentage(24)
        assert result is not None
        # Moderate score should have moderate bleeding risk
        if isinstance(result, (int, float)):
            assert 4.0 <= result <= 7.0
    
    def test_bleeding_risk_high_score(self):
        """Test bleeding risk percentage for high score"""
        result = risk_classifier.calculate_bleeding_risk_percentage(30)
        assert result is not None
        # High score should have high bleeding risk
        if isinstance(result, (int, float)):
            assert result > 6.0
    
    def test_bleeding_risk_zero_score(self):
        """Test bleeding risk percentage for zero score"""
        result = risk_classifier.calculate_bleeding_risk_percentage(0)
        assert result is not None
        # Zero score should have minimal bleeding risk
        if isinstance(result, (int, float)):
            assert result < 3.0
    
    def test_bleeding_risk_returns_valid_format(self):
        """Test that bleeding risk is returned in valid format"""
        result = risk_classifier.calculate_bleeding_risk_percentage(25)
        assert result is not None
        # Should be either a number or a formatted string
        if isinstance(result, str):
            assert '%' in result or '.' in result


class TestColorCoding:
    """Test color coding for risk levels"""
    
    def test_color_for_low_risk(self):
        """Test color coding for low risk"""
        result = risk_classifier.get_risk_category_info(15)
        assert 'color' in result
        # Low risk is success (green)
        assert result['color'] == 'success'
    
    def test_color_for_moderate_risk(self):
        """Test color coding for moderate risk"""
        result = risk_classifier.get_risk_category_info(24)
        assert 'color' in result
        # HBR is warning (yellow)
        assert result['color'] == 'warning'
    
    def test_color_for_high_risk(self):
        """Test color coding for high risk"""
        result = risk_classifier.get_risk_category_info(28)
        assert 'color' in result
        # Very HBR is danger (red)
        assert result['color'] == 'danger'


class TestRiskCategoryInfo:
    """Test detailed risk category information"""
    
    def test_category_info_includes_percentage(self):
        """Test that category info includes bleeding risk percentage"""
        result = risk_classifier.get_risk_category_info(25)
        # Should include bleeding risk percentage
        assert 'bleeding_risk_percent' in result
    
    def test_category_info_includes_score_range(self):
        """Test that category info includes score range"""
        result = risk_classifier.get_risk_category_info(25)
        # Should include score range information
        assert 'score_range' in result
    
    def test_category_info_consistency(self):
        """Test consistency of category info"""
        result1 = risk_classifier.get_risk_category_info(25)
        result2 = risk_classifier.get_risk_category_info(25)
        # Same score should give same result
        assert result1['category'] == result2['category']
        assert result1['color'] == result2['color']


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_negative_score(self):
        """Test handling of negative score"""
        result = risk_classifier.get_risk_category_info(-5)
        # Should handle gracefully
        assert result is not None
    
    def test_very_large_score(self):
        """Test handling of very large score"""
        result = risk_classifier.get_risk_category_info(1000)
        assert result is not None
        # Should classify as very high risk
        assert result['category'] == 'Very HBR'
    
    def test_float_score(self):
        """Test handling of float score"""
        result = risk_classifier.get_risk_category_info(24.5)
        assert result is not None
        assert 'category' in result
    
    def test_string_score(self):
        """Test handling of string score"""
        try:
            result = risk_classifier.get_risk_category_info("25")
            # If it handles string conversion
            assert result is not None
        except (TypeError, ValueError):
            # Or if it raises an exception, that's also acceptable
            assert True


class TestRiskThresholds:
    """Test risk threshold boundaries"""
    
    def test_threshold_22_not_hbr(self):
        """Test score 22 (just below HBR threshold)"""
        result = risk_classifier.get_risk_category_info(22)
        assert result is not None
        # Should be Not HBR
        assert 'Not high bleeding risk' in result['category']
    
    def test_threshold_23_hbr(self):
        """Test score 23 (HBR threshold)"""
        result = risk_classifier.get_risk_category_info(23)
        assert result is not None
        # Should be HBR
        assert result['category'] == 'HBR'
    
    def test_threshold_26_hbr(self):
        """Test score 26 (just below very high HBR)"""
        result = risk_classifier.get_risk_category_info(26)
        assert result is not None
        # Should be HBR but not very high
        assert result['category'] == 'HBR'
    
    def test_threshold_27_very_high_hbr(self):
        """Test score 27 (very high HBR threshold)"""
        result = risk_classifier.get_risk_category_info(27)
        assert result is not None
        # Should be Very High HBR
        assert result['category'] == 'Very HBR'


class TestBleedingRiskFormula:
    """Test bleeding risk calculation formula"""
    
    def test_bleeding_risk_increases_with_score(self):
        """Test that bleeding risk increases with score"""
        risk_15 = risk_classifier.calculate_bleeding_risk_percentage(15)
        risk_25 = risk_classifier.calculate_bleeding_risk_percentage(25)
        risk_35 = risk_classifier.calculate_bleeding_risk_percentage(35)
        
        # Convert to float if string
        if isinstance(risk_15, str):
            risk_15 = float(risk_15.replace('%', ''))
        if isinstance(risk_25, str):
            risk_25 = float(risk_25.replace('%', ''))
        if isinstance(risk_35, str):
            risk_35 = float(risk_35.replace('%', ''))
        
        # Risk should increase with score
        assert risk_15 < risk_25 < risk_35
    
    def test_bleeding_risk_reasonable_range(self):
        """Test that bleeding risk is in reasonable range"""
        for score in [10, 20, 30, 40]:
            risk = risk_classifier.calculate_bleeding_risk_percentage(score)
            if isinstance(risk, str):
                risk = float(risk.replace('%', ''))
            # Bleeding risk should be between 0% and 100%
            assert 0 <= risk <= 100


class TestSingletonPattern:
    """Test singleton pattern implementation"""
    
    def test_singleton_instance(self):
        """Test that risk_classifier is a singleton"""
        from services.risk_classifier import risk_classifier as instance1
        from services.risk_classifier import risk_classifier as instance2
        assert instance1 is instance2


class TestReturnValueStructure:
    """Test structure of return values"""
    
    def test_classify_risk_returns_dict(self):
        """Test that get_risk_category_info returns a dictionary"""
        result = risk_classifier.get_risk_category_info(25)
        assert isinstance(result, dict)
    
    def test_classify_risk_has_required_keys(self):
        """Test that result has required keys"""
        result = risk_classifier.get_risk_category_info(25)
        required_keys = ['category', 'color', 'bleeding_risk_percent', 'score_range']
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"
    
    def test_bleeding_risk_percentage_type(self):
        """Test bleeding risk percentage return type"""
        result = risk_classifier.calculate_bleeding_risk_percentage(25)
        # Should be a number (float)
        assert isinstance(result, (int, float))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

