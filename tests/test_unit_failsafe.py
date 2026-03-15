"""
Unit Conversion Fail-Safe Tests

Verifies that when EHR observations contain unrecognized or missing units,
the system refuses to guess and generates explicit warnings instead of
silently treating the value as "missing data".

IEC 62304 §5.5 — Software Unit Verification
ISO 14971 — Risk Control: RISK-001 (Score Calculation Integrity)

Class C safety rationale: guessing units could cause a 10x magnitude error
(e.g., g/L vs g/dL for Hemoglobin), leading to incorrect risk classification.
"""

import pytest
from services.unit_conversion_service import UnitConversionService, unit_converter
from services.precise_hbr_calculator import PreciseHBRCalculator


def _make_demographics(age=65, gender='male'):
    return {'age': age, 'gender': gender, 'name': 'Test'}


def _make_raw_data(**overrides):
    """Build minimal raw_data dict. Pass FHIR observation lists directly."""
    data = {
        'conditions': [],
        'med_requests': [],
        'HEMOGLOBIN': [],
        'EGFR': [],
        'WBC': [],
        'CREATININE': [],
    }
    data.update(overrides)
    return data


# =========================================================================
# UnitConversionService.get_value_with_status — Status Differentiation
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestGetValueWithStatus:
    """Verify get_value_with_status returns correct status codes."""

    def test_ok_status_direct_match(self):
        """Known unit with direct match → STATUS_OK."""
        obs = {'valueQuantity': {'value': 12.0, 'unit': 'g/dL'}}
        result = unit_converter.get_value_with_status(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_OK
        assert result['value'] == 12.0

    def test_ok_status_after_conversion(self):
        """Known unit requiring conversion → STATUS_OK with converted value."""
        obs = {'valueQuantity': {'value': 120.0, 'unit': 'g/L'}}
        result = unit_converter.get_value_with_status(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_OK
        assert result['value'] == pytest.approx(12.0, abs=0.01)

    def test_unknown_unit_status(self):
        """Unrecognized unit → STATUS_UNKNOWN_UNIT, value=None, raw_value preserved."""
        obs = {'valueQuantity': {'value': 70.0, 'unit': 'mg/L'}}
        result = unit_converter.get_value_with_status(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_UNKNOWN_UNIT
        assert result['value'] is None
        assert result['raw_value'] == 70.0
        assert result['source_unit'] == 'mg/L'

    def test_missing_unit_status(self):
        """No unit field → STATUS_MISSING_UNIT, value=None, raw_value preserved."""
        obs = {'valueQuantity': {'value': 12.0}}
        result = unit_converter.get_value_with_status(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_MISSING_UNIT
        assert result['value'] is None
        assert result['raw_value'] == 12.0

    def test_empty_string_unit_is_missing(self):
        """Empty string unit → STATUS_MISSING_UNIT."""
        obs = {'valueQuantity': {'value': 12.0, 'unit': ''}}
        result = unit_converter.get_value_with_status(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_MISSING_UNIT
        assert result['value'] is None
        assert result['raw_value'] == 12.0

    def test_whitespace_only_unit_is_missing(self):
        """Whitespace-only unit → STATUS_MISSING_UNIT."""
        obs = {'valueQuantity': {'value': 12.0, 'unit': '   '}}
        result = unit_converter.get_value_with_status(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_MISSING_UNIT

    def test_no_data_status_none_obs(self):
        """None observation → STATUS_NO_DATA."""
        result = unit_converter.get_value_with_status(None, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_NO_DATA

    def test_no_data_status_empty_dict(self):
        """Empty dict → STATUS_NO_DATA."""
        result = unit_converter.get_value_with_status({}, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_NO_DATA

    def test_no_value_status(self):
        """valueQuantity present but no numeric value → STATUS_NO_VALUE."""
        obs = {'valueQuantity': {'unit': 'g/dL'}}
        result = unit_converter.get_value_with_status(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_NO_VALUE

    def test_backward_compat_get_value_from_observation(self):
        """get_value_from_observation still returns None for unknown unit."""
        obs = {'valueQuantity': {'value': 70.0, 'unit': 'mg/L'}}
        val = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert val is None

    def test_backward_compat_get_value_from_observation_ok(self):
        """get_value_from_observation still returns value for known unit."""
        obs = {'valueQuantity': {'value': 12.0, 'unit': 'g/dL'}}
        val = unit_converter.get_value_from_observation(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert val == 12.0


# =========================================================================
# Calculator — Unit Issue Tracking
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestUnitIssueTracking:
    """Verify extract_inputs tracks unit issues separately from missing data."""

    def test_unknown_hb_unit_tracked(self):
        """Hb with unknown unit → in both missing_fields AND unit_issues."""
        raw = _make_raw_data(HEMOGLOBIN=[{'valueQuantity': {'value': 70, 'unit': 'mg/L'}}])
        inputs = PreciseHBRCalculator.extract_inputs(raw, _make_demographics())
        assert 'Hemoglobin' in inputs['missing_fields']
        assert len(inputs['unit_issues']) == 1
        assert inputs['unit_issues'][0]['parameter'] == 'Hemoglobin'
        assert inputs['unit_issues'][0]['status'] == UnitConversionService.STATUS_UNKNOWN_UNIT
        assert inputs['unit_issues'][0]['raw_value'] == 70
        assert inputs['unit_issues'][0]['source_unit'] == 'mg/L'

    def test_missing_hb_unit_tracked(self):
        """Hb with no unit → in both missing_fields AND unit_issues."""
        raw = _make_raw_data(HEMOGLOBIN=[{'valueQuantity': {'value': 12.0}}])
        inputs = PreciseHBRCalculator.extract_inputs(raw, _make_demographics())
        assert 'Hemoglobin' in inputs['missing_fields']
        assert len(inputs['unit_issues']) >= 1
        hb_issue = [i for i in inputs['unit_issues'] if i['parameter'] == 'Hemoglobin'][0]
        assert hb_issue['status'] == UnitConversionService.STATUS_MISSING_UNIT

    def test_no_fhir_data_no_unit_issue(self):
        """Hb not present at all → missing_fields but NO unit_issues."""
        raw = _make_raw_data()
        inputs = PreciseHBRCalculator.extract_inputs(raw, _make_demographics())
        assert 'Hemoglobin' in inputs['missing_fields']
        hb_issues = [i for i in inputs['unit_issues'] if i['parameter'] == 'Hemoglobin']
        assert len(hb_issues) == 0

    def test_unknown_wbc_unit_tracked(self):
        """WBC with unknown unit → tracked."""
        raw = _make_raw_data(WBC=[{'valueQuantity': {'value': 8.5, 'unit': 'cells/uL'}}])
        inputs = PreciseHBRCalculator.extract_inputs(raw, _make_demographics())
        assert 'WBC' in inputs['missing_fields']
        wbc_issues = [i for i in inputs['unit_issues'] if i['parameter'] == 'WBC']
        assert len(wbc_issues) == 1

    def test_unknown_egfr_unit_tracked(self):
        """eGFR with unknown unit → tracked (if creatinine fallback also fails)."""
        raw = _make_raw_data(EGFR=[{'valueQuantity': {'value': 60, 'unit': 'weird/unit'}}])
        inputs = PreciseHBRCalculator.extract_inputs(raw, _make_demographics())
        assert 'eGFR' in inputs['missing_fields']
        egfr_issues = [i for i in inputs['unit_issues'] if 'eGFR' in i['parameter']]
        assert len(egfr_issues) == 1

    def test_multiple_unknown_units_all_tracked(self):
        """Multiple unknown units → all tracked."""
        raw = _make_raw_data(
            HEMOGLOBIN=[{'valueQuantity': {'value': 70, 'unit': 'mg/L'}}],
            WBC=[{'valueQuantity': {'value': 8.5, 'unit': 'cells/uL'}}],
        )
        inputs = PreciseHBRCalculator.extract_inputs(raw, _make_demographics())
        assert len(inputs['unit_issues']) == 2


# =========================================================================
# Calculator — Warning Generation
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestUnitWarningGeneration:
    """Verify calculate_score generates unrecognized_unit warnings."""

    def test_unknown_unit_generates_warning(self):
        """Unknown Hb unit → unrecognized_unit warning in data_warnings."""
        raw = _make_raw_data(HEMOGLOBIN=[{'valueQuantity': {'value': 70, 'unit': 'mg/L'}}])
        components, score, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        unit_warnings = [w for w in warnings if w['type'] == 'unrecognized_unit']
        assert len(unit_warnings) == 1
        assert unit_warnings[0]['parameter'] == 'Hemoglobin'
        assert unit_warnings[0]['severity'] == 'high'
        assert unit_warnings[0]['raw_value'] == 70
        assert unit_warnings[0]['source_unit'] == 'mg/L'
        assert 'unrecognized unit' in unit_warnings[0]['message'].lower()

    def test_missing_unit_generates_warning(self):
        """Missing Hb unit → unrecognized_unit warning with missing_unit status."""
        raw = _make_raw_data(HEMOGLOBIN=[{'valueQuantity': {'value': 12.0}}])
        components, score, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        unit_warnings = [w for w in warnings if w['type'] == 'unrecognized_unit']
        assert len(unit_warnings) == 1
        assert unit_warnings[0]['status'] == UnitConversionService.STATUS_MISSING_UNIT
        assert 'without a unit' in unit_warnings[0]['message']

    def test_no_fhir_data_no_unit_warning(self):
        """No Hb data at all → no unrecognized_unit warning."""
        raw = _make_raw_data()
        components, score, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        unit_warnings = [w for w in warnings if w['type'] == 'unrecognized_unit']
        assert len(unit_warnings) == 0

    def test_known_unit_no_unit_warning(self):
        """Known Hb unit → no unrecognized_unit warning."""
        raw = _make_raw_data(HEMOGLOBIN=[{'valueQuantity': {'value': 12.0, 'unit': 'g/dL'}}])
        components, score, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        unit_warnings = [w for w in warnings if w['type'] == 'unrecognized_unit']
        assert len(unit_warnings) == 0

    def test_warning_message_includes_expected_unit(self):
        """Warning message mentions the expected canonical unit."""
        raw = _make_raw_data(HEMOGLOBIN=[{'valueQuantity': {'value': 70, 'unit': 'mg/L'}}])
        _, _, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        unit_warnings = [w for w in warnings if w['type'] == 'unrecognized_unit']
        assert 'g/dl' in unit_warnings[0]['message'].lower() or 'g/dL' in unit_warnings[0]['message']

    def test_warning_message_includes_verify(self):
        """Warning message asks clinician to verify."""
        raw = _make_raw_data(HEMOGLOBIN=[{'valueQuantity': {'value': 70, 'unit': 'mg/L'}}])
        _, _, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        unit_warnings = [w for w in warnings if w['type'] == 'unrecognized_unit']
        assert 'verify' in unit_warnings[0]['message'].lower()

    def test_hb_component_shows_not_available(self):
        """Unknown Hb unit → component shows 'Not available', NOT the raw value."""
        raw = _make_raw_data(HEMOGLOBIN=[{'valueQuantity': {'value': 70, 'unit': 'mg/L'}}])
        components, score, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        hb_comp = next(c for c in components if 'Hemoglobin' in c['parameter'])
        assert hb_comp['value'] == 'Not available'
        assert hb_comp['score'] == 0

    def test_unknown_unit_does_not_affect_score(self):
        """Unknown Hb unit → Hb does not contribute to score (excluded, not guessed)."""
        raw_good = _make_raw_data(HEMOGLOBIN=[{'valueQuantity': {'value': 7.0, 'unit': 'g/dL'}}])
        raw_bad = _make_raw_data(HEMOGLOBIN=[{'valueQuantity': {'value': 7.0, 'unit': 'mg/L'}}])
        _, score_good, _ = PreciseHBRCalculator.calculate_score(raw_good, _make_demographics())
        _, score_bad, _ = PreciseHBRCalculator.calculate_score(raw_bad, _make_demographics())
        # bad unit → Hb excluded → score should be LOWER (Hb contributes 0)
        assert score_bad < score_good


# =========================================================================
# Edge Cases
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestUnitEdgeCases:
    """Edge cases for unit handling."""

    def test_case_insensitive_unit_match(self):
        """Unit matching is case-insensitive: 'G/DL' should work."""
        obs = {'valueQuantity': {'value': 12.0, 'unit': 'G/DL'}}
        result = unit_converter.get_value_with_status(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_OK
        assert result['value'] == 12.0

    def test_unit_with_extra_whitespace(self):
        """Extra whitespace in unit should still match."""
        obs = {'valueQuantity': {'value': 12.0, 'unit': '  g/dL  '}}
        result = unit_converter.get_value_with_status(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_OK

    def test_none_unit_field(self):
        """Unit field explicitly set to None → STATUS_MISSING_UNIT."""
        obs = {'valueQuantity': {'value': 12.0, 'unit': None}}
        result = unit_converter.get_value_with_status(obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert result['status'] == UnitConversionService.STATUS_MISSING_UNIT

    def test_creatinine_unknown_unit_egfr_fallback_fails(self):
        """eGFR not available + Creatinine with unknown unit → unit issue tracked."""
        raw = _make_raw_data(
            CREATININE=[{'valueQuantity': {'value': 1.2, 'unit': 'weird'}}]
        )
        inputs = PreciseHBRCalculator.extract_inputs(raw, _make_demographics())
        assert 'eGFR' in inputs['missing_fields']
        cr_issues = [i for i in inputs['unit_issues'] if 'Creatinine' in i['parameter']]
        assert len(cr_issues) == 1

    def test_egfr_unknown_but_creatinine_ok_no_warning(self):
        """eGFR unknown unit but Creatinine fallback succeeds → no unit warning."""
        raw = _make_raw_data(
            EGFR=[{'valueQuantity': {'value': 60, 'unit': 'weird/unit'}}],
            CREATININE=[{'valueQuantity': {'value': 1.2, 'unit': 'mg/dL'}}],
        )
        inputs = PreciseHBRCalculator.extract_inputs(raw, _make_demographics())
        assert inputs['egfr'] is not None  # Creatinine fallback worked
        egfr_issues = [i for i in inputs['unit_issues'] if 'eGFR' in i['parameter']]
        assert len(egfr_issues) == 0
