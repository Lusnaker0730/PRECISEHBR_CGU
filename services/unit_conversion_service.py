"""
Unit Conversion Service
Handles all laboratory value unit conversions to canonical units
"""
import logging


class UnitConversionService:
    """Service for converting laboratory values to canonical units"""
    
    # Clinical validation ranges for input values
    VALIDATION_RANGES = {
        'creatinine': {'min': 0.1, 'max': 30.0},  # mg/dL
        'age': {'min': 18, 'max': 120},            # years (adult only)
    }
    
    # Define the canonical units the application will use internally for calculations
    TARGET_UNITS = {
        'HEMOGLOBIN': {
            'unit': 'g/dl',
            # Factors to convert a source unit TO the target unit (g/dL)
            # Reference: https://unitslab.com/node/53
            'factors': {
                'g/l': 0.1,
                # 1 mmol/L Hb = 16.1135 g/L = 1.61135 g/dL
                # Based on Hb tetramer molar mass of ~64,458 g/mol
                'mmol/l': 1.61135,
                'mg/dl': 0.001,
            }
        },
        'CREATININE': {
            'unit': 'mg/dl',
            # Factors to convert a source unit TO the target unit (mg/dL)
            'factors': {
                'umol/l': 0.0113,   # µmol/L to mg/dL
                'µmol/l': 0.0113,   # Handle unicode character
                'μmol/l': 0.0113,   # Handle Greek mu character
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
                'giga/l': 1.0,      # Giga/L = 10^9/L
                # Additional UCUM variants
                '10e9/l': 1.0,      # Scientific notation format
                'x10^9/l': 1.0,     # x-prefix format
                '10*9/ul': 1000.0,  # 10^9/µL (rare but possible)
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
                'ml/min/bsa': 1.0,          # Body surface area (assumes 1.73m²)
                'ml/min': 1.0,              # Without BSA normalization (CAUTION: may differ ±20%)
                # Additional UCUM variants
                'ml/min/1.73m**2': 1.0,     # Python-style exponent
                'ml/min/1.73m²': 1.0,       # Unicode superscript
            } 
        },
        'PLATELETS': {
            'unit': '10*9/l',
            'factors': {
                '10*3/ul': 1.0,     # 10^3/µL = K/µL = 10^9/L (same unit)
                'k/ul': 1.0,        # K/µL = thousands/µL = 10^9/L
                '/ul': 0.001,       # cells/µL ÷ 1000 = 10^9/L
                '10^9/l': 1.0,      # Already in target unit
                'giga/l': 1.0,      # Giga/L = 10^9/L
                # Additional UCUM variants
                '10e9/l': 1.0,      # Scientific notation format
                'x10^9/l': 1.0,     # x-prefix format
                'x10*9/l': 1.0,     # x-prefix with asterisk
            }
        }
    }
    
    # Status constants for get_value_with_status
    STATUS_OK = 'ok'
    STATUS_NO_DATA = 'no_data'
    STATUS_NO_VALUE = 'no_value'
    STATUS_MISSING_UNIT = 'missing_unit'
    STATUS_UNKNOWN_UNIT = 'unknown_unit'

    @classmethod
    def get_value_from_observation(cls, obs, unit_system):
        """
        Safely extracts a numeric value from an Observation resource, handling unit conversions.
        Returns the numeric value in the target unit, or None if conversion is not possible.
        """
        result = cls.get_value_with_status(obs, unit_system)
        return result['value']

    @classmethod
    def get_value_with_status(cls, obs, unit_system):
        """
        Extracts a numeric value with detailed status about the conversion outcome.

        Returns:
            dict with keys:
                - value: converted numeric value, or None
                - status: STATUS_OK | STATUS_NO_DATA | STATUS_NO_VALUE |
                          STATUS_MISSING_UNIT | STATUS_UNKNOWN_UNIT
                - source_unit: the raw unit string from the observation (or None)
                - target_unit: the expected canonical unit
                - raw_value: the original numeric value before conversion (or None)
        """
        # Handle both dict unit_system (e.g., {'unit': 'g/dL'}) and string fallback
        if isinstance(unit_system, dict):
            target_unit = unit_system.get('unit', '').lower()
        else:
            target_unit = str(unit_system).lower() if unit_system else ''
        no_data = {'value': None, 'status': cls.STATUS_NO_DATA,
                   'source_unit': None, 'target_unit': target_unit, 'raw_value': None}

        if not obs or not isinstance(obs, dict):
            return no_data

        value_quantity = obs.get('valueQuantity')
        if not value_quantity:
            return no_data

        value = value_quantity.get('value')
        if value is None or not isinstance(value, (int, float)):
            return {'value': None, 'status': cls.STATUS_NO_VALUE,
                    'source_unit': value_quantity.get('unit'),
                    'target_unit': target_unit, 'raw_value': None}

        # Normalize both units to lowercase for consistent comparison
        raw_unit = value_quantity.get('unit')
        source_unit = (raw_unit or '').lower().strip()

        # Missing unit — value present but no unit specified
        if not source_unit:
            logging.warning(
                f"Observation has numeric value {value} but no unit specified. "
                f"Expected: '{target_unit}'. Refusing to guess — treating as unusable."
            )
            return {'value': None, 'status': cls.STATUS_MISSING_UNIT,
                    'source_unit': raw_unit, 'target_unit': target_unit,
                    'raw_value': value}

        # 1. Direct match (case-insensitive)
        if source_unit == target_unit:
            return {'value': value, 'status': cls.STATUS_OK,
                    'source_unit': raw_unit, 'target_unit': target_unit,
                    'raw_value': value}

        # 2. Attempt conversion using factors
        conversion_factors = unit_system.get('factors', {})
        if source_unit in conversion_factors:
            conversion_factor = conversion_factors[source_unit]
            converted_value = value * conversion_factor

            # Warn for eGFR units that assume BSA normalization
            _IMPRECISE_EGFR_UNITS = {'ml/min', 'ml/min/bsa'}
            if source_unit in _IMPRECISE_EGFR_UNITS and target_unit == 'ml/min/1.73m2':
                logging.warning(
                    f"eGFR unit '{raw_unit}' is not explicitly BSA-normalized to 1.73m². "
                    f"Treating {value} as ml/min/1.73m² — actual value may differ."
                )

            logging.info(f"Converted {value} {source_unit} to {converted_value:.2f} {target_unit}")
            return {'value': converted_value, 'status': cls.STATUS_OK,
                    'source_unit': raw_unit, 'target_unit': target_unit,
                    'raw_value': value}

        # 3. Unknown unit — value and unit present but no conversion rule
        logging.warning(
            f"Unit mismatch and no conversion rule found for Observation. "
            f"Received: '{source_unit}', Expected: '{target_unit}'. "
            f"Raw value: {value}. Refusing to guess — treating as unusable."
        )
        return {'value': None, 'status': cls.STATUS_UNKNOWN_UNIT,
                'source_unit': raw_unit, 'target_unit': target_unit,
                'raw_value': value}
    
    @classmethod
    def validate_egfr_inputs(cls, cr_val, age, gender):
        """
        Validate inputs for eGFR calculation.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for None values
        if cr_val is None:
            return False, "Creatinine value is required"
        if age is None:
            return False, "Age is required"
        if gender is None:
            return False, "Gender is required"
        
        # Validate gender
        if gender not in ['male', 'female']:
            return False, f"Invalid gender: '{gender}'. Must be 'male' or 'female'"
        
        # Validate creatinine range
        cr_range = cls.VALIDATION_RANGES['creatinine']
        if cr_val <= 0:
            return False, "Creatinine must be a positive value"
        if cr_val < cr_range['min']:
            return False, f"Creatinine {cr_val} mg/dL is below minimum ({cr_range['min']} mg/dL)"
        if cr_val > cr_range['max']:
            return False, f"Creatinine {cr_val} mg/dL exceeds maximum ({cr_range['max']} mg/dL)"
        
        # Validate age range
        age_range = cls.VALIDATION_RANGES['age']
        if age < age_range['min']:
            return False, f"eGFR calculation requires adult age (≥{age_range['min']} years)"
        if age > age_range['max']:
            return False, f"Age {age} exceeds maximum ({age_range['max']} years)"
        
        return True, None
    
    @classmethod
    def calculate_egfr(cls, cr_val, age, gender):
        """
        Calculates eGFR using the CKD-EPI 2021 equation (race-free version).
        
        Reference:
            Inker LA, et al. New creatinine- and cystatin C-based equations to estimate 
            GFR without race. N Engl J Med. 2021;385(19):1737-1749.
            doi: 10.1056/NEJMoa2102953
        
        Args:
            cr_val: Creatinine value in mg/dL
            age: Patient age in years (must be ≥18)
            gender: 'male' or 'female'
        
        Returns:
            Tuple of (egfr_value, calculation_method_or_error)
        """
        # Validate inputs
        is_valid, error_message = cls.validate_egfr_inputs(cr_val, age, gender)
        if not is_valid:
            logging.warning(f"eGFR calculation skipped: {error_message}")
            return None, error_message
        
        # CKD-EPI 2021 constants
        # κ (kappa) = 0.7 for females, 0.9 for males
        # α (alpha) = -0.241 for females, -0.302 for males
        kappa = 0.7 if gender == 'female' else 0.9
        alpha = -0.241 if gender == 'female' else -0.302
        female_multiplier = 1.012 if gender == 'female' else 1.0
        
        # CKD-EPI 2021 formula:
        # eGFR = 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^(-1.2) × 0.9938^age × (1.012 if female)
        scr_over_kappa = cr_val / kappa
        min_term = min(scr_over_kappa, 1.0) ** alpha
        max_term = max(scr_over_kappa, 1.0) ** (-1.2)
        age_term = 0.9938 ** age
        
        egfr = 142 * min_term * max_term * age_term * female_multiplier
        
        # Round to integer (clinical standard)
        egfr_rounded = round(egfr)
        
        logging.debug(
            f"eGFR calculated: Cr={cr_val} mg/dL, Age={age}, Gender={gender} -> {egfr_rounded} mL/min/1.73m²"
        )
        
        return egfr_rounded, "CKD-EPI 2021"


# Global instance for easy access
unit_converter = UnitConversionService()
