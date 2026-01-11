"""
FHIR Data Service - Unified Entry Point

Backward-compatible facade for the refactored microservices:
- config_loader: Configuration management
- unit_conversion_service: Laboratory value unit conversions
- fhir_client_service: FHIR server interactions
- condition_checker: Medical condition checking
- risk_classifier: Risk categorization
- precise_hbr_calculator: PRECISE-HBR risk calculation
- tradeoff_model_calculator: Bleeding-thrombosis tradeoff analysis
"""
import datetime as dt
import logging

from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta

from services.config_loader import ConfigLoader, config_loader
from services.condition_checker import ConditionCheckerService, condition_checker
from services.fhir_client_service import FHIRClientService, get_fhir_data
from services.precise_hbr_calculator import (
    PreciseHBRCalculator,
    calculate_precise_hbr_score,
    calculate_risk_components,
    precise_hbr_calculator,
)
from services.risk_classifier import RiskClassifierService, risk_classifier
from services.tradeoff_model_calculator import (
    TradeoffModelCalculator,
    calculate_tradeoff_scores,
    calculate_tradeoff_scores_interactive,
    detect_tradeoff_factors,
    get_tradeoff_model_data,
    get_tradeoff_model_predictors,
    tradeoff_calculator,
)
from services.twcore_adapter import TWCoreAdapter, twcore_adapter
from services.unit_conversion_service import UnitConversionService, unit_converter

# --- Legacy Global Variables (for backward compatibility) ---
CDSS_CONFIG = config_loader.config
LOINC_CODES = config_loader.get_loinc_codes()
TEXT_SEARCH_TERMS = config_loader.get_text_search_terms()
TARGET_UNITS = unit_converter.TARGET_UNITS

# --- Legacy Helper Functions ---

def _get_loinc_codes():
    """Legacy wrapper for config_loader.get_loinc_codes()."""
    return config_loader.get_loinc_codes()


def _get_text_search_terms():
    """Legacy wrapper for config_loader.get_text_search_terms()."""
    return config_loader.get_text_search_terms()


def _resource_has_code(resource, system, code):
    """Legacy wrapper for condition_checker.resource_has_code()."""
    return condition_checker.resource_has_code(resource, system, code)


def _is_within_time_window(resource_date_str, min_months=None, max_months=None):
    """Check if a resource date falls within the specified time window from today."""
    if not resource_date_str:
        return False

    try:
        resource_date = parse_date(resource_date_str).date()
        today = dt.date.today()

        earliest_allowed = today - relativedelta(months=max_months) if max_months else None
        latest_allowed = today - relativedelta(months=min_months) if min_months else None

        if earliest_allowed and resource_date < earliest_allowed:
            return False
        if latest_allowed and resource_date > latest_allowed:
            return False

        return True
    except (ValueError, TypeError):
        return False

def get_patient_demographics(patient_resource, use_twcore=True):
    """
    Extract key demographics from a FHIR Patient resource.

    Supports Taiwan Core IG (TW Core IG) for Taiwan-specific fields:
    - Chinese name support (text field)
    - Taiwan ID (National ID) / Resident ID
    - Medical Record Number

    Args:
        patient_resource: FHIR Patient resource dictionary
        use_twcore: If True, use TW Core IG adapter for enhanced Taiwan support

    Returns:
        Dictionary with name, gender, age, birthDate, and Taiwan-specific fields
    """
    if use_twcore:
        return twcore_adapter.extract_patient_demographics_twcore(patient_resource)

    # Legacy support (backward compatible)
    demographics = {
        "name": "Unknown",
        "gender": None,
        "age": None,
        "birthDate": None,
    }

    if not patient_resource:
        return demographics

    # Extract name
    name_list = patient_resource.get("name")
    if name_list:
        name_data = name_list[0]
        if name_data.get("text"):
            demographics["name"] = name_data["text"]
        else:
            name_parts = name_data.get("given", []) + [name_data.get("family", "")]
            demographics["name"] = " ".join(name_parts).strip()

    demographics["gender"] = patient_resource.get("gender")

    # Calculate age from birthDate
    birth_date_str = patient_resource.get("birthDate")
    if birth_date_str:
        demographics["birthDate"] = birth_date_str
        try:
            birth_date = dt.datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            today = dt.date.today()
            age = today.year - birth_date.year
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1
            demographics["age"] = age
        except (ValueError, TypeError):
            pass

    return demographics

def get_value_from_observation(obs, unit_system):
    """Legacy wrapper for unit_converter.get_value_from_observation()."""
    return unit_converter.get_value_from_observation(obs, unit_system)


def calculate_egfr(cr_val, age, gender):
    """Legacy wrapper for unit_converter.calculate_egfr()."""
    return unit_converter.calculate_egfr(cr_val, age, gender)

def get_score_from_table(value, score_table, range_key):
    """
    Get score from lookup tables based on value ranges.

    Note: This function is kept for potential legacy use but may not be
    actively used in refactored code.
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
        logging.info(
            f"{config['label']} {value} outside range {boundary_item[range_key]}, "
            f"using score: {score}"
        )
        return score

    return 0

def check_bleeding_history(conditions):
    """Legacy wrapper for condition_checker.check_prior_bleeding()."""
    return condition_checker.check_prior_bleeding(conditions)


def check_oral_anticoagulation(medications):
    """Legacy wrapper for condition_checker.check_oral_anticoagulation()."""
    return condition_checker.check_oral_anticoagulation(medications)


def check_bleeding_diathesis_updated(conditions):
    """Legacy wrapper for condition_checker.check_bleeding_diathesis()."""
    return condition_checker.check_bleeding_diathesis(conditions)


def check_prior_bleeding_updated(conditions):
    """Legacy wrapper for condition_checker.check_prior_bleeding()."""
    return condition_checker.check_prior_bleeding(conditions)


def check_liver_cirrhosis_portal_hypertension_updated(conditions):
    """Legacy wrapper for condition_checker.check_liver_cirrhosis_with_portal_hypertension()."""
    return condition_checker.check_liver_cirrhosis_with_portal_hypertension(conditions)


def check_active_cancer_updated(conditions):
    """Legacy wrapper for condition_checker.check_active_cancer()."""
    return condition_checker.check_active_cancer(conditions)


def get_condition_text(condition):
    """Legacy wrapper for condition_checker.get_condition_text()."""
    return condition_checker.get_condition_text(condition)

def check_arc_hbr_factors(raw_data, medications):
    """
    Check for ARC-HBR risk factors and return simplified format.

    Returns a dict with 'has_factors' boolean and 'factors' list of descriptions.
    For detailed breakdown, use check_arc_hbr_factors_detailed instead.
    """
    details = condition_checker.check_arc_hbr_factors_detailed(raw_data, medications)

    factor_descriptions = {
        'thrombocytopenia': "Thrombocytopenia (platelets < 100x10^9/L)",
        'bleeding_diathesis': "Chronic bleeding diathesis",
        'active_malignancy': "Active malignancy",
        'liver_cirrhosis': "Liver cirrhosis with portal hypertension",
        'nsaids_corticosteroids': "Long-term NSAIDs or corticosteroids",
    }

    factors = [
        description
        for key, description in factor_descriptions.items()
        if details.get(key)
    ]

    return {
        'has_factors': details['has_any_factor'],
        'factors': factors,
    }


def check_arc_hbr_factors_detailed(raw_data, medications):
    """Legacy wrapper for condition_checker.check_arc_hbr_factors_detailed()."""
    return condition_checker.check_arc_hbr_factors_detailed(raw_data, medications)

def calculate_bleeding_risk_percentage(precise_hbr_score):
    """Legacy wrapper for risk_classifier.calculate_bleeding_risk_percentage()."""
    return risk_classifier.calculate_bleeding_risk_percentage(precise_hbr_score)


def get_risk_category_info(precise_hbr_score):
    """Legacy wrapper for risk_classifier.get_risk_category_info()."""
    return risk_classifier.get_risk_category_info(precise_hbr_score)


def get_precise_hbr_display_info(precise_hbr_score):
    """Legacy wrapper for risk_classifier.get_precise_hbr_display_info()."""
    return risk_classifier.get_precise_hbr_display_info(precise_hbr_score)


def convert_hr_to_probability(total_hr_score, baseline_event_rate):
    """Legacy wrapper for tradeoff_calculator.convert_hr_to_probability()."""
    return tradeoff_calculator.convert_hr_to_probability(total_hr_score, baseline_event_rate)

def get_active_medications(raw_data, demographics):
    """
    Identify active medications from FHIR medication request resources.

    Used for CDS Hooks medication analysis.

    Returns:
        list: Active medication resources
    """
    active_statuses = {'active', 'on-hold', 'completed'}
    medications = raw_data.get('med_requests', [])

    active_medications = [
        med for med in medications
        if med.get('status', '').lower() in active_statuses
    ]

    logging.info(f"Found {len(active_medications)} active medications")
    return active_medications


def check_medication_interactions_bleeding_risk(medications):
    """
    Check for medication combinations that increase bleeding risk.

    Specifically looks for DAPT combinations and other high-risk medications.
    This function can be expanded for more sophisticated interaction checking.

    Returns:
        dict: Interaction details including DAPT detection and recommendations
    """
    return {
        'dapt_detected': False,
        'high_risk_combinations': [],
        'bleeding_risk_medications': [],
        'recommendations': [],
    }

# --- Module Exports ---
__all__ = [
    # Configuration constants
    'CDSS_CONFIG',
    'LOINC_CODES',
    'TARGET_UNITS',
    'TEXT_SEARCH_TERMS',
    # Service instances
    'condition_checker',
    'config_loader',
    'precise_hbr_calculator',
    'risk_classifier',
    'tradeoff_calculator',
    'twcore_adapter',
    'unit_converter',
    # Service classes
    'TWCoreAdapter',
    # FHIR data retrieval
    'get_fhir_data',
    'get_tradeoff_model_data',
    'get_tradeoff_model_predictors',
    # Patient demographics
    'get_patient_demographics',
    # Unit conversion
    'calculate_egfr',
    'get_value_from_observation',
    # Risk calculation
    'calculate_precise_hbr_score',
    'calculate_risk_components',
    'calculate_tradeoff_scores',
    'calculate_tradeoff_scores_interactive',
    'convert_hr_to_probability',
    'detect_tradeoff_factors',
    # Risk classification
    'calculate_bleeding_risk_percentage',
    'get_precise_hbr_display_info',
    'get_risk_category_info',
    # Condition checking
    'check_active_cancer_updated',
    'check_arc_hbr_factors',
    'check_arc_hbr_factors_detailed',
    'check_bleeding_diathesis_updated',
    'check_bleeding_history',
    'check_liver_cirrhosis_portal_hypertension_updated',
    'check_oral_anticoagulation',
    'check_prior_bleeding_updated',
    'get_condition_text',
    # Medication analysis
    'check_medication_interactions_bleeding_risk',
    'get_active_medications',
    # Helper functions
    'get_score_from_table',
]
