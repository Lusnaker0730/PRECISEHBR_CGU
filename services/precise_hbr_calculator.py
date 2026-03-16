"""
PRECISE-HBR Calculator Service
Calculates PRECISE-HBR bleeding risk score

All scoring coefficients and truncation limits are loaded from cdss_config.json for maintainability.
"""
import logging
import math
from datetime import datetime, timedelta

from services.condition_checker import condition_checker
from services.config_loader import config_loader
from services.fhir_normalizer import NormalizedPatientData, fhir_normalizer
from services.unit_conversion_service import UnitConversionService, unit_converter


class PreciseHBRCalculator:
    """Calculator for PRECISE-HBR bleeding risk score"""
    
    # Default truncation limits (used if config is missing)
    DEFAULT_MIN_AGE, DEFAULT_MAX_AGE = 30, 80
    DEFAULT_MIN_HB, DEFAULT_MAX_HB = 5.0, 15.0
    DEFAULT_MIN_EGFR, DEFAULT_MAX_EGFR = 5, 100
    DEFAULT_MIN_WBC, DEFAULT_MAX_WBC = 3.0, 15.0

    # Default scoring coefficients
    DEFAULT_BASE_SCORE = 2
    DEFAULT_AGE_THRESHOLD = 30
    DEFAULT_AGE_COEFFICIENT = 0.25
    DEFAULT_HB_THRESHOLD = 15.0
    DEFAULT_HB_COEFFICIENT = 2.5
    DEFAULT_EGFR_THRESHOLD = 100
    DEFAULT_EGFR_COEFFICIENT = 0.055
    DEFAULT_WBC_THRESHOLD = 3.0
    DEFAULT_WBC_COEFFICIENT = 0.8
    DEFAULT_BLEEDING_SCORE = 7
    DEFAULT_ANTICOAG_SCORE = 5
    DEFAULT_ARC_HBR_SCORE = 3

    @classmethod
    def _get_config_params(cls):
        """Get PRECISE-HBR parameters from config with fallback defaults."""
        params = config_loader.get_precise_hbr_params()
        return params if params else {}

    @classmethod
    def _get_truncation_limits(cls):
        """Get truncation limits from config."""
        params = cls._get_config_params()
        return {
            'min_age': params.get('age', {}).get('truncation_min', cls.DEFAULT_MIN_AGE),
            'max_age': params.get('age', {}).get('truncation_max', cls.DEFAULT_MAX_AGE),
            'min_hb': params.get('hemoglobin', {}).get('truncation_min', cls.DEFAULT_MIN_HB),
            'max_hb': params.get('hemoglobin', {}).get('truncation_max', cls.DEFAULT_MAX_HB),
            'min_egfr': params.get('egfr', {}).get('truncation_min', cls.DEFAULT_MIN_EGFR),
            'max_egfr': params.get('egfr', {}).get('truncation_max', cls.DEFAULT_MAX_EGFR),
            'min_wbc': params.get('white_blood_cell_count', {}).get('truncation_min', cls.DEFAULT_MIN_WBC),
            'max_wbc': params.get('white_blood_cell_count', {}).get('truncation_max', cls.DEFAULT_MAX_WBC),
        }

    @classmethod
    def _get_scoring_coefficients(cls):
        """Get scoring coefficients and thresholds from config."""
        params = cls._get_config_params()
        return {
            'base_score': params.get('base_score', cls.DEFAULT_BASE_SCORE),
            'age_threshold': params.get('age', {}).get('threshold', cls.DEFAULT_AGE_THRESHOLD),
            'age_coefficient': params.get('age', {}).get('coefficient', cls.DEFAULT_AGE_COEFFICIENT),
            'hb_threshold': params.get('hemoglobin', {}).get('threshold', cls.DEFAULT_HB_THRESHOLD),
            'hb_coefficient': params.get('hemoglobin', {}).get('coefficient', cls.DEFAULT_HB_COEFFICIENT),
            'egfr_threshold': params.get('egfr', {}).get('threshold', cls.DEFAULT_EGFR_THRESHOLD),
            'egfr_coefficient': params.get('egfr', {}).get('coefficient', cls.DEFAULT_EGFR_COEFFICIENT),
            'wbc_threshold': params.get('white_blood_cell_count', {}).get('threshold', cls.DEFAULT_WBC_THRESHOLD),
            'wbc_coefficient': params.get('white_blood_cell_count', {}).get('coefficient', cls.DEFAULT_WBC_COEFFICIENT),
            'bleeding_score': params.get('previous_bleeding', {}).get('score', cls.DEFAULT_BLEEDING_SCORE),
            'anticoag_score': params.get('oral_anticoagulation', {}).get('score', cls.DEFAULT_ANTICOAG_SCORE),
            'arc_hbr_score': params.get('arc_hbr_factors', {}).get('score', cls.DEFAULT_ARC_HBR_SCORE),
        }

    @staticmethod
    def _is_outdated(date_str):
        """Checks if the date is older than 3 months"""
        if not date_str or date_str == 'N/A':
            return False
            
        try:
            date_str = str(date_str).strip()
            
            if len(date_str) == 10 and '-' in date_str:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            elif 'T' in date_str:
                if date_str.endswith('Z'):
                    date_str = date_str[:-1] + '+00:00'
                dt = datetime.fromisoformat(date_str)
            else:
                return False
                
            if dt.tzinfo:
                now = datetime.now(dt.tzinfo)
            else:
                now = datetime.now()
                
            return (now - dt) > timedelta(days=90)
            
        except Exception as e:
            logging.warning(f"Error parsing date {date_str}: {e}")
            return False

    @classmethod
    def extract_inputs(cls, raw_data, demographics):
        """
        Extracts and normalizes inputs from FHIR data for PRECISE-HBR calculation.
        
        Args:
            raw_data: Dictionary with FHIR observation data
            demographics: Dictionary with patient demographics
            
        Returns:
            Dictionary of extracted inputs with metadata and missing field tracking
        """
        limits = cls._get_truncation_limits()
        
        inputs = {
            'age': None,
            'hb': None,
            'egfr': None,
            'wbc': None,
            'prior_bleeding': False,
            'oral_anticoag': False,
            'arc_hbr_count': 0,
            'missing_fields': [],
            'empty_fhir_resources': [],  # Track empty FHIR resource types
            'unit_issues': [],           # Track unrecognized/missing unit problems
            'metadata': {}
        }

        # 1. Age
        age = demographics.get('age')
        if age is not None:
            inputs['age'] = age
            inputs['metadata']['age_effective'] = max(limits['min_age'], min(limits['max_age'], age))
        else:
            inputs['missing_fields'].append('Age')

        # 2. Hemoglobin
        hemoglobin_list = raw_data.get('HEMOGLOBIN', [])
        if hemoglobin_list:
            hb_obs = hemoglobin_list[0]
            hb_result = unit_converter.get_value_with_status(hb_obs, unit_converter.TARGET_UNITS['HEMOGLOBIN'])
            if hb_result['value'] is not None:
                inputs['hb'] = hb_result['value']
                inputs['metadata']['hb_effective'] = max(limits['min_hb'], min(limits['max_hb'], hb_result['value']))
                inputs['metadata']['hb_date'] = hb_obs.get('effectiveDateTime', 'N/A')
            elif hb_result['status'] in (unit_converter.STATUS_UNKNOWN_UNIT, unit_converter.STATUS_MISSING_UNIT):
                inputs['unit_issues'].append({
                    'parameter': 'Hemoglobin',
                    'status': hb_result['status'],
                    'raw_value': hb_result['raw_value'],
                    'source_unit': hb_result['source_unit'],
                    'target_unit': hb_result['target_unit'],
                })
                inputs['missing_fields'].append('Hemoglobin')
            else:
                inputs['missing_fields'].append('Hemoglobin')
        else:
            inputs['missing_fields'].append('Hemoglobin')

        # 3. eGFR
        egfr_val = None
        egfr_source = ""
        egfr_unit_issue = None
        egfr_list = raw_data.get('EGFR', [])
        if egfr_list:
            egfr_obs = egfr_list[0]
            egfr_result = unit_converter.get_value_with_status(egfr_obs, unit_converter.TARGET_UNITS['EGFR'])
            if egfr_result['value'] is not None:
                egfr_val = egfr_result['value']
                egfr_source = "Direct eGFR"
                inputs['metadata']['egfr_date'] = egfr_obs.get('effectiveDateTime', 'N/A')
            elif egfr_result['status'] in (unit_converter.STATUS_UNKNOWN_UNIT, unit_converter.STATUS_MISSING_UNIT):
                egfr_unit_issue = {
                    'parameter': 'eGFR',
                    'status': egfr_result['status'],
                    'raw_value': egfr_result['raw_value'],
                    'source_unit': egfr_result['source_unit'],
                    'target_unit': egfr_result['target_unit'],
                }

        if egfr_val is None:
            creatinine_list = raw_data.get('CREATININE', [])
            if creatinine_list and inputs['age'] is not None and demographics.get('gender'):
                creatinine_obs = creatinine_list[0]
                cr_result = unit_converter.get_value_with_status(creatinine_obs, unit_converter.TARGET_UNITS['CREATININE'])
                if cr_result['value'] is not None:
                    calc_egfr, reason = unit_converter.calculate_egfr(cr_result['value'], inputs['age'], demographics['gender'])
                    if calc_egfr:
                        egfr_val = calc_egfr
                        egfr_source = reason
                        egfr_unit_issue = None  # Creatinine fallback succeeded
                        inputs['metadata']['egfr_date'] = creatinine_obs.get('effectiveDateTime', 'N/A')
                elif cr_result['status'] in (unit_converter.STATUS_UNKNOWN_UNIT, unit_converter.STATUS_MISSING_UNIT) and not egfr_unit_issue:
                    egfr_unit_issue = {
                        'parameter': 'Creatinine (for eGFR calculation)',
                        'status': cr_result['status'],
                        'raw_value': cr_result['raw_value'],
                        'source_unit': cr_result['source_unit'],
                        'target_unit': cr_result['target_unit'],
                    }

        if egfr_val is not None:
            inputs['egfr'] = egfr_val
            inputs['metadata']['egfr_effective'] = max(limits['min_egfr'], min(limits['max_egfr'], egfr_val))
            inputs['metadata']['egfr_source'] = egfr_source
        else:
            inputs['missing_fields'].append('eGFR')
            if egfr_unit_issue:
                inputs['unit_issues'].append(egfr_unit_issue)

        # 4. WBC
        wbc_list = raw_data.get('WBC', [])
        if wbc_list:
            wbc_obs = wbc_list[0]
            wbc_result = unit_converter.get_value_with_status(wbc_obs, unit_converter.TARGET_UNITS['WBC'])
            if wbc_result['value'] is not None:
                inputs['wbc'] = wbc_result['value']
                inputs['metadata']['wbc_effective'] = max(limits['min_wbc'], min(limits['max_wbc'], wbc_result['value']))
                inputs['metadata']['wbc_date'] = wbc_obs.get('effectiveDateTime', 'N/A')
            elif wbc_result['status'] in (unit_converter.STATUS_UNKNOWN_UNIT, unit_converter.STATUS_MISSING_UNIT):
                inputs['unit_issues'].append({
                    'parameter': 'WBC',
                    'status': wbc_result['status'],
                    'raw_value': wbc_result['raw_value'],
                    'source_unit': wbc_result['source_unit'],
                    'target_unit': wbc_result['target_unit'],
                })
                inputs['missing_fields'].append('WBC')
            else:
                inputs['missing_fields'].append('WBC')
        else:
            inputs['missing_fields'].append('WBC')

        # 5. Prior Bleeding
        conditions = raw_data.get('conditions', [])
        
        # Track if conditions list is empty (important for risk assessment)
        if not conditions:
            inputs['empty_fhir_resources'].append('Condition')
            inputs['metadata']['conditions_empty'] = True
        else:
            inputs['metadata']['conditions_empty'] = False
            inputs['metadata']['conditions_count'] = len(conditions)
        
        has_bleeding, evidence = condition_checker.check_prior_bleeding(conditions)
        inputs['prior_bleeding'] = has_bleeding
        inputs['metadata']['bleeding_evidence'] = evidence

        # 6. Oral Anticoagulation
        medications = raw_data.get('med_requests', [])
        
        # Track if medications list is empty (important for risk assessment)
        if not medications:
            inputs['empty_fhir_resources'].append('Medication')
            inputs['metadata']['medications_empty'] = True
        else:
            inputs['metadata']['medications_empty'] = False
            inputs['metadata']['medications_count'] = len(medications)
        
        has_anticoag = condition_checker.check_oral_anticoagulation(medications)
        inputs['oral_anticoag'] = has_anticoag

        # 7. ARC-HBR
        arc_details = condition_checker.check_arc_hbr_factors_detailed(raw_data, medications)
        inputs['arc_hbr_count'] = sum([
            arc_details['thrombocytopenia'], arc_details['bleeding_diathesis'],
            arc_details['liver_cirrhosis'], arc_details['active_malignancy'],
            arc_details['nsaids_corticosteroids'], arc_details.get('recent_major_surgery_trauma', False)
        ])
        inputs['metadata']['arc_details'] = arc_details
        
        return inputs

    # -----------------------------------------------------------------
    # Normalized-input extraction (canonical model)
    # IEC 62304 §5.3 — FHIR-agnostic input extraction
    # -----------------------------------------------------------------

    @classmethod
    def extract_inputs_normalized(cls, patient_data: NormalizedPatientData) -> dict:
        """
        Extract scoring inputs from a NormalizedPatientData instance.

        This is the preferred entry point: all FHIR parsing has already been
        done by FHIRNormalizer, so this method only reads clean Python
        dataclasses — no FHIR dict access whatsoever.
        """
        limits = cls._get_truncation_limits()

        inputs: dict = {
            'age': None,
            'hb': None,
            'egfr': None,
            'wbc': None,
            'prior_bleeding': False,
            'oral_anticoag': False,
            'arc_hbr_count': 0,
            'missing_fields': [],
            'empty_fhir_resources': [],
            'unit_issues': [],
            'metadata': {},
        }

        # 1. Age
        age = patient_data.demographics.age
        if age is not None:
            inputs['age'] = age
            inputs['metadata']['age_effective'] = max(limits['min_age'], min(limits['max_age'], age))
        else:
            inputs['missing_fields'].append('Age')

        # 2. Hemoglobin
        hb_lab = patient_data.hemoglobin
        if hb_lab and hb_lab.value is not None:
            inputs['hb'] = hb_lab.value
            inputs['metadata']['hb_effective'] = max(limits['min_hb'], min(limits['max_hb'], hb_lab.value))
            inputs['metadata']['hb_date'] = hb_lab.effective_date or 'N/A'
        elif hb_lab and hb_lab.status in (UnitConversionService.STATUS_UNKNOWN_UNIT, UnitConversionService.STATUS_MISSING_UNIT):
            inputs['unit_issues'].append({
                'parameter': 'Hemoglobin',
                'status': hb_lab.status,
                'raw_value': hb_lab.raw_value,
                'source_unit': hb_lab.source_unit,
                'target_unit': hb_lab.unit,
            })
            inputs['missing_fields'].append('Hemoglobin')
        else:
            inputs['missing_fields'].append('Hemoglobin')

        # 3. eGFR (already includes creatinine fallback from normalizer)
        egfr_lab = patient_data.egfr
        if egfr_lab and egfr_lab.value is not None:
            inputs['egfr'] = egfr_lab.value
            inputs['metadata']['egfr_effective'] = max(limits['min_egfr'], min(limits['max_egfr'], egfr_lab.value))
            inputs['metadata']['egfr_source'] = egfr_lab.source or ''
            inputs['metadata']['egfr_date'] = egfr_lab.effective_date or 'N/A'
        elif egfr_lab and egfr_lab.status in (UnitConversionService.STATUS_UNKNOWN_UNIT, UnitConversionService.STATUS_MISSING_UNIT):
            inputs['unit_issues'].append({
                'parameter': 'eGFR' if egfr_lab.source is None else egfr_lab.source,
                'status': egfr_lab.status,
                'raw_value': egfr_lab.raw_value,
                'source_unit': egfr_lab.source_unit,
                'target_unit': egfr_lab.unit,
            })
            inputs['missing_fields'].append('eGFR')
        else:
            inputs['missing_fields'].append('eGFR')

        # 4. WBC
        wbc_lab = patient_data.wbc
        if wbc_lab and wbc_lab.value is not None:
            inputs['wbc'] = wbc_lab.value
            inputs['metadata']['wbc_effective'] = max(limits['min_wbc'], min(limits['max_wbc'], wbc_lab.value))
            inputs['metadata']['wbc_date'] = wbc_lab.effective_date or 'N/A'
        elif wbc_lab and wbc_lab.status in (UnitConversionService.STATUS_UNKNOWN_UNIT, UnitConversionService.STATUS_MISSING_UNIT):
            inputs['unit_issues'].append({
                'parameter': 'WBC',
                'status': wbc_lab.status,
                'raw_value': wbc_lab.raw_value,
                'source_unit': wbc_lab.source_unit,
                'target_unit': wbc_lab.unit,
            })
            inputs['missing_fields'].append('WBC')
        else:
            inputs['missing_fields'].append('WBC')

        # 5. Prior Bleeding (normalized)
        if not patient_data.conditions:
            inputs['empty_fhir_resources'].append('Condition')
            inputs['metadata']['conditions_empty'] = True
        else:
            inputs['metadata']['conditions_empty'] = False
            inputs['metadata']['conditions_count'] = len(patient_data.conditions)

        has_bleeding, evidence = condition_checker.check_prior_bleeding_normalized(patient_data.conditions)
        inputs['prior_bleeding'] = has_bleeding
        inputs['metadata']['bleeding_evidence'] = evidence

        # 6. Oral Anticoagulation (normalized)
        if not patient_data.medications:
            inputs['empty_fhir_resources'].append('Medication')
            inputs['metadata']['medications_empty'] = True
        else:
            inputs['metadata']['medications_empty'] = False
            inputs['metadata']['medications_count'] = len(patient_data.medications)

        inputs['oral_anticoag'] = condition_checker.check_oral_anticoagulation_normalized(patient_data.medications)

        # 7. ARC-HBR (normalized)
        arc_details = condition_checker.check_arc_hbr_factors_normalized(patient_data)
        inputs['arc_hbr_count'] = sum([
            arc_details['thrombocytopenia'], arc_details['bleeding_diathesis'],
            arc_details['liver_cirrhosis'], arc_details['active_malignancy'],
            arc_details['nsaids_corticosteroids'], arc_details.get('recent_major_surgery_trauma', False),
        ])
        inputs['metadata']['arc_details'] = arc_details

        return inputs

    @classmethod
    def calculate_score_normalized(cls, patient_data: NormalizedPatientData):
        """
        Full score calculation from NormalizedPatientData.

        Returns the same (components, total_score, data_warnings) tuple as
        calculate_score(), but operates entirely on pre-normalized data.
        """
        inputs = cls.extract_inputs_normalized(patient_data)
        return cls._build_result(inputs)

    @classmethod
    def _check_truncation_warnings(cls, inputs):
        """
        Detect values that were truncated and generate clinical warnings.

        A truncated value means the EHR-reported value fell outside the
        clinically expected range. This could indicate:
        - Unit conversion error in the EHR (e.g., g/L reported as g/dL)
        - Data entry error
        - Genuinely extreme patient values

        In all cases, the clinician MUST be informed.
        """
        limits = cls._get_truncation_limits()
        warnings = []

        checks = [
            ('age', 'Age', inputs.get('age'), 'age_effective',
             limits['min_age'], limits['max_age'], 'years'),
            ('hb', 'Hemoglobin', inputs.get('hb'), 'hb_effective',
             limits['min_hb'], limits['max_hb'], 'g/dL'),
            ('egfr', 'eGFR', inputs.get('egfr'), 'egfr_effective',
             limits['min_egfr'], limits['max_egfr'], 'mL/min/1.73m²'),
            ('wbc', 'WBC', inputs.get('wbc'), 'wbc_effective',
             limits['min_wbc'], limits['max_wbc'], '10^9/L'),
        ]

        for key, label, raw_val, eff_key, low, high, unit in checks:
            if raw_val is None:
                continue
            eff_val = inputs['metadata'].get(eff_key)
            if eff_val is not None and raw_val != eff_val:
                direction = 'above' if raw_val > high else 'below'
                warnings.append({
                    'type': 'truncated_value',
                    'severity': 'high',
                    'parameter': label,
                    'raw_value': raw_val,
                    'effective_value': eff_val,
                    'unit': unit,
                    'range_min': low,
                    'range_max': high,
                    'direction': direction,
                    'message': (
                        f'{label} value {raw_val} {unit} is {direction} the expected '
                        f'clinical range ({low}-{high} {unit}). '
                        f'The score was calculated using the capped value of {eff_val} {unit}. '
                        f'Please verify this value — it may indicate a unit conversion error '
                        f'or data entry issue in the EHR.'
                    ),
                })

        return warnings

    @classmethod
    def _check_unit_issue_warnings(cls, inputs):
        """
        Generate high-severity warnings when lab values were present in the EHR
        but could not be used because the unit was unrecognized or missing.

        This is a Fail-safe mechanism for Class C medical devices: the system
        refuses to guess and explicitly alerts the clinician, rather than
        silently treating the value as "missing data".
        """
        warnings = []
        for issue in inputs.get('unit_issues', []):
            status = issue['status']
            param = issue['parameter']
            raw_val = issue['raw_value']
            source_unit = issue.get('source_unit')
            target_unit = issue['target_unit']

            if status == unit_converter.STATUS_MISSING_UNIT:
                message = (
                    f'{param} value {raw_val} was received from the EHR '
                    f'without a unit. The expected unit is {target_unit}. '
                    f'The system cannot safely assume the unit and has '
                    f'excluded this value from the score calculation. '
                    f'Please verify the value and unit in the EHR, then '
                    f'use the manual override if appropriate.'
                )
            else:  # STATUS_UNKNOWN_UNIT
                message = (
                    f'{param} value {raw_val} was received with an '
                    f'unrecognized unit "{source_unit}". '
                    f'The expected unit is {target_unit}. '
                    f'The system cannot safely convert this value and has '
                    f'excluded it from the score calculation. '
                    f'Please verify the value and unit in the EHR, then '
                    f'use the manual override if appropriate.'
                )

            warnings.append({
                'type': 'unrecognized_unit',
                'severity': 'high',
                'parameter': param,
                'raw_value': raw_val,
                'source_unit': source_unit,
                'target_unit': target_unit,
                'status': status,
                'message': message,
            })

        return warnings

    @classmethod
    def _build_result(cls, inputs, access_denied=None):
        """
        Shared result builder: turns extracted inputs into
        (components, total_score, data_warnings).

        Used by both calculate_score() and calculate_score_normalized().
        """
        total_score, breakdown = cls.calculate_pure_score(inputs)

        # Reconstruct detailed components for UI
        components = []

        # Base
        components.append({
            "parameter": "PRECISE-HBR - Base Score",
            "value": "Fixed base score",
            "score": breakdown['base'],
            "date": "N/A",
            "description": f"Base score: {breakdown['base']} points (fixed)"
        })

        # Age
        if 'Age' in inputs['missing_fields']:
            components.append({
                "parameter": "PRECISE-HBR - Age",
                "value": "Unknown",
                "score": 0,
                "date": "N/A",
                "description": "Age not available"
            })
        else:
            age = inputs['age']
            eff_age = inputs['metadata']['age_effective']
            age_display = f"{age} years (capped to {eff_age})" if age != eff_age else f"{age} years"
            components.append({
                "parameter": "PRECISE-HBR - Age",
                "value": age_display,
                "score": math.floor(breakdown['age'] + 0.5),
                "raw_value": age,
                "date": "N/A",
                "is_truncated": age != eff_age,
                "effective_value": eff_age,
                "description": f"Age score: {breakdown['age']:.2f}"
            })

        # Hemoglobin
        if 'Hemoglobin' in inputs['missing_fields']:
            components.append({
                "parameter": "PRECISE-HBR - Hemoglobin",
                "value": "Not available",
                "score": 0,
                "date": "N/A",
                "description": "Hemoglobin not available"
            })
        else:
            hb = inputs['hb']
            eff_hb = inputs['metadata']['hb_effective']
            hb_display = f"{hb} g/dL (capped to {eff_hb})" if hb != eff_hb else f"{hb} g/dL"
            components.append({
                "parameter": "PRECISE-HBR - Hemoglobin",
                "value": hb_display,
                "score": math.floor(breakdown['hb'] + 0.5),
                "raw_value": hb,
                "date": inputs['metadata'].get('hb_date', 'N/A'),
                "is_outdated": cls._is_outdated(inputs['metadata'].get('hb_date', 'N/A')),
                "is_truncated": hb != eff_hb,
                "effective_value": eff_hb,
                "description": f"Hb score: {breakdown['hb']:.2f}"
            })

        # eGFR
        if 'eGFR' in inputs['missing_fields']:
            components.append({
                "parameter": "PRECISE-HBR - eGFR",
                "value": "Not available",
                "score": 0,
                "date": "N/A",
                "description": "eGFR not available"
            })
        else:
            egfr = inputs['egfr']
            eff_egfr = inputs['metadata']['egfr_effective']
            egfr_display = f"{egfr} mL/min/1.73m² (capped to {eff_egfr})" if egfr != eff_egfr else f"{egfr} mL/min/1.73m²"
            components.append({
                "parameter": "PRECISE-HBR - eGFR",
                "value": egfr_display,
                "score": math.floor(breakdown['egfr'] + 0.5),
                "raw_value": egfr,
                "date": inputs['metadata'].get('egfr_date', 'N/A'),
                "is_outdated": cls._is_outdated(inputs['metadata'].get('egfr_date', 'N/A')),
                "is_truncated": egfr != eff_egfr,
                "effective_value": eff_egfr,
                "description": f"eGFR score: {breakdown['egfr']:.2f}"
            })

        # WBC
        if 'WBC' in inputs['missing_fields']:
            components.append({
                "parameter": "PRECISE-HBR - White Blood Cell Count",
                "value": "Not available",
                "score": 0,
                "date": "N/A",
                "description": "WBC not available"
            })
        else:
            wbc = inputs['wbc']
            eff_wbc = inputs['metadata']['wbc_effective']
            wbc_display = f"{wbc} 10^9/L (capped to {eff_wbc})" if wbc != eff_wbc else f"{wbc} 10^9/L"
            components.append({
                "parameter": "PRECISE-HBR - White Blood Cell Count",
                "value": wbc_display,
                "score": math.floor(breakdown['wbc'] + 0.5),
                "raw_value": wbc,
                "date": inputs['metadata'].get('wbc_date', 'N/A'),
                "is_outdated": cls._is_outdated(inputs['metadata'].get('wbc_date', 'N/A')),
                "is_truncated": wbc != eff_wbc,
                "effective_value": eff_wbc,
                "description": f"WBC score: {breakdown['wbc']:.2f}"
            })

        # Bleeding
        components.append({
            "parameter": "PRECISE-HBR - Prior Bleeding",
            "value": "Yes" if inputs['prior_bleeding'] else "No",
            "score": breakdown['bleeding'],
            "is_present": inputs['prior_bleeding'],
            "description": f"Prior Bleeding: {breakdown['bleeding']}"
        })

        # Anticoag
        components.append({
            "parameter": "PRECISE-HBR - Oral Anticoagulation",
            "value": "Yes" if inputs['oral_anticoag'] else "No",
            "score": breakdown['anticoag'],
            "is_present": inputs['oral_anticoag'],
            "description": f"Anticoagulation: {breakdown['anticoag']}"
        })

        # ARC-HBR Details
        arc_details = inputs['metadata'].get('arc_details', {})

        components.append({
            "parameter": "PRECISE-HBR - Platelet Count",
            "value": "Yes" if arc_details.get('thrombocytopenia') else "No",
            "score": 0,
            "is_present": arc_details.get('thrombocytopenia', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Platelet count < 100x10^9/L"
        })

        components.append({
            "parameter": "PRECISE-HBR - Chronic Bleeding Diathesis",
            "value": "Yes" if arc_details.get('bleeding_diathesis') else "No",
            "score": 0,
            "is_present": arc_details.get('bleeding_diathesis', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "History of chronic bleeding diathesis"
        })

        components.append({
            "parameter": "PRECISE-HBR - Liver Cirrhosis",
            "value": "Yes" if arc_details.get('liver_cirrhosis') else "No",
            "score": 0,
            "is_present": arc_details.get('liver_cirrhosis', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Liver cirrhosis with portal hypertension"
        })

        components.append({
            "parameter": "PRECISE-HBR - Active Malignancy",
            "value": "Yes" if arc_details.get('active_malignancy') else "No",
            "score": 0,
            "is_present": arc_details.get('active_malignancy', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Active malignancy in past 12 months"
        })

        components.append({
            "parameter": "PRECISE-HBR - NSAIDs/Corticosteroids",
            "value": "Yes" if arc_details.get('nsaids_corticosteroids') else "No",
            "score": 0,
            "is_present": arc_details.get('nsaids_corticosteroids', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Chronic use of NSAIDs or corticosteroids"
        })

        components.append({
            "parameter": "PRECISE-HBR - Recent Major Surgery or Trauma",
            "value": "Yes" if arc_details.get('recent_major_surgery_trauma') else "No",
            "score": 0,
            "is_present": arc_details.get('recent_major_surgery_trauma', False),
            "is_arc_hbr_element": True,
            "date": "N/A",
            "description": "Recent major surgery or trauma"
        })

        components.append({
            "parameter": "PRECISE-HBR - ARC-HBR Summary",
            "value": f"{inputs['arc_hbr_count']} factor(s)",
            "score": breakdown['arc_hbr'],
            "is_present": inputs['arc_hbr_count'] > 0,
            "description": f"ARC-HBR: {breakdown['arc_hbr']}"
        })

        # Build data warnings
        data_warnings = []
        empty_resources = inputs.get('empty_fhir_resources', [])

        if 'Condition' in empty_resources:
            data_warnings.append({
                'type': 'missing_fhir_resource',
                'resource': 'Condition',
                'message': 'No Condition records found - Prior Bleeding History and ARC-HBR factors (bleeding diathesis, liver cirrhosis, active malignancy, recent major surgery or trauma) may be missed.',
                'affected_factors': ['Prior Bleeding', 'Bleeding Diathesis', 'Liver Cirrhosis', 'Active Malignancy', 'Recent Major Surgery or Trauma']
            })

        if 'Medication' in empty_resources:
            data_warnings.append({
                'type': 'missing_fhir_resource',
                'resource': 'Medication',
                'message': 'No Medication records found - Oral Anticoagulation status and NSAID/Corticosteroid use may be inaccurate.',
                'affected_factors': ['Oral Anticoagulation', 'NSAIDs/Corticosteroids']
            })

        # Access-denied warnings (Break the Glass)
        if access_denied:
            denied_str = ', '.join(access_denied)
            data_warnings.append({
                'type': 'access_denied',
                'severity': 'critical',
                'denied_resources': access_denied,
                'message': (
                    f'Access denied (403 Forbidden) for: {denied_str}. '
                    f'This patient may have Break the Glass (BTG) protections. '
                    f'The score was calculated with INCOMPLETE data and may '
                    f'UNDERESTIMATE bleeding risk. Please complete BTG authorization '
                    f'in the EHR and recalculate.'
                ),
            })

        # Truncation warnings
        truncation_warnings = cls._check_truncation_warnings(inputs)
        data_warnings.extend(truncation_warnings)

        # Unit issue warnings (Fail-safe for Class C)
        unit_issue_warnings = cls._check_unit_issue_warnings(inputs)
        data_warnings.extend(unit_issue_warnings)

        logging.info(f"PRECISE-HBR calculation complete: {total_score}")
        if data_warnings:
            warning_types = [w.get('resource', w.get('parameter', '?')) for w in data_warnings]
            logging.warning(f"Data warnings: {warning_types}")

        return components, total_score, data_warnings

    @classmethod
    def calculate_pure_score(cls, inputs):
        """
        Calculates score from extracted inputs.
        Only performs math. Does not handle IO or extractions.
        Uses coefficients from config.
        
        Args:
            inputs: Dictionary from extract_inputs
            
        Returns:
            Tuple (score, breakdown_dict)
        """
        coeffs = cls._get_scoring_coefficients()
        
        score = float(coeffs['base_score'])
        breakdown = {'base': coeffs['base_score']}
        
        # Age: (effective_age - threshold) × coefficient
        if inputs['age'] is not None:
            eff_age = inputs['metadata']['age_effective']
            if eff_age > coeffs['age_threshold']:
                s = (eff_age - coeffs['age_threshold']) * coeffs['age_coefficient']
                score += s
                breakdown['age'] = s
            else:
                breakdown['age'] = 0
        else:
            breakdown['age'] = 0

        # Hemoglobin: (threshold - effective_hb) × coefficient
        if inputs['hb'] is not None:
            eff_hb = inputs['metadata']['hb_effective']
            if eff_hb < coeffs['hb_threshold']:
                s = (coeffs['hb_threshold'] - eff_hb) * coeffs['hb_coefficient']
                score += s
                breakdown['hb'] = s
            else:
                breakdown['hb'] = 0
        else:
            breakdown['hb'] = 0

        # eGFR: (threshold - effective_egfr) × coefficient
        if inputs['egfr'] is not None:
            eff_egfr = inputs['metadata']['egfr_effective']
            if eff_egfr < coeffs['egfr_threshold']:
                s = (coeffs['egfr_threshold'] - eff_egfr) * coeffs['egfr_coefficient']
                score += s
                breakdown['egfr'] = s
            else:
                breakdown['egfr'] = 0
        else:
            breakdown['egfr'] = 0

        # WBC: (effective_wbc - threshold) × coefficient
        if inputs['wbc'] is not None:
            eff_wbc = inputs['metadata']['wbc_effective']
            if eff_wbc > coeffs['wbc_threshold']:
                s = (eff_wbc - coeffs['wbc_threshold']) * coeffs['wbc_coefficient']
                score += s
                breakdown['wbc'] = s
            else:
                breakdown['wbc'] = 0
        else:
            breakdown['wbc'] = 0

        # Binary Factors
        if inputs['prior_bleeding']:
            score += coeffs['bleeding_score']
            breakdown['bleeding'] = coeffs['bleeding_score']
        else:
            breakdown['bleeding'] = 0
            
        if inputs['oral_anticoag']:
            score += coeffs['anticoag_score']
            breakdown['anticoag'] = coeffs['anticoag_score']
        else:
            breakdown['anticoag'] = 0
            
        if inputs['arc_hbr_count'] > 0:
            score += coeffs['arc_hbr_score']
            breakdown['arc_hbr'] = coeffs['arc_hbr_score']
        else:
            breakdown['arc_hbr'] = 0
            
        return math.floor(score + 0.5), breakdown

    @classmethod
    def calculate_score(cls, raw_data, demographics):
        """
        Main entry point for PRECISE-HBR score calculation (legacy interface).
        Uses extract_inputs and calculate_pure_score.

        Returns:
            Tuple of (components_list, total_score, data_warnings)
        """
        inputs = cls.extract_inputs(raw_data, demographics)
        return cls._build_result(inputs, access_denied=raw_data.get('_access_denied_resources', []))


# Global instance
precise_hbr_calculator = PreciseHBRCalculator()


# Legacy functions for backward compatibility
def calculate_precise_hbr_score(raw_data, demographics):
    """Legacy function - calls the new calculator service"""
    return precise_hbr_calculator.calculate_score(raw_data, demographics)


def calculate_risk_components(raw_data, demographics):
    """Legacy function - calls PRECISE-HBR calculator"""
    return precise_hbr_calculator.calculate_score(raw_data, demographics)


def get_calculator_inputs(raw_data, demographics):
    """Utility to get inputs and check missing fields directly"""
    return precise_hbr_calculator.extract_inputs(raw_data, demographics)
