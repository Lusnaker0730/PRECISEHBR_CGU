"""
Unit Conversion Service
Handles all laboratory value unit conversions to canonical units
"""
import logging


class UnitConversionService:
    """Service for converting laboratory values to canonical units"""
    
    # Define the canonical units the application will use internally for calculations
    TARGET_UNITS = {
        'HEMOGLOBIN': {
            'unit': 'g/dl',
            # Factors to convert a source unit TO the target unit (g/dL)
            'factors': {
                'g/l': 0.1,
                'mmol/l': 1.61135,  # Based on Hb molar mass of 64,458 g/mol
                'mg/dl': 0.001,  # Conversion for mg/dL to g/dL
            }
        },
        'CREATININE': {
            'unit': 'mg/dl',
            # Factors to convert a source unit TO the target unit (mg/dL)
            'factors': {
                'umol/l': 0.0113,  # µmol/L to mg/dL
                'µmol/l': 0.0113,  # Handle unicode character
            }
        },
        'WBC': {
            'unit': '10*9/l',
            # Factors to convert a source unit TO the target unit (10^9/L)
            'factors': {
                '10*3/ul': 1.0,     # 10^3/µL = K/µL = 10^9/L (same unit, different notation)
                'k/ul': 1.0,        # K/µL = thousands/µL = 10^9/L
                '/ul': 0.001,       # cells/µL ÷ 1000 = 10^9/L
                '/mm3': 0.001,      # cells/mm³ = cells/µL, same conversion
                '10^9/l': 1.0,      # Already in target unit
                'giga/l': 1.0       # Giga/L = 10^9/L
            }
        },
        'EGFR': {
            'unit': 'ml/min/1.73m2',
            'factors': {
                'ml/min/1.73m2': 1.0,       # Standard format
                'ml/min/{1.73_m2}': 1.0,    # Cerner format with braces
                'ml/min/1.73m^2': 1.0,      # With caret
                'ml/min/1.73 m2': 1.0,      # With space
                'ml/min/1.73 m^2': 1.0,     # Space and caret
                'ml/min per 1.73m2': 1.0,   # With 'per'
                'ml/min/bsa': 1.0,          # Body surface area
                'ml/min': 1.0               # Without BSA normalization
            } 
        },
        'PLATELETS': {
            'unit': '10*9/l',
            'factors': {
                '10*3/ul': 1.0,     # 10^3/µL = K/µL = 10^9/L (same unit)
                'k/ul': 1.0,        # K/µL = thousands/µL = 10^9/L
                '/ul': 0.001,       # cells/µL ÷ 1000 = 10^9/L
                '10^9/l': 1.0,      # Already in target unit
                'giga/l': 1.0       # Giga/L = 10^9/L
            }
        }
    }
    
    @classmethod
    def get_value_from_observation(cls, obs, unit_system):
        """
        Safely extracts a numeric value from an Observation resource, handling unit conversions.
        Returns the numeric value in the target unit, or None if conversion is not possible.
        """
        if not obs or not isinstance(obs, dict):
            return None

        value_quantity = obs.get('valueQuantity')
        if not value_quantity:
            return None

        value = value_quantity.get('value')
        if value is None or not isinstance(value, (int, float)):
            return None
            
        source_unit = value_quantity.get('unit', '').lower()
        target_unit = unit_system['unit']
        
        # 1. Direct match
        if source_unit == target_unit:
            return value

        # 2. Check for common alternative writings of the target unit
        if source_unit.lower() == target_unit.lower():
            return value

        # 3. Attempt conversion
        conversion_factors = unit_system.get('factors', {})
        if source_unit in conversion_factors:
            conversion_factor = conversion_factors[source_unit]
            converted_value = value * conversion_factor
            logging.info(f"Converted {value} {source_unit} to {converted_value:.2f} {target_unit}")
            return converted_value

        # 4. If no conversion is possible, log a warning and return None
        logging.warning(f"Unit mismatch and no conversion rule found for Observation. "
                        f"Received: '{source_unit}', Expected: '{target_unit}'. Cannot proceed with this value.")
        return None
    
    @classmethod
    def calculate_egfr(cls, cr_val, age, gender):
        """
        Calculates eGFR using the CKD-EPI 2021 equation.
        
        Args:
            cr_val: Creatinine value in mg/dL
            age: Patient age in years
            gender: 'male' or 'female'
        
        Returns:
            Tuple of (egfr_value, calculation_method)
        """
        if not all([cr_val, age, gender]) or gender not in ['male', 'female']:
            return None, "Missing data for eGFR calculation"
        
        k = 0.7 if gender == 'female' else 0.9
        alpha = -0.241 if gender == 'female' else -0.302
        
        # CKD-EPI 2021 formula
        egfr = 142 * (min(cr_val / k, 1) ** alpha) * (max(cr_val / k, 1) ** -1.2) * (0.9938 ** age)
        if gender == 'female':
            egfr *= 1.012
            
        return round(egfr), "CKD-EPI 2021"


# Global instance for easy access
unit_converter = UnitConversionService()

