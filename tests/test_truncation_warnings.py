"""
Data Quality Warning Tests — Truncation Detection

Verifies that when EHR-reported values fall outside clinically expected
ranges (due to unit errors, data entry mistakes, or extreme values),
the system generates explicit warnings instead of silently truncating.

IEC 62304 §5.5 — Software Unit Verification
ISO 14971 — Risk Control: RISK-001 (Score Calculation Integrity)
"""

import pytest
from services.precise_hbr_calculator import PreciseHBRCalculator


def _make_demographics(age=65, gender='male'):
    return {'age': age, 'gender': gender, 'name': 'Test'}


def _make_raw_data(hb=None, egfr=None, wbc=None, creatinine=None):
    """Build minimal raw_data dict with optional lab values."""
    data = {
        'conditions': [],
        'med_requests': [],
        'HEMOGLOBIN': [],
        'EGFR': [],
        'WBC': [],
        'CREATININE': [],
    }
    if hb is not None:
        data['HEMOGLOBIN'] = [{'valueQuantity': {'value': hb, 'unit': 'g/dL'}}]
    if egfr is not None:
        data['EGFR'] = [{'valueQuantity': {'value': egfr, 'unit': 'mL/min/1.73m2'}}]
    if wbc is not None:
        data['WBC'] = [{'valueQuantity': {'value': wbc, 'unit': '10*9/L'}}]
    return data


# =========================================================================
# Truncation Detection
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestTruncationWarnings:
    """Verify truncation warnings are generated for out-of-range values."""

    def test_normal_values_no_warnings(self):
        """Normal values within range should produce no truncation warnings."""
        raw = _make_raw_data(hb=12.0, egfr=60, wbc=8.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics()
        )
        truncation_warnings = [w for w in warnings if w['type'] == 'truncated_value']
        assert len(truncation_warnings) == 0

    def test_hb_above_max_generates_warning(self):
        """Hb=105 (likely g/L unit error) should warn, not silently cap."""
        raw = _make_raw_data(hb=105.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics()
        )
        trunc = [w for w in warnings if w['type'] == 'truncated_value' and w['parameter'] == 'Hemoglobin']
        assert len(trunc) == 1
        assert trunc[0]['raw_value'] == 105.0
        assert trunc[0]['effective_value'] == 15.0
        assert trunc[0]['direction'] == 'above'
        assert 'unit conversion error' in trunc[0]['message']

    def test_hb_below_min_generates_warning(self):
        """Hb=2.0 (extremely low) should warn."""
        raw = _make_raw_data(hb=2.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics()
        )
        trunc = [w for w in warnings if w['type'] == 'truncated_value' and w['parameter'] == 'Hemoglobin']
        assert len(trunc) == 1
        assert trunc[0]['direction'] == 'below'
        assert trunc[0]['effective_value'] == 5.0

    def test_egfr_above_max_generates_warning(self):
        """eGFR=150 should warn."""
        raw = _make_raw_data(egfr=150)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics()
        )
        trunc = [w for w in warnings if w['type'] == 'truncated_value' and w['parameter'] == 'eGFR']
        assert len(trunc) == 1
        assert trunc[0]['raw_value'] == 150
        assert trunc[0]['effective_value'] == 100

    def test_egfr_below_min_generates_warning(self):
        """eGFR=2 should warn."""
        raw = _make_raw_data(egfr=2)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics()
        )
        trunc = [w for w in warnings if w['type'] == 'truncated_value' and w['parameter'] == 'eGFR']
        assert len(trunc) == 1
        assert trunc[0]['effective_value'] == 5

    def test_wbc_above_max_generates_warning(self):
        """WBC=50 should warn."""
        raw = _make_raw_data(wbc=50.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics()
        )
        trunc = [w for w in warnings if w['type'] == 'truncated_value' and w['parameter'] == 'WBC']
        assert len(trunc) == 1
        assert trunc[0]['raw_value'] == 50.0
        assert trunc[0]['effective_value'] == 15.0

    def test_age_above_max_generates_warning(self):
        """Age=95 should warn."""
        raw = _make_raw_data(hb=12.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics(age=95)
        )
        trunc = [w for w in warnings if w['type'] == 'truncated_value' and w['parameter'] == 'Age']
        assert len(trunc) == 1
        assert trunc[0]['raw_value'] == 95
        assert trunc[0]['effective_value'] == 80

    def test_multiple_truncations_all_warned(self):
        """Multiple out-of-range values should each generate a warning."""
        raw = _make_raw_data(hb=105.0, egfr=150, wbc=50.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics(age=95)
        )
        trunc = [w for w in warnings if w['type'] == 'truncated_value']
        params = {w['parameter'] for w in trunc}
        assert params == {'Age', 'Hemoglobin', 'eGFR', 'WBC'}

    def test_boundary_values_no_warning(self):
        """Values exactly at boundary should NOT trigger warnings."""
        raw = _make_raw_data(hb=15.0, egfr=100, wbc=15.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics(age=80)
        )
        trunc = [w for w in warnings if w['type'] == 'truncated_value']
        assert len(trunc) == 0

    def test_boundary_min_values_no_warning(self):
        """Values exactly at min boundary should NOT trigger warnings."""
        raw = _make_raw_data(hb=5.0, egfr=5, wbc=3.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics(age=30)
        )
        trunc = [w for w in warnings if w['type'] == 'truncated_value']
        assert len(trunc) == 0


# =========================================================================
# Component Display
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestComponentDisplayTruncation:
    """Verify component 'value' field shows truncation info."""

    def test_hb_truncated_shows_capped(self):
        """Hb component value should show '(capped to X)' when truncated."""
        raw = _make_raw_data(hb=105.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics()
        )
        hb_comp = next(c for c in components if 'Hemoglobin' in c['parameter'])
        assert 'capped to' in hb_comp['value']
        assert hb_comp['is_truncated'] is True
        assert hb_comp['effective_value'] == 15.0

    def test_egfr_truncated_shows_capped(self):
        raw = _make_raw_data(egfr=2)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics()
        )
        egfr_comp = next(c for c in components if 'eGFR' in c['parameter'])
        assert 'capped to' in egfr_comp['value']
        assert egfr_comp['is_truncated'] is True

    def test_wbc_truncated_shows_capped(self):
        raw = _make_raw_data(wbc=50.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics()
        )
        wbc_comp = next(c for c in components if 'White Blood Cell' in c['parameter'])
        assert 'capped to' in wbc_comp['value']
        assert wbc_comp['is_truncated'] is True

    def test_age_truncated_shows_capped(self):
        raw = _make_raw_data(hb=12.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics(age=95)
        )
        age_comp = next(c for c in components if 'Age' in c['parameter'])
        assert 'capped to' in age_comp['value']
        assert age_comp['is_truncated'] is True

    def test_normal_hb_no_capped_label(self):
        raw = _make_raw_data(hb=12.0)
        components, score, warnings = PreciseHBRCalculator.calculate_score(
            raw, _make_demographics()
        )
        hb_comp = next(c for c in components if 'Hemoglobin' in c['parameter'])
        assert 'capped' not in hb_comp['value']
        assert hb_comp.get('is_truncated') is not True


# =========================================================================
# Warning Message Quality
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
class TestWarningMessageContent:
    """Verify warning messages contain actionable clinical information."""

    def test_warning_includes_raw_and_effective(self):
        raw = _make_raw_data(hb=105.0)
        _, _, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        trunc = [w for w in warnings if w['type'] == 'truncated_value'][0]
        assert '105' in trunc['message']
        assert '15' in trunc['message']

    def test_warning_includes_expected_range(self):
        raw = _make_raw_data(hb=105.0)
        _, _, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        trunc = [w for w in warnings if w['type'] == 'truncated_value'][0]
        assert '5' in trunc['message']  # min
        assert '15' in trunc['message']  # max

    def test_warning_suggests_verification(self):
        raw = _make_raw_data(hb=105.0)
        _, _, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        trunc = [w for w in warnings if w['type'] == 'truncated_value'][0]
        assert 'verify' in trunc['message'].lower()

    def test_warning_severity_is_high(self):
        raw = _make_raw_data(hb=105.0)
        _, _, warnings = PreciseHBRCalculator.calculate_score(raw, _make_demographics())
        trunc = [w for w in warnings if w['type'] == 'truncated_value'][0]
        assert trunc['severity'] == 'high'
