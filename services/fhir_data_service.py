"""
FHIR Data Service - Legacy Facade (Deprecated)

This module is a backward-compatible facade for the refactored microservices.
All functions here delegate to their canonical service implementations.

DEPRECATION NOTICE:
    Import directly from the canonical service instead of this facade.
    This module will be removed in a future version.

    Migration guide:
        # Old (deprecated):
        from services.fhir_data_service import get_patient_demographics
        from services import fhir_data_service
        fhir_data_service.calculate_precise_hbr_score(...)

        # New (preferred):
        from services.twcore_adapter import twcore_adapter
        twcore_adapter.get_patient_demographics(...)

        from services.precise_hbr_calculator import precise_hbr_calculator
        precise_hbr_calculator.calculate_score(...)

    Full mapping:
        get_patient_demographics     -> twcore_adapter.get_patient_demographics()
        get_fhir_data                -> fhir_client_service.get_fhir_data()
        calculate_precise_hbr_score  -> precise_hbr_calculator.calculate_score()
        calculate_risk_components    -> precise_hbr_calculator.calculate_score()
        get_precise_hbr_display_info -> risk_classifier.get_precise_hbr_display_info()
        get_risk_category_info       -> risk_classifier.get_risk_category_info()
        calculate_bleeding_risk_pct  -> risk_classifier.calculate_bleeding_risk_percentage()
        get_score_from_table         -> risk_classifier.get_score_from_table()
        check_bleeding_history       -> condition_checker.check_prior_bleeding()
        check_oral_anticoagulation   -> condition_checker.check_oral_anticoagulation()
        check_bleeding_diathesis_upd -> condition_checker.check_bleeding_diathesis()
        check_prior_bleeding_updated -> condition_checker.check_prior_bleeding()
        check_liver_cirrhosis_...    -> condition_checker.check_liver_cirrhosis_with_portal_hypertension()
        check_active_cancer_updated  -> condition_checker.check_active_cancer()
        get_condition_text           -> condition_checker.get_condition_text()
        check_arc_hbr_factors        -> condition_checker.check_arc_hbr_factors_summary()
        check_arc_hbr_factors_detail -> condition_checker.check_arc_hbr_factors_detailed()
        get_active_medications       -> condition_checker.get_active_medications()
        check_medication_interact..  -> condition_checker.check_medication_interactions_bleeding_risk()
        get_value_from_observation   -> unit_converter.get_value_from_observation()
        calculate_egfr               -> unit_converter.calculate_egfr()
        convert_hr_to_probability    -> tradeoff_calculator.convert_hr_to_probability()
        get_tradeoff_model_data      -> tradeoff_model_calculator (module-level function)
        get_tradeoff_model_predictors -> tradeoff_model_calculator (module-level function)
        calculate_tradeoff_scores    -> tradeoff_model_calculator (module-level function)
        calculate_tradeoff_scores_interactive -> tradeoff_model_calculator (module-level function)
        detect_tradeoff_factors      -> tradeoff_model_calculator (module-level function)
"""
import warnings
import logging

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


# ---------------------------------------------------------------------------
# Deprecation helper
# ---------------------------------------------------------------------------

def _deprecated(old_name: str, new_location: str):
    """Emit a DeprecationWarning for a legacy facade function."""
    warnings.warn(
        f"fhir_data_service.{old_name}() is deprecated. "
        f"Use {new_location} instead. "
        f"This facade will be removed in a future version.",
        DeprecationWarning,
        stacklevel=3,
    )


# ---------------------------------------------------------------------------
# Legacy Global Variables (deprecated — use service properties directly)
# ---------------------------------------------------------------------------

def _get_cdss_config():
    """Deprecated. Use config_loader.config instead."""
    _deprecated('CDSS_CONFIG', 'config_loader.config')
    return config_loader.config


def _get_loinc_codes_var():
    """Deprecated. Use config_loader.get_loinc_codes() instead."""
    _deprecated('LOINC_CODES', 'config_loader.get_loinc_codes()')
    return config_loader.get_loinc_codes()


def _get_text_search_terms_var():
    """Deprecated. Use config_loader.get_text_search_terms() instead."""
    _deprecated('TEXT_SEARCH_TERMS', 'config_loader.get_text_search_terms()')
    return config_loader.get_text_search_terms()


def _get_target_units():
    """Deprecated. Use unit_converter.TARGET_UNITS instead."""
    _deprecated('TARGET_UNITS', 'unit_converter.TARGET_UNITS')
    return unit_converter.TARGET_UNITS


# Keep module-level names for import compatibility, but as live references
# so they don't become stale snapshots.
CDSS_CONFIG = config_loader.config
LOINC_CODES = config_loader.get_loinc_codes()
TEXT_SEARCH_TERMS = config_loader.get_text_search_terms()
TARGET_UNITS = unit_converter.TARGET_UNITS


# ---------------------------------------------------------------------------
# Legacy Helper Functions (deprecated)
# ---------------------------------------------------------------------------

def _get_loinc_codes():
    """Deprecated. Use config_loader.get_loinc_codes()."""
    _deprecated('_get_loinc_codes', 'config_loader.get_loinc_codes()')
    return config_loader.get_loinc_codes()


def _get_text_search_terms():
    """Deprecated. Use config_loader.get_text_search_terms()."""
    _deprecated('_get_text_search_terms', 'config_loader.get_text_search_terms()')
    return config_loader.get_text_search_terms()


def _resource_has_code(resource, system, code):
    """Deprecated. Use condition_checker.resource_has_code()."""
    _deprecated('_resource_has_code', 'condition_checker.resource_has_code()')
    return condition_checker.resource_has_code(resource, system, code)


def _is_within_time_window(resource_date_str, min_months=None, max_months=None):
    """Check if a resource date falls within the specified time window from today.

    Note: This function has unique logic not delegated elsewhere. It will be
    moved to a utility module in Phase 2.
    """
    if not resource_date_str:
        return False

    try:
        from dateutil.parser import parse as parse_date
        from dateutil.relativedelta import relativedelta
        import datetime as dt

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


# ---------------------------------------------------------------------------
# Patient Demographics (deprecated)
# ---------------------------------------------------------------------------

def get_patient_demographics(patient_resource, use_twcore=True):
    """Deprecated. Use twcore_adapter.get_patient_demographics()."""
    _deprecated('get_patient_demographics', 'twcore_adapter.get_patient_demographics()')
    return twcore_adapter.get_patient_demographics(patient_resource, use_twcore)


# ---------------------------------------------------------------------------
# Unit Conversion (deprecated)
# ---------------------------------------------------------------------------

def get_value_from_observation(obs, unit_system):
    """Deprecated. Use unit_converter.get_value_from_observation()."""
    _deprecated('get_value_from_observation', 'unit_converter.get_value_from_observation()')
    return unit_converter.get_value_from_observation(obs, unit_system)


def calculate_egfr(cr_val, age, gender):
    """Deprecated. Use unit_converter.calculate_egfr()."""
    _deprecated('calculate_egfr', 'unit_converter.calculate_egfr()')
    return unit_converter.calculate_egfr(cr_val, age, gender)


# ---------------------------------------------------------------------------
# Risk Classification (deprecated)
# ---------------------------------------------------------------------------

def get_score_from_table(value, score_table, range_key):
    """Deprecated. Use risk_classifier.get_score_from_table()."""
    _deprecated('get_score_from_table', 'risk_classifier.get_score_from_table()')
    return risk_classifier.get_score_from_table(value, score_table, range_key)


def calculate_bleeding_risk_percentage(precise_hbr_score):
    """Deprecated. Use risk_classifier.calculate_bleeding_risk_percentage()."""
    _deprecated('calculate_bleeding_risk_percentage', 'risk_classifier.calculate_bleeding_risk_percentage()')
    return risk_classifier.calculate_bleeding_risk_percentage(precise_hbr_score)


def get_risk_category_info(precise_hbr_score):
    """Deprecated. Use risk_classifier.get_risk_category_info()."""
    _deprecated('get_risk_category_info', 'risk_classifier.get_risk_category_info()')
    return risk_classifier.get_risk_category_info(precise_hbr_score)


def get_precise_hbr_display_info(precise_hbr_score):
    """Deprecated. Use risk_classifier.get_precise_hbr_display_info()."""
    _deprecated('get_precise_hbr_display_info', 'risk_classifier.get_precise_hbr_display_info()')
    return risk_classifier.get_precise_hbr_display_info(precise_hbr_score)


# ---------------------------------------------------------------------------
# Condition Checking (deprecated)
# ---------------------------------------------------------------------------

def check_bleeding_history(conditions):
    """Deprecated. Use condition_checker.check_prior_bleeding()."""
    _deprecated('check_bleeding_history', 'condition_checker.check_prior_bleeding()')
    return condition_checker.check_prior_bleeding(conditions)


def check_oral_anticoagulation(medications):
    """Deprecated. Use condition_checker.check_oral_anticoagulation()."""
    _deprecated('check_oral_anticoagulation', 'condition_checker.check_oral_anticoagulation()')
    return condition_checker.check_oral_anticoagulation(medications)


def check_bleeding_diathesis_updated(conditions):
    """Deprecated. Use condition_checker.check_bleeding_diathesis()."""
    _deprecated('check_bleeding_diathesis_updated', 'condition_checker.check_bleeding_diathesis()')
    return condition_checker.check_bleeding_diathesis(conditions)


def check_prior_bleeding_updated(conditions):
    """Deprecated. Use condition_checker.check_prior_bleeding()."""
    _deprecated('check_prior_bleeding_updated', 'condition_checker.check_prior_bleeding()')
    return condition_checker.check_prior_bleeding(conditions)


def check_liver_cirrhosis_portal_hypertension_updated(conditions):
    """Deprecated. Use condition_checker.check_liver_cirrhosis_with_portal_hypertension()."""
    _deprecated(
        'check_liver_cirrhosis_portal_hypertension_updated',
        'condition_checker.check_liver_cirrhosis_with_portal_hypertension()',
    )
    return condition_checker.check_liver_cirrhosis_with_portal_hypertension(conditions)


def check_active_cancer_updated(conditions):
    """Deprecated. Use condition_checker.check_active_cancer()."""
    _deprecated('check_active_cancer_updated', 'condition_checker.check_active_cancer()')
    return condition_checker.check_active_cancer(conditions)


def get_condition_text(condition):
    """Deprecated. Use condition_checker.get_condition_text()."""
    _deprecated('get_condition_text', 'condition_checker.get_condition_text()')
    return condition_checker.get_condition_text(condition)


def check_arc_hbr_factors(raw_data, medications):
    """Deprecated. Use condition_checker.check_arc_hbr_factors_summary()."""
    _deprecated('check_arc_hbr_factors', 'condition_checker.check_arc_hbr_factors_summary()')
    return condition_checker.check_arc_hbr_factors_summary(raw_data, medications)


def check_arc_hbr_factors_detailed(raw_data, medications):
    """Deprecated. Use condition_checker.check_arc_hbr_factors_detailed()."""
    _deprecated('check_arc_hbr_factors_detailed', 'condition_checker.check_arc_hbr_factors_detailed()')
    return condition_checker.check_arc_hbr_factors_detailed(raw_data, medications)


# ---------------------------------------------------------------------------
# Medication Analysis (deprecated)
# ---------------------------------------------------------------------------

def get_active_medications(raw_data, demographics=None):
    """Deprecated. Use condition_checker.get_active_medications()."""
    _deprecated('get_active_medications', 'condition_checker.get_active_medications()')
    return condition_checker.get_active_medications(raw_data, demographics)


def check_medication_interactions_bleeding_risk(medications):
    """Deprecated. Use condition_checker.check_medication_interactions_bleeding_risk()."""
    _deprecated(
        'check_medication_interactions_bleeding_risk',
        'condition_checker.check_medication_interactions_bleeding_risk()',
    )
    return condition_checker.check_medication_interactions_bleeding_risk(medications)


# ---------------------------------------------------------------------------
# Tradeoff Analysis (deprecated — these are re-exports, not wrappers)
# ---------------------------------------------------------------------------

def convert_hr_to_probability(total_hr_score, baseline_event_rate):
    """Deprecated. Use tradeoff_calculator.convert_hr_to_probability()."""
    _deprecated('convert_hr_to_probability', 'tradeoff_calculator.convert_hr_to_probability()')
    return tradeoff_calculator.convert_hr_to_probability(total_hr_score, baseline_event_rate)


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------
__all__ = [
    # Configuration constants (deprecated)
    'CDSS_CONFIG',
    'LOINC_CODES',
    'TARGET_UNITS',
    'TEXT_SEARCH_TERMS',
    # Service instances (re-exports — prefer importing from canonical module)
    'condition_checker',
    'config_loader',
    'precise_hbr_calculator',
    'risk_classifier',
    'tradeoff_calculator',
    'twcore_adapter',
    'unit_converter',
    # Service classes (re-exports)
    'TWCoreAdapter',
    # FHIR data retrieval (re-exports)
    'get_fhir_data',
    'get_tradeoff_model_data',
    'get_tradeoff_model_predictors',
    # Deprecated wrapper functions
    'get_patient_demographics',
    'calculate_egfr',
    'get_value_from_observation',
    'calculate_precise_hbr_score',
    'calculate_risk_components',
    'calculate_tradeoff_scores',
    'calculate_tradeoff_scores_interactive',
    'convert_hr_to_probability',
    'detect_tradeoff_factors',
    'calculate_bleeding_risk_percentage',
    'get_precise_hbr_display_info',
    'get_risk_category_info',
    'get_score_from_table',
    'check_active_cancer_updated',
    'check_arc_hbr_factors',
    'check_arc_hbr_factors_detailed',
    'check_bleeding_diathesis_updated',
    'check_bleeding_history',
    'check_liver_cirrhosis_portal_hypertension_updated',
    'check_oral_anticoagulation',
    'check_prior_bleeding_updated',
    'get_condition_text',
    'check_medication_interactions_bleeding_risk',
    'get_active_medications',
]
