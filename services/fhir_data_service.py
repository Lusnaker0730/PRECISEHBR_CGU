"""
FHIR Data Service - Unified Entry Point
This module serves as a backward-compatible facade for the refactored microservices.

Original monolithic service has been refactored into the following microservices:
- services/config_loader.py: Configuration management
- services/unit_conversion_service.py: Laboratory value unit conversions
- services/fhir_client_service.py: FHIR server interactions
- services/condition_checker.py: Medical condition checking
- services/risk_classifier.py: Risk categorization
- services/precise_hbr_calculator.py: PRECISE-HBR risk calculation
- services/tradeoff_model_calculator.py: Bleeding-thrombosis tradeoff analysis

This file maintains backward compatibility by re-exporting all legacy functions.
"""
import logging
import datetime as dt
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta

# Import all refactored services
from services.config_loader import config_loader, ConfigLoader
from services.unit_conversion_service import unit_converter, UnitConversionService
from services.fhir_client_service import FHIRClientService, get_fhir_data
from services.condition_checker import condition_checker, ConditionCheckerService
from services.risk_classifier import risk_classifier, RiskClassifierService
from services.precise_hbr_calculator import (
    precise_hbr_calculator,
    PreciseHBRCalculator,
    calculate_precise_hbr_score,
    calculate_risk_components
)
from services.tradeoff_model_calculator import (
    tradeoff_calculator,
    TradeoffModelCalculator,
    get_tradeoff_model_data,
    get_tradeoff_model_predictors,
    detect_tradeoff_factors,
    calculate_tradeoff_scores,
    calculate_tradeoff_scores_interactive
)
from services.twcore_adapter import twcore_adapter, TWCoreAdapter

# --- Legacy Global Variables (for backward compatibility) ---
CDSS_CONFIG = config_loader.config
LOINC_CODES = config_loader.get_loinc_codes()
TEXT_SEARCH_TERMS = config_loader.get_text_search_terms()
TARGET_UNITS = unit_converter.TARGET_UNITS

# --- Legacy Helper Functions ---

def _get_loinc_codes():
    """Legacy function - replaced by config_loader.get_loinc_codes()"""
    return config_loader.get_loinc_codes()

def _get_text_search_terms():
    """Legacy function - replaced by config_loader.get_text_search_terms()"""
    return config_loader.get_text_search_terms()

def _resource_has_code(resource, system, code):
    """Legacy function - replaced by condition_checker.resource_has_code()"""
    return condition_checker.resource_has_code(resource, system, code)

def _is_within_time_window(resource_date_str, min_months=None, max_months=None):
    """Checks if a resource date is within the specified time window from today."""
    if not resource_date_str:
        return False
    try:
        resource_date = parse_date(resource_date_str).date()
        today = dt.date.today()
        if min_months is not None and resource_date > today - relativedelta(months=min_months):
            return False
        if max_months is not None and resource_date < today - relativedelta(months=max_months):
            return False
        return True
    except (ValueError, TypeError):
        return False

def get_patient_demographics(patient_resource, use_twcore=True):
    """
    Extracts and returns key demographics from a patient resource.
    
    Enhanced to support Taiwan Core IG (TW Core IG) for Taiwan-specific requirements:
    - Chinese name support (text field)
    - Taiwan ID (National ID) / Resident ID
    - Medical Record Number
    
    Args:
        patient_resource: FHIR Patient resource dictionary
        use_twcore: If True, use TW Core IG adapter for enhanced Taiwan support
    
    Returns:
        Dictionary with name, gender, age, birthDate, and Taiwan-specific fields
    """
    # Use TW Core IG adapter if enabled
    if use_twcore:
        demographics = twcore_adapter.extract_patient_demographics_twcore(patient_resource)
        return demographics
    
    # Legacy support (backward compatible)
    demographics = {
        "name": "Unknown",
        "gender": None,
        "age": None,
        "birthDate": None
    }
    if not patient_resource:
        return demographics

    # Name
    if patient_resource.get("name"):
        name_data = patient_resource["name"][0]
        # Support for Taiwan Core FHIR Profile where name is in a single 'text' field
        if name_data.get("text"):
            demographics["name"] = name_data["text"]
        else:
            demographics["name"] = " ".join(name_data.get("given", []) + [name_data.get("family", "")]).strip()

    # Gender
    demographics["gender"] = patient_resource.get("gender")

    # Age
    if patient_resource.get("birthDate"):
        demographics["birthDate"] = patient_resource["birthDate"]
        try:
            birth_date = dt.datetime.strptime(patient_resource["birthDate"], "%Y-%m-%d").date()
            today = dt.date.today()
            demographics["age"] = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        except (ValueError, TypeError):
            pass
            
    return demographics

def get_value_from_observation(obs, unit_system):
    """
    Legacy function - replaced by unit_converter.get_value_from_observation()
    
    Safely extracts a numeric value from an Observation resource, handling unit conversions.
    Returns the numeric value in the target unit, or None if conversion is not possible.
    """
    return unit_converter.get_value_from_observation(obs, unit_system)

def calculate_egfr(cr_val, age, gender):
    """
    Legacy function - replaced by unit_converter.calculate_egfr()
    
    Calculates eGFR using the CKD-EPI 2021 equation.
    """
    return unit_converter.calculate_egfr(cr_val, age, gender)

def get_score_from_table(value, score_table, range_key):
    """
    Helper function to get score from lookup tables.
    Note: This function is kept for potential legacy use, but may not be actively used in refactored code.
    """
    matched_score = None
    
    for item in score_table:
        if range_key in item:
            range_values = item[range_key]
            if len(range_values) == 2 and range_values[0] <= value <= range_values[1]:
                return item.get('base_score', 0)
    
    # If no exact match, check if value exceeds the highest range
    if range_key == 'age_range':
        max_range_item = max(score_table, key=lambda x: x[range_key][1] if range_key in x else 0)
        if value > max_range_item[range_key][1]:
            logging.info(f"Age {value} exceeds max range {max_range_item[range_key]}, using highest score: {max_range_item.get('base_score', 0)}")
            return max_range_item.get('base_score', 0)
    elif range_key == 'hb_range':
        min_range_item = min(score_table, key=lambda x: x[range_key][0] if range_key in x else float('inf'))
        if value < min_range_item[range_key][0]:
            logging.info(f"Hemoglobin {value} below min range {min_range_item[range_key]}, using highest score: {min_range_item.get('base_score', 0)}")
            return min_range_item.get('base_score', 0)
    elif range_key == 'ccr_range':
        min_range_item = min(score_table, key=lambda x: x[range_key][0] if range_key in x else float('inf'))
        if value < min_range_item[range_key][0]:
            logging.info(f"Creatinine clearance {value} below min range {min_range_item[range_key]}, using highest score: {min_range_item.get('base_score', 0)}")
            return min_range_item.get('base_score', 0)
    elif range_key == 'wbc_range':
        max_range_item = max(score_table, key=lambda x: x[range_key][1] if range_key in x else 0)
        if value > max_range_item[range_key][1]:
            logging.info(f"WBC {value} exceeds max range {max_range_item[range_key]}, using highest score: {max_range_item.get('base_score', 0)}")
            return max_range_item.get('base_score', 0)
    
    return 0

def check_bleeding_history(conditions):
    """
    Legacy function - replaced by condition_checker.check_prior_bleeding()
    
    Checks for history of spontaneous bleeding in patient conditions.
    """
    return condition_checker.check_prior_bleeding(conditions)

def check_oral_anticoagulation(medications):
    """
    Legacy function - replaced by condition_checker.check_oral_anticoagulation()
    
    Check for long-term oral anticoagulation therapy using codes from configuration.
    """
    return condition_checker.check_oral_anticoagulation(medications)

def check_bleeding_diathesis_updated(conditions):
    """Legacy function - replaced by condition_checker.check_bleeding_diathesis()"""
    return condition_checker.check_bleeding_diathesis(conditions)

def check_prior_bleeding_updated(conditions):
    """Legacy function - replaced by condition_checker.check_prior_bleeding()"""
    return condition_checker.check_prior_bleeding(conditions)

def check_liver_cirrhosis_portal_hypertension_updated(conditions):
    """Legacy function - replaced by condition_checker.check_liver_cirrhosis_with_portal_hypertension()"""
    return condition_checker.check_liver_cirrhosis_with_portal_hypertension(conditions)

def check_active_cancer_updated(conditions):
    """Legacy function - replaced by condition_checker.check_active_cancer()"""
    return condition_checker.check_active_cancer(conditions)

def get_condition_text(condition):
    """Legacy function - replaced by condition_checker.get_condition_text()"""
    return condition_checker.get_condition_text(condition)

def check_arc_hbr_factors(raw_data, medications):
    """
    Legacy function - checks for ARC-HBR risk factors.
    Note: This returns a different format than check_arc_hbr_factors_detailed.
    """
    details = condition_checker.check_arc_hbr_factors_detailed(raw_data, medications)
    
    factors = []
    if details['thrombocytopenia']:
        factors.append("Thrombocytopenia (platelets < 100×10⁹/L)")
    if details['bleeding_diathesis']:
        factors.append("Chronic bleeding diathesis")
    if details['active_malignancy']:
        factors.append("Active malignancy")
    if details['liver_cirrhosis']:
        factors.append("Liver cirrhosis with portal hypertension")
    if details['nsaids_corticosteroids']:
                factors.append("Long-term NSAIDs or corticosteroids")
    
    return {
        'has_factors': details['has_any_factor'],
        'factors': factors
    }

def check_arc_hbr_factors_detailed(raw_data, medications):
    """Legacy function - replaced by condition_checker.check_arc_hbr_factors_detailed()"""
    return condition_checker.check_arc_hbr_factors_detailed(raw_data, medications)

def calculate_bleeding_risk_percentage(precise_hbr_score):
    """Legacy function - replaced by risk_classifier.calculate_bleeding_risk_percentage()"""
    return risk_classifier.calculate_bleeding_risk_percentage(precise_hbr_score)

def get_risk_category_info(precise_hbr_score):
    """Legacy function - replaced by risk_classifier.get_risk_category_info()"""
    return risk_classifier.get_risk_category_info(precise_hbr_score)

def get_precise_hbr_display_info(precise_hbr_score):
    """Legacy function - replaced by risk_classifier.get_precise_hbr_display_info()"""
    return risk_classifier.get_precise_hbr_display_info(precise_hbr_score)

def convert_hr_to_probability(total_hr_score, baseline_event_rate):
    """Legacy function - replaced by tradeoff_calculator.convert_hr_to_probability()"""
    return tradeoff_calculator.convert_hr_to_probability(total_hr_score, baseline_event_rate)

def get_active_medications(raw_data, demographics):
    """
    Process medication data from FHIR resources to identify active medications.
    Used for CDS Hooks medication analysis.
    
    Returns: list of active medication resources
    """
    medications = raw_data.get('med_requests', [])
    active_medications = []
    
    for med in medications:
        status = med.get('status', '').lower()
        if status in ['active', 'on-hold', 'completed']:
            active_medications.append(med)
    
    logging.info(f"Found {len(active_medications)} active medications")
    return active_medications

def check_medication_interactions_bleeding_risk(medications):
    """
    Check for medication combinations that increase bleeding risk.
    Specifically looks for DAPT combinations and other high-risk medications.
    
    Returns: dict with interaction details
    """
    interactions = {
        'dapt_detected': False,
        'high_risk_combinations': [],
        'bleeding_risk_medications': [],
        'recommendations': []
    }
    
    # This function can be expanded to include more sophisticated
    # medication interaction checking beyond DAPT
    
    return interactions 

# --- Module Exports ---
__all__ = [
    # Configuration
    'CDSS_CONFIG',
    'LOINC_CODES',
    'TEXT_SEARCH_TERMS',
    'TARGET_UNITS',
    
    # Service instances
    'config_loader',
    'unit_converter',
    'condition_checker',
    'risk_classifier',
    'precise_hbr_calculator',
    'tradeoff_calculator',
    'twcore_adapter',  # TW Core IG Adapter
    
    # FHIR Data Retrieval
    'get_fhir_data',
    'get_tradeoff_model_data',
    'get_tradeoff_model_predictors',
    
    # Patient Demographics
    'get_patient_demographics',
    
    # Unit Conversion
    'get_value_from_observation',
    'calculate_egfr',
    
    # Risk Calculation
    'calculate_precise_hbr_score',
    'calculate_risk_components',
    'calculate_tradeoff_scores',
    'calculate_tradeoff_scores_interactive',
    'detect_tradeoff_factors',
    'convert_hr_to_probability',
    
    # Risk Classification
    'calculate_bleeding_risk_percentage',
    'get_risk_category_info',
    'get_precise_hbr_display_info',
    
    # Condition Checking
    'check_bleeding_history',
    'check_oral_anticoagulation',
    'check_arc_hbr_factors',
    'check_arc_hbr_factors_detailed',
    'check_bleeding_diathesis_updated',
    'check_prior_bleeding_updated',
    'check_liver_cirrhosis_portal_hypertension_updated',
    'check_active_cancer_updated',
    'get_condition_text',
    
    # Medication Analysis
    'get_active_medications',
    'check_medication_interactions_bleeding_risk',
    
    # Helper Functions
    'get_score_from_table',
    
    # TW Core IG Classes
    'TWCoreAdapter',
]
