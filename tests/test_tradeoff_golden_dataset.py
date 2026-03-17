"""
ARC-HBR Tradeoff Model Golden Dataset Verification
Validates bleeding and thrombotic risk calculations against 25 cases
verified with the official ARC-HBR app.

IEC 62304 §5.5 — Software Unit Verification
"""
import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.tradeoff_model_calculator import TradeoffModelCalculator

GOLDEN_CSV = os.path.join(os.path.dirname(__file__), '..', 'tradeoff-golden.csv')


def _load_cases():
    cases = []
    with open(GOLDEN_CSV, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            factors = {
                'age_ge_65': bool(int(row['age_ge_65'])),
                'liver_cancer_surgery': bool(int(row['liver_cancer_surgery'])),
                'copd': bool(int(row['copd'])),
                'smoker': bool(int(row['smoker'])),
                'hemoglobin_11_12.9': bool(int(row['hb_11_12.9'])),
                'hemoglobin_lt_11': bool(int(row['hb_lt_11'])),
                'egfr_30_59': bool(int(row['egfr_30_59'])),
                'egfr_lt_30': bool(int(row['egfr_lt_30'])),
                'complex_pci': bool(int(row['complex_pci'])),
                'oac_discharge': bool(int(row['oac_discharge'])),
                'diabetes': bool(int(row['diabetes'])),
                'prior_mi': bool(int(row['prior_mi'])),
                'nstemi_stemi': bool(int(row['nstemi_stemi'])),
                'bms': bool(int(row['bms'])),
            }
            cases.append({
                'case_id': row['case_id'],
                'description': row['description'],
                'factors': factors,
                'expected_bleeding': float(row['expected_bleeding_pct']),
                'expected_thrombotic': float(row['expected_mi_st_pct']),
            })
    return cases


GOLDEN_CASES = _load_cases()


@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c['case_id'] for c in GOLDEN_CASES])
def test_tradeoff_bleeding_risk(case):
    """Golden dataset: bleeding risk must match official ARC-HBR app (tolerance <0.1%)"""
    model = TradeoffModelCalculator.load_tradeoff_model()
    assert model is not None, "Failed to load tradeoff model"

    result = TradeoffModelCalculator.calculate_tradeoff_scores_interactive(model, case['factors'])
    actual = result['bleeding_score']
    expected = case['expected_bleeding']
    assert abs(actual - expected) < 0.1, (
        f"{case['case_id']} ({case['description']}): "
        f"bleeding got {actual}%, expected {expected}% (diff {abs(actual - expected):.3f}%)"
    )


@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c['case_id'] for c in GOLDEN_CASES])
def test_tradeoff_thrombotic_risk(case):
    """Golden dataset: thrombotic risk must match official ARC-HBR app (tolerance <0.1%)"""
    model = TradeoffModelCalculator.load_tradeoff_model()
    assert model is not None, "Failed to load tradeoff model"

    result = TradeoffModelCalculator.calculate_tradeoff_scores_interactive(model, case['factors'])
    actual = result['thrombotic_score']
    expected = case['expected_thrombotic']
    assert abs(actual - expected) < 0.1, (
        f"{case['case_id']} ({case['description']}): "
        f"thrombotic got {actual}%, expected {expected}% (diff {abs(actual - expected):.3f}%)"
    )
