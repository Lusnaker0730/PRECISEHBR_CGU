"""
Tests for fhir_data_service.py Legacy Facade Deprecation

Verifies:
1. All facade functions emit DeprecationWarning
2. Facade functions still return correct results (backward compatibility)
3. Canonical service methods match facade output exactly
"""

import warnings

import pytest


pytestmark = [
    pytest.mark.requirement("SRS-003"),
    pytest.mark.design("SDS-003"),
]


# ============================================================
# Helpers
# ============================================================

def _call_with_deprecation_check(func, *args, **kwargs):
    """Call a function and assert it emits a DeprecationWarning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = func(*args, **kwargs)
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) >= 1, (
            f"{func.__name__} did not emit DeprecationWarning. "
            f"Got: {[x.category.__name__ for x in w]}"
        )
        msg = str(dep_warnings[0].message)
        assert 'deprecated' in msg.lower()
    return result


# ============================================================
# 1. Deprecation Warnings
# ============================================================

class TestFacadeDeprecationWarnings:
    """Every facade wrapper must emit DeprecationWarning."""

    def test_get_patient_demographics_warns(self):
        from services import fhir_data_service
        patient = {'resourceType': 'Patient', 'id': 'p1', 'gender': 'male'}
        _call_with_deprecation_check(
            fhir_data_service.get_patient_demographics, patient, use_twcore=False
        )

    def test_calculate_egfr_warns(self):
        from services import fhir_data_service
        _call_with_deprecation_check(fhir_data_service.calculate_egfr, 1.0, 50, 'male')

    def test_get_value_from_observation_warns(self):
        from services import fhir_data_service
        obs = {
            'resourceType': 'Observation',
            'valueQuantity': {'value': 12.0, 'unit': 'g/dL'},
        }
        _call_with_deprecation_check(
            fhir_data_service.get_value_from_observation, obs, {'unit': 'g/dL'}
        )

    def test_get_precise_hbr_display_info_warns(self):
        from services import fhir_data_service
        _call_with_deprecation_check(fhir_data_service.get_precise_hbr_display_info, 20)

    def test_get_risk_category_info_warns(self):
        from services import fhir_data_service
        _call_with_deprecation_check(fhir_data_service.get_risk_category_info, 25)

    def test_calculate_bleeding_risk_percentage_warns(self):
        from services import fhir_data_service
        _call_with_deprecation_check(fhir_data_service.calculate_bleeding_risk_percentage, 20)

    def test_get_score_from_table_warns(self):
        from services import fhir_data_service
        table = [{'age_range': [30, 50], 'base_score': 3}]
        _call_with_deprecation_check(fhir_data_service.get_score_from_table, 40, table, 'age_range')

    def test_check_bleeding_history_warns(self):
        from services import fhir_data_service
        _call_with_deprecation_check(fhir_data_service.check_bleeding_history, [])

    def test_check_oral_anticoagulation_warns(self):
        from services import fhir_data_service
        _call_with_deprecation_check(fhir_data_service.check_oral_anticoagulation, [])

    def test_check_bleeding_diathesis_updated_warns(self):
        from services import fhir_data_service
        _call_with_deprecation_check(fhir_data_service.check_bleeding_diathesis_updated, [])

    def test_check_active_cancer_updated_warns(self):
        from services import fhir_data_service
        _call_with_deprecation_check(fhir_data_service.check_active_cancer_updated, [])

    def test_check_arc_hbr_factors_warns(self):
        from services import fhir_data_service
        raw = {'conditions': [], 'med_requests': []}
        _call_with_deprecation_check(fhir_data_service.check_arc_hbr_factors, raw, [])

    def test_get_active_medications_warns(self):
        from services import fhir_data_service
        raw = {'med_requests': []}
        _call_with_deprecation_check(fhir_data_service.get_active_medications, raw)

    def test_check_medication_interactions_warns(self):
        from services import fhir_data_service
        _call_with_deprecation_check(
            fhir_data_service.check_medication_interactions_bleeding_risk, []
        )

    def test_get_condition_text_warns(self):
        from services import fhir_data_service
        cond = {'code': {'coding': [{'display': 'Diabetes'}]}}
        _call_with_deprecation_check(fhir_data_service.get_condition_text, cond)

    def test_convert_hr_to_probability_warns(self):
        from services import fhir_data_service
        _call_with_deprecation_check(fhir_data_service.convert_hr_to_probability, 1.5, 0.05)


# ============================================================
# 2. Backward Compatibility — facade returns same as canonical
# ============================================================

class TestFacadeBackwardCompatibility:
    """Facade functions must return identical results to canonical services."""

    def test_get_patient_demographics_matches_twcore(self):
        from services import fhir_data_service
        from services.twcore_adapter import twcore_adapter

        patient = {
            'resourceType': 'Patient', 'id': 'p1',
            'name': [{'family': 'Chen', 'given': ['Wei']}],
            'gender': 'male', 'birthDate': '1970-01-01',
        }

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            facade_result = fhir_data_service.get_patient_demographics(patient, use_twcore=False)

        canonical_result = twcore_adapter.get_patient_demographics(patient, use_twcore=False)
        assert facade_result == canonical_result

    def test_get_precise_hbr_display_info_matches_classifier(self):
        from services import fhir_data_service
        from services.risk_classifier import risk_classifier

        for score in [10, 20, 25, 30]:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                facade_result = fhir_data_service.get_precise_hbr_display_info(score)

            canonical_result = risk_classifier.get_precise_hbr_display_info(score)
            assert facade_result == canonical_result, f"Mismatch at score={score}"

    def test_calculate_egfr_matches_converter(self):
        from services import fhir_data_service
        from services.unit_conversion_service import unit_converter

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            facade_result = fhir_data_service.calculate_egfr(1.2, 55, 'female')

        canonical_result = unit_converter.calculate_egfr(1.2, 55, 'female')
        assert facade_result == canonical_result

    def test_get_score_from_table_matches_classifier(self):
        from services import fhir_data_service
        from services.risk_classifier import risk_classifier

        table = [
            {'age_range': [30, 50], 'base_score': 3},
            {'age_range': [51, 70], 'base_score': 5},
        ]

        for value in [40, 60, 80]:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                facade_result = fhir_data_service.get_score_from_table(value, table, 'age_range')

            canonical_result = risk_classifier.get_score_from_table(value, table, 'age_range')
            assert facade_result == canonical_result, f"Mismatch at value={value}"

    def test_check_arc_hbr_factors_matches_checker(self):
        from services import fhir_data_service
        from services.condition_checker import condition_checker

        raw = {'conditions': [], 'med_requests': []}

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            facade_result = fhir_data_service.check_arc_hbr_factors(raw, [])

        canonical_result = condition_checker.check_arc_hbr_factors_summary(raw, [])
        assert facade_result == canonical_result

    def test_get_active_medications_matches_checker(self):
        from services import fhir_data_service
        from services.condition_checker import condition_checker

        raw = {
            'med_requests': [
                {'status': 'active', 'medicationCodeableConcept': {'text': 'Aspirin'}},
                {'status': 'stopped', 'medicationCodeableConcept': {'text': 'Old drug'}},
            ]
        }

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            facade_result = fhir_data_service.get_active_medications(raw)

        canonical_result = condition_checker.get_active_medications(raw)
        assert facade_result == canonical_result
        assert len(facade_result) == 1
