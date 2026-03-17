"""
Risk Classifier Service
Handles risk categorization and bleeding risk percentage calculations
"""
import logging
import math

logger = logging.getLogger(__name__)


class RiskClassifierService:
    """Service for classifying risk levels and calculating risk percentages"""

    # PRECISE-HBR Score Thresholds (based on validation study)
    THRESHOLD_NON_HBR = 22      # Score ≤22: Not high bleeding risk
    THRESHOLD_HBR = 26          # Score 23-26: High bleeding risk

    # Complementary log-log (cloglog) calibration curve coefficients
    # Derived from the Fine-Gray competing risks model in the PRECISE-HBR
    # validation study.  Formula: risk = 1 - exp(-exp(a + b * score))
    # Coefficients fitted against the official calculator (precise-hbr.eoc.ch)
    # and verified across score range 2-54 with <0.05% absolute error.
    _CLOGLOG_A = -5.3945
    _CLOGLOG_B = 0.09725

    # Valid score range for the cloglog calibration curve (validation study).
    # Scores outside this range are clamped to prevent math overflow.
    _SCORE_MIN = 2
    _SCORE_MAX = 54

    @classmethod
    def calculate_bleeding_risk_percentage(cls, precise_hbr_score):
        """
        Calculate 1-year bleeding risk percentage based on PRECISE-HBR score.

        Uses the complementary log-log link function from the Fine-Gray
        competing risks model (PRECISE-HBR validation study calibration curve).

        Returns the estimated 1-year risk of BARC 3 or 5 bleeding events.
        """
        if not isinstance(precise_hbr_score, (int, float)) or math.isnan(precise_hbr_score):
            logger.warning(f"Invalid score type for bleeding risk: {precise_hbr_score}")
            return 0.0

        # Clamp to validated range to prevent math.exp overflow/domain errors
        clamped = max(cls._SCORE_MIN, min(cls._SCORE_MAX, precise_hbr_score))
        if clamped != precise_hbr_score:
            logger.warning(
                f"PRECISE-HBR score {precise_hbr_score} outside validated range "
                f"[{cls._SCORE_MIN}, {cls._SCORE_MAX}], clamped to {clamped}"
            )

        linear_predictor = cls._CLOGLOG_A + cls._CLOGLOG_B * clamped
        risk = 1.0 - math.exp(-math.exp(linear_predictor))
        return round(risk * 100, 2)
    
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


    @classmethod
    def get_score_from_table(cls, value, score_table, range_key):
        """
        Get score from lookup tables based on value ranges.

        Args:
            value: The numeric value to look up
            score_table: List of dicts with range_key and base_score
            range_key: Key name for the range field (e.g. 'age_range')

        Returns:
            Score from table, or 0 if not found
        """
        # Check for exact range match
        for item in score_table:
            if range_key not in item:
                continue
            range_values = item[range_key]
            if len(range_values) == 2 and range_values[0] <= value <= range_values[1]:
                return item.get('base_score', 0)

        # Handle out-of-range values based on range type
        boundary_configs = {
            'age_range': {'check': 'above_max', 'label': 'Age'},
            'wbc_range': {'check': 'above_max', 'label': 'WBC'},
            'hb_range': {'check': 'below_min', 'label': 'Hemoglobin'},
            'ccr_range': {'check': 'below_min', 'label': 'Creatinine clearance'},
        }

        config = boundary_configs.get(range_key)
        if not config:
            return 0

        if config['check'] == 'above_max':
            boundary_item = max(
                score_table,
                key=lambda x: x[range_key][1] if range_key in x else 0
            )
            boundary_value = boundary_item[range_key][1]
            is_out_of_range = value > boundary_value
        else:
            boundary_item = min(
                score_table,
                key=lambda x: x[range_key][0] if range_key in x else float('inf')
            )
            boundary_value = boundary_item[range_key][0]
            is_out_of_range = value < boundary_value

        if is_out_of_range:
            score = boundary_item.get('base_score', 0)
            logger.info(
                f"{config['label']} {value} outside range {boundary_item[range_key]}, "
                f"using score: {score}"
            )
            return score

        return 0


# Global instance
risk_classifier = RiskClassifierService()

