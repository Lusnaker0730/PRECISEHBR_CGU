"""
FHIR-to-Canonical Data Normalizer

Translates raw FHIR R4 resources into pure Python dataclasses that the
core calculation layer consumes.  ALL FHIR-specific parsing lives here;
nothing downstream (precise_hbr_calculator, condition_checker,
risk_classifier) should touch ``valueQuantity``, ``coding``, or any other
FHIR dict structure.

IEC 62304 §5.3 — Software Architecture Design
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from services.config_loader import config_loader
from services.twcore_adapter import twcore_adapter
from services.unit_conversion_service import UnitConversionService, unit_converter

logger = logging.getLogger(__name__)


# =========================================================================
# Canonical Data Model
# =========================================================================

@dataclass
class NormalizedLabValue:
    """A single lab result, already converted to canonical units."""
    parameter: str                # e.g. 'hemoglobin', 'egfr', 'wbc'
    value: float | None = None   # converted value in canonical unit
    raw_value: float | None = None
    unit: str | None = None      # canonical unit string (e.g. 'g/dL')
    source_unit: str | None = None
    effective_date: str | None = None
    status: str = UnitConversionService.STATUS_NO_DATA
    source: str | None = None    # e.g. 'Direct eGFR', 'CKD-EPI 2021'


@dataclass
class NormalizedDemographics:
    """Patient demographics, already parsed from FHIR Patient."""
    name: str = 'Unknown'
    name_chinese: str | None = None
    gender: str | None = None     # 'male' | 'female'
    age: int | None = None
    birth_date: str | None = None
    taiwan_id: str | None = None
    medical_record_number: str | None = None


@dataclass
class CodeEntry:
    """A single clinical code."""
    system: str
    code: str
    display: str = ''


@dataclass
class NormalizedCondition:
    """A patient condition, pre-parsed for code matching."""
    codes: list[CodeEntry] = field(default_factory=list)
    icd10_code: str | None = None
    icd10_display: str | None = None
    text: str = ''                # combined display text, lowercased
    clinical_status: str = 'active'


@dataclass
class NormalizedMedication:
    """A medication, pre-parsed for keyword/code matching."""
    text: str = ''                # combined text, lowercased
    nhi_code: str | None = None
    rxnorm_codes: list[str] = field(default_factory=list)
    status: str | None = None


@dataclass
class NormalizedPatientData:
    """Top-level container replacing the raw_data dict."""
    demographics: NormalizedDemographics = field(default_factory=NormalizedDemographics)
    hemoglobin: NormalizedLabValue | None = None
    egfr: NormalizedLabValue | None = None
    creatinine: NormalizedLabValue | None = None
    wbc: NormalizedLabValue | None = None
    platelets: NormalizedLabValue | None = None
    conditions: list[NormalizedCondition] = field(default_factory=list)
    medications: list[NormalizedMedication] = field(default_factory=list)
    security_summary: dict | None = None


# =========================================================================
# Normalizer
# =========================================================================

class FHIRNormalizer:
    """Converts raw FHIR R4 dicts → NormalizedPatientData."""

    # ---- Demographics ---------------------------------------------------

    @staticmethod
    def normalize_demographics(demographics_dict: dict | None) -> NormalizedDemographics:
        """
        Convert a demographics dict (from twcore_adapter or plain dict)
        into NormalizedDemographics.
        """
        if not demographics_dict:
            return NormalizedDemographics()
        return NormalizedDemographics(
            name=demographics_dict.get('name', 'Unknown'),
            name_chinese=demographics_dict.get('name_chinese'),
            gender=demographics_dict.get('gender'),
            age=demographics_dict.get('age'),
            birth_date=demographics_dict.get('birthDate'),
            taiwan_id=demographics_dict.get('taiwan_id'),
            medical_record_number=demographics_dict.get('medical_record_number'),
        )

    @classmethod
    def normalize_demographics_from_patient(cls, patient_resource: dict | None) -> NormalizedDemographics:
        """Parse a FHIR Patient resource → NormalizedDemographics."""
        if not patient_resource:
            return NormalizedDemographics()
        raw = twcore_adapter.get_patient_demographics(patient_resource)
        return cls.normalize_demographics(raw)

    # ---- Lab Values -----------------------------------------------------

    @staticmethod
    def _normalize_lab(
        parameter: str,
        obs_list: list,
        unit_system: dict,
    ) -> NormalizedLabValue | None:
        """Convert a list of FHIR Observations → single NormalizedLabValue (most recent)."""
        if not obs_list:
            return None

        obs = obs_list[0]
        result = unit_converter.get_value_with_status(obs, unit_system)

        return NormalizedLabValue(
            parameter=parameter,
            value=result['value'],
            raw_value=result['raw_value'],
            unit=unit_system.get('unit') if isinstance(unit_system, dict) else str(unit_system),
            source_unit=result['source_unit'],
            effective_date=obs.get('effectiveDateTime', None) if isinstance(obs, dict) else None,
            status=result['status'],
        )

    @classmethod
    def _normalize_egfr(
        cls,
        egfr_list: list,
        creatinine_list: list,
        demographics: NormalizedDemographics,
    ) -> NormalizedLabValue | None:
        """
        Normalize eGFR with creatinine fallback.

        Tries direct eGFR first; if unavailable, calculates from creatinine
        using CKD-EPI 2021.  The fallback logic lives here (not in the
        calculator) because it is data derivation, not scoring.
        """
        # Try direct eGFR
        egfr_lab = cls._normalize_lab('egfr', egfr_list, unit_converter.TARGET_UNITS['EGFR'])
        if egfr_lab and egfr_lab.value is not None:
            egfr_lab.source = 'Direct eGFR'
            return egfr_lab

        # Fallback: calculate from creatinine
        if creatinine_list and demographics.age is not None and demographics.gender:
            cr_lab = cls._normalize_lab('creatinine', creatinine_list, unit_converter.TARGET_UNITS['CREATININE'])
            if cr_lab and cr_lab.value is not None:
                calc_egfr, reason = unit_converter.calculate_egfr(
                    cr_lab.value, demographics.age, demographics.gender,
                )
                if calc_egfr:
                    return NormalizedLabValue(
                        parameter='egfr',
                        value=calc_egfr,
                        raw_value=calc_egfr,
                        unit='mL/min/1.73m2',
                        source_unit=None,
                        effective_date=cr_lab.effective_date,
                        status=UnitConversionService.STATUS_OK,
                        source=reason,
                    )
            # Creatinine has unit issue — propagate it
            if cr_lab and cr_lab.status in (
                UnitConversionService.STATUS_UNKNOWN_UNIT,
                UnitConversionService.STATUS_MISSING_UNIT,
            ):
                return NormalizedLabValue(
                    parameter='egfr',
                    value=None,
                    raw_value=cr_lab.raw_value,
                    unit='mL/min/1.73m2',
                    source_unit=cr_lab.source_unit,
                    effective_date=cr_lab.effective_date,
                    status=cr_lab.status,
                    source='Creatinine (for eGFR calculation)',
                )

        # Propagate eGFR unit issue if we had one
        if egfr_lab and egfr_lab.status in (
            UnitConversionService.STATUS_UNKNOWN_UNIT,
            UnitConversionService.STATUS_MISSING_UNIT,
        ):
            return egfr_lab

        return None

    # ---- Conditions -----------------------------------------------------

    @staticmethod
    def _normalize_condition(condition: dict) -> NormalizedCondition:
        """Parse a single FHIR Condition resource → NormalizedCondition."""
        code_element = condition.get('code', {})

        # Extract all codes
        codes = []
        for coding in code_element.get('coding', []):
            codes.append(CodeEntry(
                system=coding.get('system', ''),
                code=coding.get('code', ''),
                display=coding.get('display', ''),
            ))

        # Combined text
        text_parts = []
        if code_element.get('text'):
            text_parts.append(code_element['text'])
        for c in codes:
            if c.display:
                text_parts.append(c.display)
        text = ' '.join(text_parts).lower()

        # ICD-10
        diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
        icd10_code = diagnosis_info.get('icd10_code') if diagnosis_info.get('has_icd10') else None
        icd10_display = diagnosis_info.get('icd10_display') if icd10_code else None

        # Clinical status
        clinical_status_raw = condition.get('clinicalStatus', {})
        clinical_status = 'active'
        if isinstance(clinical_status_raw, str):
            clinical_status = clinical_status_raw.lower()
        elif isinstance(clinical_status_raw, dict):
            status_system = (
                config_loader.get_fhir_system('condition_clinical')
                or 'http://terminology.hl7.org/CodeSystem/condition-clinical'
            )
            for coding in clinical_status_raw.get('coding', []):
                if coding.get('system') == status_system:
                    clinical_status = coding.get('code', 'active')
                    break

        return NormalizedCondition(
            codes=codes,
            icd10_code=icd10_code,
            icd10_display=icd10_display,
            text=text,
            clinical_status=clinical_status,
        )

    # ---- Medications ----------------------------------------------------

    @staticmethod
    def _normalize_medication(med: dict) -> NormalizedMedication:
        """Parse a single FHIR MedicationRequest → NormalizedMedication."""
        med_concept = med.get('medicationCodeableConcept', {})

        # Text
        texts = []
        if med_concept.get('text'):
            texts.append(med_concept['text'])
        for coding in med_concept.get('coding', []):
            if coding.get('display'):
                texts.append(coding['display'])
        # Contained medications
        for contained in med.get('contained', []):
            if contained.get('resourceType') == 'Medication':
                code_el = contained.get('code', {})
                if code_el.get('text'):
                    texts.append(code_el['text'])
                for coding in code_el.get('coding', []):
                    if coding.get('display'):
                        texts.append(coding['display'])

        # RxNorm codes
        rxnorm_codes = []
        for coding in med_concept.get('coding', []):
            if coding.get('system') == 'http://www.nlm.nih.gov/research/umls/rxnorm':
                rxnorm_codes.append(coding.get('code', ''))

        # NHI code
        nhi_info = twcore_adapter.extract_nhi_medication_code(med)
        nhi_code = nhi_info.get('nhi_code') if nhi_info.get('has_nhi_code') else None

        return NormalizedMedication(
            text=' '.join(texts).lower(),
            nhi_code=nhi_code,
            rxnorm_codes=rxnorm_codes,
            status=med.get('status'),
        )

    # ---- Top-Level Normalize --------------------------------------------

    @classmethod
    def normalize(cls, raw_data: dict, demographics_dict: dict | None = None) -> NormalizedPatientData:
        """
        Convert the raw_data dict (from fhir_client_service.get_all_patient_data
        or manually assembled from CDS Hooks prefetch) into NormalizedPatientData.

        Args:
            raw_data: dict with keys like 'HEMOGLOBIN', 'conditions', 'med_requests', etc.
            demographics_dict: pre-extracted demographics dict (if None, extracted from raw_data['patient'])
        """
        # Demographics
        if demographics_dict:
            demographics = cls.normalize_demographics(demographics_dict)
        else:
            demographics = cls.normalize_demographics_from_patient(raw_data.get('patient'))

        # Lab values
        hb = cls._normalize_lab('hemoglobin', raw_data.get('HEMOGLOBIN', []), unit_converter.TARGET_UNITS['HEMOGLOBIN'])
        wbc = cls._normalize_lab('wbc', raw_data.get('WBC', []), unit_converter.TARGET_UNITS['WBC'])
        platelets = cls._normalize_lab('platelets', raw_data.get('PLATELETS', []), unit_converter.TARGET_UNITS['PLATELETS'])
        creatinine = cls._normalize_lab('creatinine', raw_data.get('CREATININE', []), unit_converter.TARGET_UNITS['CREATININE'])
        egfr = cls._normalize_egfr(raw_data.get('EGFR', []), raw_data.get('CREATININE', []), demographics)

        # Conditions
        conditions = [cls._normalize_condition(c) for c in raw_data.get('conditions', [])]

        # Medications
        medications = [cls._normalize_medication(m) for m in raw_data.get('med_requests', [])]

        return NormalizedPatientData(
            demographics=demographics,
            hemoglobin=hb,
            egfr=egfr,
            creatinine=creatinine,
            wbc=wbc,
            platelets=platelets,
            conditions=conditions,
            medications=medications,
            security_summary=raw_data.get('_security_summary'),
        )


# Global singleton
fhir_normalizer = FHIRNormalizer()
