"""
FHIR Normalizer and Canonical Model Tests

Verifies:
1. FHIRNormalizer correctly parses FHIR R4 resources into canonical dataclasses
2. NormalizedPatientData → calculator produces identical scores to legacy path
3. Normalized condition/medication checker produces consistent results

IEC 62304 §5.5 — Software Unit Verification
ISO 14971 — Risk Control: RISK-001 (Score Calculation Integrity)
"""

from __future__ import annotations

import pytest
from services.fhir_normalizer import (
    CodeEntry,
    FHIRNormalizer,
    NormalizedCondition,
    NormalizedDemographics,
    NormalizedLabValue,
    NormalizedMedication,
    NormalizedPatientData,
    fhir_normalizer,
)
from services.precise_hbr_calculator import precise_hbr_calculator
from services.condition_checker import condition_checker
from services.unit_conversion_service import UnitConversionService


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def sample_patient():
    return {
        'resourceType': 'Patient',
        'id': 'test-001',
        'name': [{'given': ['Ming'], 'family': 'Wang', 'text': '王明'}],
        'gender': 'male',
        'birthDate': '1960-01-15',
    }


@pytest.fixture
def sample_raw_data(sample_patient):
    """A realistic raw_data dict matching get_all_patient_data output."""
    return {
        'patient': sample_patient,
        'HEMOGLOBIN': [{
            'resourceType': 'Observation',
            'valueQuantity': {'value': 11.5, 'unit': 'g/dL'},
            'effectiveDateTime': '2026-01-10T08:00:00Z',
        }],
        'CREATININE': [{
            'resourceType': 'Observation',
            'valueQuantity': {'value': 1.8, 'unit': 'mg/dL'},
            'effectiveDateTime': '2026-01-10T08:00:00Z',
        }],
        'EGFR': [],
        'WBC': [{
            'resourceType': 'Observation',
            'valueQuantity': {'value': 8.5, 'unit': '10*9/L'},
            'effectiveDateTime': '2026-01-10T08:00:00Z',
        }],
        'PLATELETS': [{
            'resourceType': 'Observation',
            'valueQuantity': {'value': 180, 'unit': '10*9/L'},
            'effectiveDateTime': '2026-01-10T08:00:00Z',
        }],
        'conditions': [
            {
                'resourceType': 'Condition',
                'code': {
                    'coding': [{'system': 'http://hl7.org/fhir/sid/icd-10-cm', 'code': 'I25.10', 'display': 'Coronary artery disease'}],
                    'text': 'Coronary artery disease',
                },
                'clinicalStatus': {
                    'coding': [{'system': 'http://terminology.hl7.org/CodeSystem/condition-clinical', 'code': 'active'}],
                },
            },
        ],
        'med_requests': [
            {
                'resourceType': 'MedicationRequest',
                'status': 'active',
                'medicationCodeableConcept': {
                    'coding': [{'system': 'http://www.nlm.nih.gov/research/umls/rxnorm', 'code': '1191', 'display': 'Aspirin'}],
                    'text': 'Aspirin 100mg',
                },
            },
        ],
    }


# =========================================================================
# NormalizedLabValue
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestNormalizeLabValues:

    def test_hemoglobin_direct_unit(self):
        obs_list = [{'valueQuantity': {'value': 12.5, 'unit': 'g/dL'}, 'effectiveDateTime': '2026-01-01'}]
        from services.unit_conversion_service import unit_converter
        lab = FHIRNormalizer._normalize_lab('hemoglobin', obs_list, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert lab is not None
        assert lab.value == 12.5
        assert lab.status == UnitConversionService.STATUS_OK

    def test_hemoglobin_unit_conversion(self):
        obs_list = [{'valueQuantity': {'value': 125, 'unit': 'g/L'}}]
        from services.unit_conversion_service import unit_converter
        lab = FHIRNormalizer._normalize_lab('hemoglobin', obs_list, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert lab is not None
        assert abs(lab.value - 12.5) < 0.01

    def test_hemoglobin_unknown_unit(self):
        obs_list = [{'valueQuantity': {'value': 12.5, 'unit': 'mg/banana'}}]
        from services.unit_conversion_service import unit_converter
        lab = FHIRNormalizer._normalize_lab('hemoglobin', obs_list, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert lab is not None
        assert lab.value is None
        assert lab.status == UnitConversionService.STATUS_UNKNOWN_UNIT

    def test_hemoglobin_missing_unit(self):
        obs_list = [{'valueQuantity': {'value': 12.5}}]
        from services.unit_conversion_service import unit_converter
        lab = FHIRNormalizer._normalize_lab('hemoglobin', obs_list, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert lab is not None
        assert lab.value is None
        assert lab.status == UnitConversionService.STATUS_MISSING_UNIT

    def test_empty_obs_list(self):
        from services.unit_conversion_service import unit_converter
        lab = FHIRNormalizer._normalize_lab('hemoglobin', [], unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        assert lab is None


# =========================================================================
# eGFR with creatinine fallback
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestNormalizeEGFR:

    def test_direct_egfr(self):
        egfr_list = [{'valueQuantity': {'value': 85, 'unit': 'mL/min/1.73m2'}}]
        demo = NormalizedDemographics(age=65, gender='male')
        lab = FHIRNormalizer._normalize_egfr(egfr_list, [], demo)
        assert lab is not None
        assert lab.value == 85
        assert lab.source == 'Direct eGFR'

    def test_creatinine_fallback(self):
        cr_list = [{'valueQuantity': {'value': 1.2, 'unit': 'mg/dL'}}]
        demo = NormalizedDemographics(age=65, gender='male')
        lab = FHIRNormalizer._normalize_egfr([], cr_list, demo)
        assert lab is not None
        assert lab.value is not None
        assert 'CKD-EPI' in (lab.source or '')

    def test_no_egfr_no_creatinine(self):
        demo = NormalizedDemographics(age=65, gender='male')
        lab = FHIRNormalizer._normalize_egfr([], [], demo)
        assert lab is None

    def test_creatinine_fallback_needs_demographics(self):
        cr_list = [{'valueQuantity': {'value': 1.2, 'unit': 'mg/dL'}}]
        demo = NormalizedDemographics(age=None, gender=None)  # Missing
        lab = FHIRNormalizer._normalize_egfr([], cr_list, demo)
        assert lab is None


# =========================================================================
# Conditions
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestNormalizeConditions:

    def test_condition_with_icd10(self):
        condition = {
            'code': {
                'coding': [
                    {'system': 'http://hl7.org/fhir/sid/icd-10-cm', 'code': 'K74.6', 'display': 'Cirrhosis'},
                ],
                'text': 'Liver cirrhosis',
            },
            'clinicalStatus': {
                'coding': [{'system': 'http://terminology.hl7.org/CodeSystem/condition-clinical', 'code': 'active'}],
            },
        }
        nc = FHIRNormalizer._normalize_condition(condition)
        assert nc.icd10_code == 'K74.6'
        assert nc.clinical_status == 'active'
        assert 'cirrhosis' in nc.text

    def test_condition_text_lowercased(self):
        condition = {
            'code': {'coding': [{'system': 'test', 'code': '1', 'display': 'UPPER CASE'}], 'text': 'Mixed Case'},
        }
        nc = FHIRNormalizer._normalize_condition(condition)
        assert nc.text == 'mixed case upper case'

    def test_empty_condition(self):
        nc = FHIRNormalizer._normalize_condition({})
        assert nc.text == ''
        assert nc.codes == []
        assert nc.clinical_status == 'active'  # conservative default


# =========================================================================
# Medications
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestNormalizeMedications:

    def test_medication_with_rxnorm(self):
        med = {
            'medicationCodeableConcept': {
                'coding': [{'system': 'http://www.nlm.nih.gov/research/umls/rxnorm', 'code': '1191', 'display': 'Aspirin'}],
                'text': 'Aspirin 100mg',
            },
            'status': 'active',
        }
        nm = FHIRNormalizer._normalize_medication(med)
        assert '1191' in nm.rxnorm_codes
        assert 'aspirin' in nm.text
        assert nm.status == 'active'

    def test_medication_text_lowercased(self):
        med = {'medicationCodeableConcept': {'text': 'WARFARIN 5MG', 'coding': []}}
        nm = FHIRNormalizer._normalize_medication(med)
        assert nm.text == 'warfarin 5mg'

    def test_empty_medication(self):
        nm = FHIRNormalizer._normalize_medication({})
        assert nm.text == ''
        assert nm.rxnorm_codes == []


# =========================================================================
# Full normalize()
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestFullNormalize:

    def test_normalize_produces_patient_data(self, sample_raw_data):
        pd = fhir_normalizer.normalize(sample_raw_data)
        assert isinstance(pd, NormalizedPatientData)
        assert pd.demographics.gender == 'male'
        assert pd.hemoglobin is not None
        assert pd.hemoglobin.value == 11.5
        assert pd.wbc is not None
        assert pd.platelets is not None
        assert len(pd.conditions) == 1
        assert len(pd.medications) == 1

    def test_normalize_empty_data(self):
        pd = fhir_normalizer.normalize({})
        assert pd.hemoglobin is None
        assert pd.egfr is None
        assert pd.conditions == []
        assert pd.medications == []


# =========================================================================
# Normalized condition checker methods
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestNormalizedConditionChecker:

    def test_prior_bleeding_keyword_match(self):
        cond = NormalizedCondition(
            text='history of gastrointestinal bleeding',
            clinical_status='active',
        )
        has_bleeding, evidence = condition_checker.check_prior_bleeding_normalized([cond])
        assert has_bleeding is True

    def test_prior_bleeding_no_match(self):
        cond = NormalizedCondition(text='hypertension', clinical_status='active')
        has_bleeding, evidence = condition_checker.check_prior_bleeding_normalized([cond])
        assert has_bleeding is False

    def test_oral_anticoag_keyword(self):
        med = NormalizedMedication(text='warfarin 5mg')
        assert condition_checker.check_oral_anticoagulation_normalized([med]) is True

    def test_oral_anticoag_no_match(self):
        med = NormalizedMedication(text='aspirin 100mg')
        assert condition_checker.check_oral_anticoagulation_normalized([med]) is False

    def test_thrombocytopenia_low_platelets(self):
        plt_lab = NormalizedLabValue(parameter='platelets', value=80, status='ok')
        assert condition_checker.check_thrombocytopenia_normalized(plt_lab, []) is True

    def test_thrombocytopenia_normal_platelets(self):
        plt_lab = NormalizedLabValue(parameter='platelets', value=200, status='ok')
        assert condition_checker.check_thrombocytopenia_normalized(plt_lab, []) is False


# =========================================================================
# Score Equivalence: Legacy vs Normalized path
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-001")
@pytest.mark.design("SDS-001")
class TestScoreEquivalence:
    """
    Critical Class C safety test: the normalized calculation path MUST
    produce identical scores to the legacy path for the same input data.
    """

    def _make_raw_data(self, hb=12.0, cr=1.2, egfr=None, wbc=8.0, plt=200,
                       conditions=None, meds=None, gender='male', age=65):
        patient = {
            'resourceType': 'Patient', 'id': 'equiv-test',
            'name': [{'given': ['Test'], 'family': 'Patient'}],
            'gender': gender, 'birthDate': f'{2026-age}-01-01',
        }
        raw = {
            'patient': patient,
            'HEMOGLOBIN': [{'valueQuantity': {'value': hb, 'unit': 'g/dL'}}] if hb else [],
            'CREATININE': [{'valueQuantity': {'value': cr, 'unit': 'mg/dL'}}] if cr else [],
            'EGFR': [{'valueQuantity': {'value': egfr, 'unit': 'mL/min/1.73m2'}}] if egfr else [],
            'WBC': [{'valueQuantity': {'value': wbc, 'unit': '10*9/L'}}] if wbc else [],
            'PLATELETS': [{'valueQuantity': {'value': plt, 'unit': '10*9/L'}}] if plt else [],
            'conditions': conditions or [],
            'med_requests': meds or [],
        }
        return raw, {'name': 'Test Patient', 'age': age, 'gender': gender, 'birthDate': f'{2026-age}-01-01'}

    def test_basic_equivalence(self):
        raw, demo = self._make_raw_data()
        # Legacy path
        _, legacy_score, _ = precise_hbr_calculator.calculate_score(raw, demo)
        # Normalized path
        pd = fhir_normalizer.normalize(raw, demo)
        _, norm_score, _ = precise_hbr_calculator.calculate_score_normalized(pd)
        assert legacy_score == norm_score

    def test_equivalence_with_missing_data(self):
        raw, demo = self._make_raw_data(hb=None, wbc=None)
        _, legacy_score, _ = precise_hbr_calculator.calculate_score(raw, demo)
        pd = fhir_normalizer.normalize(raw, demo)
        _, norm_score, _ = precise_hbr_calculator.calculate_score_normalized(pd)
        assert legacy_score == norm_score

    def test_equivalence_with_creatinine_fallback(self):
        raw, demo = self._make_raw_data(cr=1.8, egfr=None)
        _, legacy_score, _ = precise_hbr_calculator.calculate_score(raw, demo)
        pd = fhir_normalizer.normalize(raw, demo)
        _, norm_score, _ = precise_hbr_calculator.calculate_score_normalized(pd)
        assert legacy_score == norm_score

    def test_equivalence_with_conditions(self):
        conditions = [{
            'code': {
                'coding': [{'system': 'http://snomed.info/sct', 'code': '74474003', 'display': 'GI hemorrhage'}],
                'text': 'gastrointestinal hemorrhage',
            },
        }]
        raw, demo = self._make_raw_data(conditions=conditions)
        _, legacy_score, _ = precise_hbr_calculator.calculate_score(raw, demo)
        pd = fhir_normalizer.normalize(raw, demo)
        _, norm_score, _ = precise_hbr_calculator.calculate_score_normalized(pd)
        assert legacy_score == norm_score

    def test_equivalence_with_anticoag(self):
        meds = [{
            'medicationCodeableConcept': {
                'text': 'Warfarin 5mg',
                'coding': [],
            },
            'status': 'active',
        }]
        raw, demo = self._make_raw_data(meds=meds)
        _, legacy_score, _ = precise_hbr_calculator.calculate_score(raw, demo)
        pd = fhir_normalizer.normalize(raw, demo)
        _, norm_score, _ = precise_hbr_calculator.calculate_score_normalized(pd)
        assert legacy_score == norm_score

    def test_equivalence_all_missing(self):
        raw, demo = self._make_raw_data(hb=None, cr=None, egfr=None, wbc=None, plt=None)
        _, legacy_score, _ = precise_hbr_calculator.calculate_score(raw, demo)
        pd = fhir_normalizer.normalize(raw, demo)
        _, norm_score, _ = precise_hbr_calculator.calculate_score_normalized(pd)
        assert legacy_score == norm_score
