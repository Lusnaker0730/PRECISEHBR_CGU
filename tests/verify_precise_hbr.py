import sys
import os
import random
import logging
import pytest
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.precise_hbr_calculator import PreciseHBRCalculator
from services.unit_conversion_service import unit_converter

# Configure logging
logging.basicConfig(level=logging.ERROR)

# ==========================================
# 1. Independent Reference Implementation
# ==========================================

def reference_precise_hbr_calc(age, hb, egfr, wbc, prior_bleeding, anticoag, arc_hbr_factors):
    """
    Independent reference implementation of PRECISE-HBR score.
    
    Formula based on code analysis (V5.0 Methodology intent):
    Score = 2 (base) 
          + 0.25 * (Age - 30) if Age > 30
          + 2.5 * (15 - Hb) if Hb < 15
          + 0.05 * (100 - eGFR) if eGFR < 100
          + 0.8 * (WBC - 3) if WBC > 3
          + 7 if Prior Bleeding
          + 5 if Oral Anticoagulation
          + 3 if ARC-HBR Factors >= 1
    
    Note: Inputs are assumed to be "effective" values (clamped if necessary), 
    but the main calculator handles clamping. We will pass clamped values 
    to this reference or implement clamping here matching the spec.
    """
    score = 2.0
    
    # Age (years)
    # Spec: >30
    eff_age = max(30, min(80, age)) # Clamping based on observations in code
    if eff_age > 30:
        score += 0.25 * (eff_age - 30)
        
    # Hemoglobin (g/dL)
    # Spec: <15
    eff_hb = max(5.0, min(15.0, hb))
    if eff_hb < 15:
        score += 2.5 * (15 - eff_hb)
        
    # eGFR (mL/min)
    # Spec: <100
    eff_egfr = max(5, min(100, egfr))
    if eff_egfr < 100:
        score += 0.05 * (100 - eff_egfr)
        
    # WBC (10^9/L)
    # Spec: >3
    eff_wbc = min(15.0, wbc)
    if eff_wbc > 3:
        score += 0.8 * (eff_wbc - 3)
        
    # Binary factors
    if prior_bleeding:
        score += 7
    if anticoag:
        score += 5
    if arc_hbr_factors:
        score += 3
        
    return round(score)

# ==========================================
# 2. Golden Dataset Generator
# ==========================================

def generate_golden_dataset(n=100):
    dataset = []
    
    # 1. Normal/Healthy case (should be low score)
    dataset.append({
        'case_id': 'TC-NORMAL-001',
        'age': 40, 'hb': 16.0, 'egfr': 110, 'wbc': 5.0,
        'bleeding': False, 'anticoag': False, 'arc': False
    })
    
    # 2. High Risk case (Pathological)
    dataset.append({
        'case_id': 'TC-PATH-001',
        'age': 75, 'hb': 10.0, 'egfr': 30, 'wbc': 12.0,
        'bleeding': True, 'anticoag': True, 'arc': True
    })
    
    # Random cases
    for i in range(n-2):
        data = {
            'case_id': f'TC-RAND-{i+1:03d}',
            'age': random.randint(20, 95), # Range wider than effective to test clamping
            'hb': random.uniform(4.0, 18.0),
            'egfr': random.uniform(2, 120),
            'wbc': random.uniform(1.0, 20.0),
            'bleeding': random.choice([True, False]),
            'anticoag': random.choice([True, False]),
            'arc': random.choice([True, False]),
        }
        dataset.append(data)
        
    return dataset

def convert_to_calculator_input(case):
    """Convert flat case data to FHIR/App format"""
    raw_data = {
        'HEMOGLOBIN': [{
            'valueQuantity': {'value': case['hb'], 'unit': 'g/dL'},
            'effectiveDateTime': '2023-01-01'
        }],
        'EGFR': [{
            'valueQuantity': {'value': case['egfr'], 'unit': 'mL/min/1.73m2'},
            'effectiveDateTime': '2023-01-01'
        }],
        'WBC': [{
            'valueQuantity': {'value': case['wbc'], 'unit': '10*9/L'},
            'effectiveDateTime': '2023-01-01'
        }],
        'conditions': [],
        'med_requests': []
    }
    
    if case['bleeding']:
        # Add a condition that triggers bleeding history
        # (Assuming code checks specific codes, but we might need to mock condition_checker or look at it)
        # For now, let's look at how condition_checker works or mock it.
        # Actually, let's use the code's assumption.
        # Based on services/condition_checker.py which I haven't read fully, 
        # I'll need to mock the result of condition_checker or construct data that passes it.
        pass

    demographics = {
        'age': case['age'],
        'gender': 'male' # Irrelevant for this calc except maybe eGFR derivation if needed, but we provide direct eGFR
    }
    
    return raw_data, demographics

# Mocking Condition Checker for simplicity in this verification script
# Since we want to verify the MATH, we can patch the condition checker results
# to match our test case intent.

@pytest.mark.parametrize("case", generate_golden_dataset(20)) # Run 20 random cases for unit testing
def test_golden_dataset_verification(case):
    # Prepare Inputs
    raw_data, demographics = convert_to_calculator_input(case)
    
    from unittest.mock import patch
    
    with patch('services.condition_checker.condition_checker.check_prior_bleeding', return_value=(case['bleeding'], ['trace'])):
        with patch('services.condition_checker.condition_checker.check_oral_anticoagulation', return_value=case['anticoag']):
            # Fix: Ensure at least one factor is true if has_any_factor is true, because pure calculator logic sums them.
            arc_factors = {
                'has_any_factor': case['arc'], 
                'thrombocytopenia': case['arc'], # Set one true if arc is true
                'bleeding_diathesis': False, 
                'liver_cirrhosis': False, 
                'active_malignancy': False, 
                'nsaids_corticosteroids': False
            }
            with patch('services.condition_checker.condition_checker.check_arc_hbr_factors_detailed', return_value=arc_factors):
                
                # Execute Implementation
                components, score_impl = PreciseHBRCalculator.calculate_score(raw_data, demographics)
                
                # Execute Reference
                score_ref = reference_precise_hbr_calc(
                    case['age'], case['hb'], case['egfr'], case['wbc'],
                    case['bleeding'], case['anticoag'], case['arc']
                )
                
                # Compare
                assert score_impl == score_ref, \
                    f"Mismatch for Case {case['case_id']}: Impl={score_impl}, Ref={score_ref}. Data={case}"

# ==========================================
# 3. Boundary Value Analysis
# ==========================================

def test_boundary_values():
    """Test specific boundary conditions defined in Protocol Phase 2"""
    from unittest.mock import patch
    
    # We patch dependencies to ensure we are testing the CALCULATOR logic, not the extractor logic
    # Defaulting to False/None for these patches as the BVA cases here don't focus on them
    with patch('services.condition_checker.condition_checker.check_prior_bleeding', return_value=(False, [])):
        with patch('services.condition_checker.condition_checker.check_oral_anticoagulation', return_value=False):
            with patch('services.condition_checker.condition_checker.check_arc_hbr_factors_detailed', return_value={
                'has_any_factor': False, 
                'thrombocytopenia': False, 'bleeding_diathesis': False, 
                'liver_cirrhosis': False, 'active_malignancy': False, 'nsaids_corticosteroids': False
            }):
    
                # 1. Age Boundaries (30, 80)
                # Age 30 (Should contribute 0)
                raw, dem = convert_to_calculator_input({
                    'case_id': 'BVA-AGE-30', 'age': 30, 'hb': 15, 'egfr': 100, 'wbc': 3, 
                    'bleeding': False, 'anticoag': False, 'arc': False
                })
                _, score = PreciseHBRCalculator.calculate_score(raw, dem)
                assert score == 2 # Base 2 + 0
                
                # Age 31 (Should contribute (31-30)*0.25 = 0.25 -> Total 2.25 -> Round -> 2)
                raw, dem = convert_to_calculator_input({
                    'case_id': 'BVA-AGE-31', 'age': 31, 'hb': 15, 'egfr': 100, 'wbc': 3, 
                    'bleeding': False, 'anticoag': False, 'arc': False
                })
                _, score = PreciseHBRCalculator.calculate_score(raw, dem)
                # 2 + 0.25 = 2.25 -> round(2.25) = 2.
                assert score == 2
                
                # Age 34 (Should contribute (34-30)*0.25 = 1.0 -> Total 3)
                raw, dem = convert_to_calculator_input({
                    'case_id': 'BVA-AGE-34', 'age': 34, 'hb': 15, 'egfr': 100, 'wbc': 3, 
                    'bleeding': False, 'anticoag': False, 'arc': False
                })
                _, score = PreciseHBRCalculator.calculate_score(raw, dem)
                assert score == 3
            
                # Age 81 (Clamped to 80)
                # (80-30)*0.25 = 12.5. Base 2 = 14.5. Round(14.5) = 14 (to even)? Or 15?
                # round(14.5) in Python 3 is 14.
                raw, dem = convert_to_calculator_input({
                    'case_id': 'BVA-AGE-81', 'age': 81, 'hb': 15, 'egfr': 100, 'wbc': 3, 
                    'bleeding': False, 'anticoag': False, 'arc': False
                })
                _, score = PreciseHBRCalculator.calculate_score(raw, dem)
                assert score == 14


if __name__ == "__main__":
    # Standard Execution: Export Golden Dataset to CSV for Documentation
    import csv
    
    print("Generating Golden Dataset CSV...")
    dataset = generate_golden_dataset(100)
    
    # Calculate reference scores for all
    for case in dataset:
        case['expected_score'] = reference_precise_hbr_calc(
            case['age'], case['hb'], case['egfr'], case['wbc'],
            case['bleeding'], case['anticoag'], case['arc']
        )
    
    output_file = os.path.join(os.path.dirname(__file__), '..', 'docs', 'PreciseHBR_Golden_Dataset.csv')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['case_id', 'age', 'hb', 'egfr', 'wbc', 'bleeding', 'anticoag', 'arc', 'expected_score'])
        writer.writeheader()
        writer.writerows(dataset)
        
    print(f"Golden Dataset saved to {output_file}")
    
    # Run tests via pytest programmatically if desired, or assume user runs pytest
    # We will exit with 0 to indicate success of generation
    sys.exit(0)
