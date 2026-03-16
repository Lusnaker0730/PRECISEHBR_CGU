"""
Golden Dataset CSV 驗證測試
驗證 PRECISE-HBR 計算器對手工定義的黃金數據集（precisehbr-golden.csv）的正確性。

測試覆蓋：
1. 有效案例：分數、風險分類、1 年出血風險百分比
2. 無效輸入：超出臨床合理範圍的值應被截斷（不報錯，但截斷到邊界值）

IEC 62304 §5.5 — 軟體單元驗證
"""
import csv
import math
import os
import sys
import logging

import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.precise_hbr_calculator import PreciseHBRCalculator
from services.risk_classifier import RiskClassifierService
from services.condition_checker import condition_checker

logging.basicConfig(level=logging.ERROR)

# ==========================================
# Load golden dataset from CSV
# ==========================================

GOLDEN_CSV = os.path.join(os.path.dirname(__file__), '..', 'precisehbr-golden.csv')


def _load_golden_cases():
    """Parse the golden CSV into valid and invalid case lists."""
    valid_cases = []
    invalid_cases = []

    with open(GOLDEN_CSV, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            age = float(row['Age'])
            hb = float(row['Hb(g/dl)'])
            wbc = float(row['WBC(10^3/uL)'])
            egfr = float(row['eGFR(ml/min/1.73m2)'])
            prior_bleeding = int(row['piorbleed'])
            oac = int(row['OAC'])
            arc_hbr = int(row['ARC-HBR'])
            score_str = row['score'].strip()
            risk_str = row['risk'].strip()
            risk_pct_str = row['1-year-risk'].strip()
            note = row.get('output', '').strip()

            case = {
                'age': age,
                'hb': hb,
                'wbc': wbc,
                'egfr': egfr,
                'prior_bleeding': bool(prior_bleeding),
                'oac': bool(oac),
                'arc_hbr': bool(arc_hbr),
                'note': note,
            }

            if score_str:
                # Valid case with expected outputs
                case['expected_score'] = int(score_str)
                case['expected_risk'] = risk_str
                case['expected_risk_pct'] = risk_pct_str
                valid_cases.append(case)
            else:
                # Invalid/boundary case — no expected score
                invalid_cases.append(case)

    return valid_cases, invalid_cases


VALID_CASES, INVALID_CASES = _load_golden_cases()

# ==========================================
# Helper: build FHIR-like input for calculator
# ==========================================


def _build_calculator_input(case):
    """Convert a golden case dict into (raw_data, demographics) for the calculator."""
    raw_data = {
        'HEMOGLOBIN': [{
            'valueQuantity': {'value': case['hb'], 'unit': 'g/dL'},
            'effectiveDateTime': '2025-01-01',
        }],
        'EGFR': [{
            'valueQuantity': {'value': case['egfr'], 'unit': 'mL/min/1.73m2'},
            'effectiveDateTime': '2025-01-01',
        }],
        'WBC': [{
            'valueQuantity': {'value': case['wbc'], 'unit': '10*9/L'},
            'effectiveDateTime': '2025-01-01',
        }],
        'conditions': [],
        'med_requests': [],
    }
    demographics = {'age': case['age'], 'gender': 'male'}
    return raw_data, demographics


def _run_calculator(case):
    """Run the calculator with mocked condition/medication flags and return (score, risk_info)."""
    raw_data, demographics = _build_calculator_input(case)

    arc_factors = {
        'has_any_factor': case['arc_hbr'],
        'thrombocytopenia': case['arc_hbr'],
        'bleeding_diathesis': False,
        'liver_cirrhosis': False,
        'active_malignancy': False,
        'nsaids_corticosteroids': False,
        'recent_major_surgery_trauma': False,
    }

    with patch.object(condition_checker, 'check_prior_bleeding',
                      return_value=(case['prior_bleeding'], ['golden-dataset'])):
        with patch.object(condition_checker, 'check_oral_anticoagulation',
                          return_value=case['oac']):
            with patch.object(condition_checker, 'check_arc_hbr_factors_detailed',
                              return_value=arc_factors):
                components, score, warnings = PreciseHBRCalculator.calculate_score(
                    raw_data, demographics
                )

    risk_info = RiskClassifierService.get_precise_hbr_display_info(score)
    return score, risk_info


# ==========================================
# Risk category mapping (CSV text → code text)
# ==========================================

RISK_CATEGORY_MAP = {
    'not high bleeding risk': 'Not high bleeding risk',
    'high bleeding risk': 'HBR',
    'very high bleeding risk': 'Very HBR',
}


# ==========================================
# Tests: Valid cases — score verification
# ==========================================


def _case_id(case):
    return (f"Age{int(case['age'])}_Hb{case['hb']}_eGFR{int(case['egfr'])}"
            f"_WBC{case['wbc']}_BL{int(case.get('prior_bleeding', 0))}"
            f"_OAC{int(case.get('oac', 0))}_ARC{int(case.get('arc_hbr', 0))}")


@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
@pytest.mark.parametrize("case", VALID_CASES, ids=[_case_id(c) for c in VALID_CASES])
def test_golden_score(case):
    """Golden dataset: 計算分數必須與預期值完全一致"""
    score, _ = _run_calculator(case)
    assert score == case['expected_score'], (
        f"Score mismatch: got {score}, expected {case['expected_score']} "
        f"(Age={case['age']}, Hb={case['hb']}, eGFR={case['egfr']}, "
        f"WBC={case['wbc']}, BL={case['prior_bleeding']}, "
        f"OAC={case['oac']}, ARC={case['arc_hbr']})"
    )


# ==========================================
# Tests: Valid cases — risk category verification
# ==========================================


@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
@pytest.mark.parametrize("case", VALID_CASES, ids=[_case_id(c) for c in VALID_CASES])
def test_golden_risk_category(case):
    """Golden dataset: 風險分類必須正確"""
    _, risk_info = _run_calculator(case)
    expected_category = RISK_CATEGORY_MAP[case['expected_risk']]
    assert risk_info['risk_category'] == expected_category, (
        f"Risk category mismatch: got '{risk_info['risk_category']}', "
        f"expected '{expected_category}' (score={risk_info['score']})"
    )


# ==========================================
# Tests: Valid cases — 1-year bleeding risk %
# ==========================================


@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
@pytest.mark.parametrize("case", VALID_CASES, ids=[_case_id(c) for c in VALID_CASES])
def test_golden_bleeding_risk_percent(case):
    """Golden dataset: 1 年出血風險百分比必須與預期值一致（容差 ±0.05%）"""
    _, risk_info = _run_calculator(case)
    actual_pct = float(risk_info['bleeding_risk_percent'].rstrip('%'))
    expected_pct = float(case['expected_risk_pct'].rstrip('%'))
    assert abs(actual_pct - expected_pct) < 0.05, (
        f"Bleeding risk % mismatch: got {actual_pct}%, expected {expected_pct}% "
        f"(score={risk_info['score']})"
    )


# ==========================================
# Tests: Invalid input cases — truncation
# ==========================================


@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
@pytest.mark.parametrize("case", INVALID_CASES, ids=[_case_id(c) for c in INVALID_CASES])
def test_golden_invalid_input_does_not_crash(case):
    """Golden dataset: 超出範圍的輸入應被截斷處理，不應拋出例外"""
    # Calculator should handle out-of-range inputs via truncation, not crash
    score, risk_info = _run_calculator(case)
    assert isinstance(score, int), f"Score should be int, got {type(score)}"
    assert score >= 2, f"Score should be at least base score (2), got {score}"
    assert risk_info['risk_category'] in ('Not high bleeding risk', 'HBR', 'Very HBR'), (
        f"Unexpected risk category: {risk_info['risk_category']}"
    )


# ==========================================
# Tests: Boundary cases (score 22, 26, 27)
# ==========================================


@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
def test_boundary_score_22_is_non_hbr():
    """邊界測試：score=22 應分類為 Not high bleeding risk"""
    info = RiskClassifierService.get_risk_category_info(22)
    assert info['category'] == 'Not high bleeding risk'


@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
def test_boundary_score_23_is_hbr():
    """邊界測試：score=23 應分類為 HBR"""
    info = RiskClassifierService.get_risk_category_info(23)
    assert info['category'] == 'HBR'


@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
def test_boundary_score_26_is_hbr():
    """邊界測試：score=26 應分類為 HBR"""
    info = RiskClassifierService.get_risk_category_info(26)
    assert info['category'] == 'HBR'


@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
def test_boundary_score_27_is_very_hbr():
    """邊界測試：score=27 應分類為 Very HBR"""
    info = RiskClassifierService.get_risk_category_info(27)
    assert info['category'] == 'Very HBR'
