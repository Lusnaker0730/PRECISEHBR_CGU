"""
Risk Classifier Service
Handles risk categorization and bleeding risk percentage calculations
"""
import logging


class RiskClassifierService:
    """Service for classifying risk levels and calculating risk percentages"""
    
    # PRECISE-HBR Score Thresholds (based on validation study)
    THRESHOLD_NON_HBR = 22      # Score ≤22: Not high bleeding risk
    THRESHOLD_HBR = 26          # Score 23-26: High bleeding risk
    THRESHOLD_VERY_HBR = 30     # Score 27-30: Very high bleeding risk
    THRESHOLD_EXTREME = 35      # Score 31-35: Extremely high risk
    
    # Bleeding Risk Percentages (1-year BARC 3/5 events, from calibration curve)
    RISK_PCTS = {
        'non_hbr': {'base': 0.5, 'max': 3.5, 'slope': 3.0},      # Score 0-22
        'hbr': {'base': 3.5, 'max': 5.5, 'slope': 2.0},          # Score 23-26
        'very_hbr': {'base': 5.5, 'max': 8.0, 'slope': 2.5},     # Score 27-30
        'extreme': {'base': 8.0, 'max': 12.0, 'slope': 4.0},     # Score 31-35
        'cap': {'base': 12.0, 'max': 15.0, 'slope': 3.0}         # Score >35
    }
    
    @classmethod
    def calculate_bleeding_risk_percentage(cls, precise_hbr_score):
        """
        Calculate 1-year bleeding risk percentage based on PRECISE-HBR score.
        Based on the calibration curve from the PRECISE-HBR validation study.
        
        Returns the estimated 1-year risk of BARC 3 or 5 bleeding events.
        """
        if precise_hbr_score <= cls.THRESHOLD_NON_HBR:
            # Non-HBR: risk ranges from ~0.5% to ~3.5%
            pct = cls.RISK_PCTS['non_hbr']
            risk_percent = pct['base'] + (precise_hbr_score / cls.THRESHOLD_NON_HBR) * pct['slope']
            return min(pct['max'], risk_percent)
        elif precise_hbr_score <= cls.THRESHOLD_HBR:
            # HBR: risk ranges from ~3.5% to ~5.5%
            pct = cls.RISK_PCTS['hbr']
            range_size = cls.THRESHOLD_HBR - cls.THRESHOLD_NON_HBR
            risk_percent = pct['base'] + ((precise_hbr_score - cls.THRESHOLD_NON_HBR) / range_size) * pct['slope']
            return min(pct['max'], risk_percent)
        elif precise_hbr_score <= cls.THRESHOLD_VERY_HBR:
            # Very HBR: risk ranges from ~5.5% to ~8%
            pct = cls.RISK_PCTS['very_hbr']
            range_size = cls.THRESHOLD_VERY_HBR - cls.THRESHOLD_HBR
            risk_percent = pct['base'] + ((precise_hbr_score - cls.THRESHOLD_HBR) / range_size) * pct['slope']
            return min(pct['max'], risk_percent)
        elif precise_hbr_score <= cls.THRESHOLD_EXTREME:
            # Extremely high risk: risk ranges from ~8% to ~12%
            pct = cls.RISK_PCTS['extreme']
            range_size = cls.THRESHOLD_EXTREME - cls.THRESHOLD_VERY_HBR
            risk_percent = pct['base'] + ((precise_hbr_score - cls.THRESHOLD_VERY_HBR) / range_size) * pct['slope']
            return min(pct['max'], risk_percent)
        else:
            # For very high scores (>35), cap at ~15%
            pct = cls.RISK_PCTS['cap']
            risk_percent = pct['base'] + ((precise_hbr_score - cls.THRESHOLD_EXTREME) / 10) * pct['slope']
            return min(pct['max'], risk_percent)
    
    @classmethod
    def get_risk_category_info(cls, precise_hbr_score):
        """
        Get risk category information based on PRECISE-HBR score.
        
        Returns:
            Dictionary with category label, color, and bleeding risk percentage
        """
        bleeding_risk_percent = cls.calculate_bleeding_risk_percentage(precise_hbr_score)
        
        if precise_hbr_score <= cls.THRESHOLD_NON_HBR:
            return {
                "category": "Not high bleeding risk",
                "color": "success",
                "bleeding_risk_percent": f"{bleeding_risk_percent:.1f}%",
                "score_range": f"(score ≤{cls.THRESHOLD_NON_HBR})"
            }
        elif precise_hbr_score <= cls.THRESHOLD_HBR:
            return {
                "category": "HBR",
                "color": "warning",
                "bleeding_risk_percent": f"{bleeding_risk_percent:.1f}%",
                "score_range": f"(score {cls.THRESHOLD_NON_HBR + 1}-{cls.THRESHOLD_HBR})"
            }
        else:  # score >= 27
            return {
                "category": "Very HBR",
                "color": "danger",
                "bleeding_risk_percent": f"{bleeding_risk_percent:.1f}%",
                "score_range": f"(score ≥{cls.THRESHOLD_HBR + 1})"
            }
    
    @classmethod
    def get_precise_hbr_display_info(cls, precise_hbr_score):
        """
        Get complete display information for PRECISE-HBR score.
        
        Returns:
            Dictionary with all display information including recommendations
        """
        risk_info = cls.get_risk_category_info(precise_hbr_score)
        bleeding_risk_percent = cls.calculate_bleeding_risk_percentage(precise_hbr_score)
        
        return {
            "score": precise_hbr_score,
            "risk_category": risk_info["category"],
            "score_range": risk_info["score_range"],
            "bleeding_risk_percent": f"{bleeding_risk_percent:.2f}%",
            "color_class": risk_info["color"],
            "full_label": f"{risk_info['category']} {risk_info['score_range']}",
            "recommendation": f"1-year risk of major bleeding: {bleeding_risk_percent:.2f}% "
                            f"(Bleeding Academic Research Consortium [BARC] type 3 or 5)"
        }


# Global instance
risk_classifier = RiskClassifierService()

