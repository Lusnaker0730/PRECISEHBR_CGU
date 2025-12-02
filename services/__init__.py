"""
Services Package
Microservice modules for SMART FHIR App
"""

# Configuration
from services.config_loader import config_loader, ConfigLoader

# Unit Conversion
from services.unit_conversion_service import unit_converter, UnitConversionService

# FHIR Client
from services.fhir_client_service import (
    FHIRClientService,
    get_fhir_data  # Legacy function
)

# Condition Checking
from services.condition_checker import condition_checker, ConditionCheckerService

# Risk Classification
from services.risk_classifier import risk_classifier, RiskClassifierService

# PRECISE-HBR Calculator
from services.precise_hbr_calculator import (
    precise_hbr_calculator,
    PreciseHBRCalculator,
    calculate_precise_hbr_score,  # Legacy function
    calculate_risk_components  # Legacy function
)

# Tradeoff Model Calculator
from services.tradeoff_model_calculator import (
    tradeoff_calculator,
    TradeoffModelCalculator,
    get_tradeoff_model_data,  # Legacy function
    get_tradeoff_model_predictors,  # Legacy function
    detect_tradeoff_factors,  # Legacy function
    calculate_tradeoff_scores,  # Legacy function
    calculate_tradeoff_scores_interactive  # Legacy function
)

# TW Core IG Adapter (Taiwan-specific FHIR profiles)
from services.twcore_adapter import twcore_adapter, TWCoreAdapter

# FHIR Utilities
from services.fhir_utils import (
    get_observation_effective_date,
    get_observation_effective_date_from_model,
    sort_observations_by_date,
    sort_bundle_entries_by_date,
    extract_most_recent_observation
)

__all__ = [
    # Service instances
    'config_loader',
    'unit_converter',
    'condition_checker',
    'risk_classifier',
    'precise_hbr_calculator',
    'tradeoff_calculator',
    'twcore_adapter',  # TW Core IG Adapter
    
    # Service classes
    'ConfigLoader',
    'UnitConversionService',
    'FHIRClientService',
    'ConditionCheckerService',
    'RiskClassifierService',
    'PreciseHBRCalculator',
    'TradeoffModelCalculator',
    'TWCoreAdapter',  # TW Core IG Adapter Class
    
    # Legacy functions
    'get_fhir_data',
    'calculate_precise_hbr_score',
    'calculate_risk_components',
    'get_tradeoff_model_data',
    'get_tradeoff_model_predictors',
    'detect_tradeoff_factors',
    'calculate_tradeoff_scores',
    'calculate_tradeoff_scores_interactive',
    
    # FHIR Utilities
    'get_observation_effective_date',
    'get_observation_effective_date_from_model',
    'sort_observations_by_date',
    'sort_bundle_entries_by_date',
    'extract_most_recent_observation',
]

