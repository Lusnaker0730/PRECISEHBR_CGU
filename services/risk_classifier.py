"""
Risk Classifier Service
Handles risk categorization and bleeding risk percentage calculations
"""
import logging


class RiskClassifierService:
    """Service for classifying risk levels and calculating risk percentages"""
    
    @staticmethod
    def calculate_bleeding_risk_percentage(precise_hbr_score):
        """
        Calculate 1-year bleeding risk percentage based on PRECISE-HBR score.
        Based on the calibration curve from the PRECISE-HBR validation study.
        
        Returns the estimated 1-year risk of BARC 3 or 5 bleeding events.
        """
        if precise_hbr_score <= 22:
            # Non-HBR: risk ranges from ~0.5% to ~3.5%
            risk_percent = 0.5 + (precise_hbr_score / 22) * 3.0
            return min(3.5, risk_percent)
        elif precise_hbr_score <= 26:
            # HBR: risk ranges from ~3.5% to ~5.5%
            risk_percent = 3.5 + ((precise_hbr_score - 22) / 4) * 2.0
            return min(5.5, risk_percent)
        elif precise_hbr_score <= 30:
            # Very HBR: risk ranges from ~5.5% to ~8%
            risk_percent = 5.5 + ((precise_hbr_score - 26) / 4) * 2.5
            return min(8.0, risk_percent)
        elif precise_hbr_score <= 35:
            # Extremely high risk: risk ranges from ~8% to ~12%
            risk_percent = 8.0 + ((precise_hbr_score - 30) / 5) * 4.0
            return min(12.0, risk_percent)
        else:
            # For very high scores (>35), cap at ~15%
            risk_percent = 12.0 + ((precise_hbr_score - 35) / 10) * 3.0
            return min(15.0, risk_percent)
    
    @classmethod
    def get_risk_category_info(cls, precise_hbr_score):
        """
        Get risk category information based on PRECISE-HBR score.
        
        Returns:
            Dictionary with category label, color, and bleeding risk percentage
        """
        bleeding_risk_percent = cls.calculate_bleeding_risk_percentage(precise_hbr_score)
        
        if precise_hbr_score <= 22:
            return {
                "category": "Not high bleeding risk",
                "color": "success",
                "bleeding_risk_percent": f"{bleeding_risk_percent:.1f}%",
                "score_range": f"(score ≤22)"
            }
        elif precise_hbr_score <= 26:
            return {
                "category": "HBR",
                "color": "warning",
                "bleeding_risk_percent": f"{bleeding_risk_percent:.1f}%",
                "score_range": f"(score 23-26)"
            }
        else:  # score >= 27
            return {
                "category": "Very HBR",
                "color": "danger",
                "bleeding_risk_percent": f"{bleeding_risk_percent:.1f}%",
                "score_range": f"(score ≥27)"
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

