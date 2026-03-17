import json
import logging
import os
import time
from typing import Optional

from flask import Blueprint, jsonify, request
from flask_cors import CORS

from services.audit_logger import get_audit_logger
from services.config_loader import config_loader
from services.fhir_data_service import (
    get_patient_demographics,
    calculate_precise_hbr_score,
    get_precise_hbr_display_info
)
from services.precise_hbr_calculator import get_calculator_inputs, precise_hbr_calculator

# Load medication and CDS hooks configuration
_med_config = config_loader.config.get('medication_keywords', {})
_cds_config = config_loader.config.get('cds_hooks_config', {})

# CDS Hooks deadline — EHRs expect responses within 500ms.
# We set a generous 3s budget to account for network + compute.
CDS_DEADLINE_SECONDS = 3.0

hooks_bp = Blueprint('hooks', __name__)

# Enable CORS for ALL CDS Hooks endpoints (required for external CDS Hooks clients like sandbox.cds-hooks.org)
CORS(hooks_bp, 
     origins="*",  # Allow all origins for CDS Hooks
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=False)


def _build_medication_lookup():
    """Build medication lookup dictionaries from config."""
    aspirin_cfg = _med_config.get('aspirin', {})
    aspirin_codes = {
        'rxnorm': aspirin_cfg.get('rxnorm_codes', ['1191']),
        'names': aspirin_cfg.get('generic_names', []) + aspirin_cfg.get('brand_names', [])
    }

    antiplatelet_cfg = _med_config.get('antiplatelet_agents', {})
    antiplatelet_agents = {}
    for agent in ['clopidogrel', 'prasugrel', 'ticagrelor']:
        agent_cfg = antiplatelet_cfg.get(agent, {})
        if agent_cfg:
            antiplatelet_agents[agent] = {
                'rxnorm': agent_cfg.get('rxnorm_codes', []),
                'names': agent_cfg.get('generic_names', []) + agent_cfg.get('brand_names', [])
            }

    oac_cfg = _med_config.get('oral_anticoagulants', {})
    oral_anticoagulants = {
        'warfarin': {'rxnorm': ['11289'], 'names': ['warfarin', 'coumadin']},
        'apixaban': {'rxnorm': ['1364430'], 'names': ['apixaban', 'eliquis']},
        'rivaroxaban': {'rxnorm': ['1114195'], 'names': ['rivaroxaban', 'xarelto']}
    }
    # Override with config if available
    if oac_cfg.get('rxnorm_codes'):
        for i, name in enumerate(oac_cfg.get('generic_names', [])):
            if i < len(oac_cfg['rxnorm_codes']):
                brand = oac_cfg.get('brand_names', [])[i] if i < len(oac_cfg.get('brand_names', [])) else ''
                oral_anticoagulants[name] = {
                    'rxnorm': [oac_cfg['rxnorm_codes'][i]],
                    'names': [name, brand] if brand else [name]
                }

    return aspirin_codes, antiplatelet_agents, oral_anticoagulants


def check_high_bleeding_risk_medications(medications):
    """
    Check if patient is on medications that increase bleeding risk.
    Uses medication codes from cdss_config.json.
    """
    aspirin_codes, antiplatelet_agents, oral_anticoagulants = _build_medication_lookup()

    found_meds = {'aspirin': False, 'antiplatelet': None, 'anticoagulant': None}
    medication_details = []

    for med in medications:
        if not med or 'medicationCodeableConcept' not in med:
            continue
        med_concept = med['medicationCodeableConcept']
        med_name = med_concept.get('text', '').lower()
        med_codes = [c.get('code') for c in med_concept.get('coding', [])
                     if c.get('system') == 'http://www.nlm.nih.gov/research/umls/rxnorm']

        # Simplified check logic for brevity
        if any(c in aspirin_codes['rxnorm'] for c in med_codes) or any(n in med_name for n in aspirin_codes['names']):
            found_meds['aspirin'] = True
            medication_details.append({'name': 'Aspirin'})
            continue

        for agent, details in antiplatelet_agents.items():
            if any(c in details['rxnorm'] for c in med_codes) or any(n in med_name for n in details['names']):
                found_meds['antiplatelet'] = agent
                medication_details.append({'name': agent.title()})
                break

        for agent, details in oral_anticoagulants.items():
            if any(c in details['rxnorm'] for c in med_codes) or any(n in med_name for n in details['names']):
                found_meds['anticoagulant'] = agent
                medication_details.append({'name': agent.title()})
                break

    has_dapt = found_meds['aspirin'] and found_meds['antiplatelet']
    has_anticoagulant = found_meds['anticoagulant']
    return has_dapt or has_anticoagulant, medication_details


def _get_risk_indicator(risk_category):
    """Get CDS Hooks indicator from risk category using config."""
    indicators = _cds_config.get('risk_indicators', {})
    if "Very" in risk_category:
        return indicators.get('very_high_risk', 'critical')
    elif "HBR" in risk_category:
        return indicators.get('high_risk', 'warning')
    return indicators.get('low_risk', 'info')


def _get_source_info():
    """Get source information from config."""
    source = _cds_config.get('source', {})
    return {
        "label": source.get('label', 'PRECISE-HBR Bleeding Risk Calculator'),
        "url": source.get('url', 'https://www.acc.org/latest-in-cardiology/articles/2022/01/18/16/19/predicting-out-of-hospital-bleeding-after-pci')
    }


def _get_service_request_code():
    """Get service request code from config."""
    code_cfg = _cds_config.get('service_request_code', {})
    return {
        "system": code_cfg.get('system', 'http://loinc.org'),
        "code": code_cfg.get('code', 'LA-PRECISE-HBR')
    }


def create_precise_hbr_warning_card(
        patient_name,
        precise_hbr_score,
        risk_category,
        bleeding_risk_percentage,
        medications_found):
    """Create a CDS Hooks card for PRECISE-HBR high bleeding risk warning."""

    medication_list = ", ".join([med['name'] for med in medications_found])
    indicator = _get_risk_indicator(risk_category)
    source = _get_source_info()
    service_code = _get_service_request_code()

    card = {
        "summary": f"{risk_category}: Patient score {precise_hbr_score} ({bleeding_risk_percentage}% 1-yr risk)",
        "detail": f"Patient on {medication_list} has a PRECISE-HBR score of {precise_hbr_score}. "
                  "Consider shorter DAPT duration and enhanced monitoring.",
        "indicator": indicator,
        "source": source,
        "suggestions": [
            {
                "label": "View Detailed Assessment",
                "actions": [
                    {
                        "type": "create",
                        "description": "Launch detailed PRECISE-HBR risk calculator",
                        "resource": {
                            "resourceType": "ServiceRequest",
                            "status": "draft",
                            "intent": "proposal",
                            "code": {"coding": [service_code]},
                            "subject": {"reference": f"Patient/{{{{context.patientId}}}}"}
                        }
                    }
                ]
            },
        ]
    }
    return card


def _build_fallback_card(reason='timeout'):
    """
    Build a graceful degradation card when the CDS Hook cannot complete
    within the deadline or the FHIR server is unavailable.

    Returns a CDS Hooks card that informs the clinician without blocking
    their workflow.
    """
    source = _get_source_info()

    if reason == 'timeout':
        summary = "PRECISE-HBR: Assessment delayed — data retrieval slow"
        detail = (
            "The bleeding risk assessment could not be completed within the "
            "response deadline. The health records server may be experiencing "
            "high load. Please use the full PRECISE-HBR Calculator for a "
            "complete assessment."
        )
    elif reason == 'circuit_open':
        summary = "PRECISE-HBR: Assessment unavailable — server temporarily unreachable"
        detail = (
            "The health records server has been temporarily unreachable. "
            "The system will automatically retry shortly. Please use the "
            "full PRECISE-HBR Calculator or assess bleeding risk manually."
        )
    elif reason == 'access_denied':
        summary = "PRECISE-HBR: Patient data access restricted (Break the Glass)"
        detail = (
            "This patient's clinical data is protected and requires elevated access. "
            "Please complete Break the Glass (BTG) authorization in the EHR, "
            "then re-open the patient's chart to trigger a new assessment."
        )
    else:
        summary = "PRECISE-HBR: Assessment could not be completed"
        detail = (
            "An unexpected issue prevented the bleeding risk assessment. "
            "Please use the full PRECISE-HBR Calculator for a complete assessment."
        )

    return {
        "summary": summary,
        "indicator": "warning",
        "detail": detail,
        "source": source,
    }


def _extract_cds_user(hook_request: Optional[dict]) -> Optional[str]:
    """Extract practitioner identity from CDS Hooks fhirAuthorization or context.

    CDS Hooks spec: fhirAuthorization.userId is a FHIR reference like
    'Practitioner/12345'. Some EHRs also put userId in context.
    """
    if not hook_request:
        return None
    fhir_auth = hook_request.get('fhirAuthorization', {})
    if fhir_auth and fhir_auth.get('userId'):
        return fhir_auth['userId']
    return hook_request.get('context', {}).get('userId')


def _get_cds_ip() -> str:
    """Get real client IP for CDS Hooks (X-Forwarded-For aware)."""
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or ''


def _log_cds_event(
    action: str,
    hook_request: Optional[dict] = None,
    patient_id: Optional[str] = None,
    outcome: str = 'success',
    details: Optional[dict] = None,
) -> None:
    """Convenience: log a CDS Hooks audit event."""
    get_audit_logger().log_event(
        event_type='CDS_DECISION',
        action=action,
        patient_id=patient_id,
        fhir_user=_extract_cds_user(hook_request),
        outcome=outcome,
        ip_address=_get_cds_ip(),
        user_agent=request.headers.get('User-Agent'),
        details=details or {},
    )


class _DeadlineExceeded(Exception):
    """Raised when CDS Hook processing exceeds the deadline."""
    pass


def _check_deadline(start_time, stage=''):
    """
    Check if the CDS deadline has been exceeded.

    Args:
        start_time: monotonic time when processing started
        stage: description of current processing stage (for logging)

    Raises:
        _DeadlineExceeded: if deadline is exceeded
    """
    elapsed = time.monotonic() - start_time
    if elapsed >= CDS_DEADLINE_SECONDS:
        logging.warning(
            f"CDS Hook deadline exceeded at stage '{stage}' "
            f"({elapsed:.2f}s >= {CDS_DEADLINE_SECONDS}s)"
        )
        raise _DeadlineExceeded(stage)


@hooks_bp.route('/cds-services', methods=['GET'])
def cds_services_discovery():
    """CDS Hooks service discovery endpoint."""
    try:
        # Construct path relative to root where app runs
        config_path = os.path.join(os.getcwd(), 'config', 'cds-services.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        _log_cds_event(
            action='service_discovery',
            outcome='success',
            details={'endpoint': '/cds-services'},
        )
        return jsonify(config_data)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        config_path = os.path.join(os.getcwd(), 'config', 'cds-services.json')
        logging.error(f"Could not load cds-services.json from {config_path}: {e}")
        # Fallback config from cdss_config.json
        fallback_svc = _cds_config.get('fallback_service', {})
        fallback_config = {
            "services": [
                {
                    "hook": fallback_svc.get("hook", "medication-prescribe"),
                    "id": fallback_svc.get("id", "precise_hbr_bleeding_risk_alert"),
                    "title": fallback_svc.get("title", "PRECISE-HBR High Bleeding Risk Alert"),
                    "description": fallback_svc.get("description", "Alert for patients with high bleeding risk (PRECISE-HBR >= 23)")
                }
            ]
        }
        return jsonify(fallback_config)


@hooks_bp.route('/cds-services/precise_hbr_bleeding_risk_alert', methods=['POST'])
def handle_precise_hbr_bleeding_risk_hook():
    """
    Shared handler for PRECISE-HBR high bleeding risk alerts.

    Enforces a CDS deadline to ensure fast response to the EHR.
    If processing exceeds the deadline, returns a fallback card.
    """
    start_time = time.monotonic()
    try:
        hook_request = request.get_json(silent=True)  # C-03
        if not hook_request:
            return jsonify({"cards": []}), 400

        context = hook_request.get('context', {})
        prefetch = hook_request.get('prefetch', {})
        patient_id = context.get('patientId')
        if not patient_id:
            return jsonify({"cards": []})

        patient_data = prefetch.get('patient')
        patient_name = "Patient"
        if patient_data:
            name_data = patient_data.get('name', [{}])[0]
            given = " ".join(name_data.get('given', []))
            family = name_data.get('family', "")
            patient_name = f"{given} {family}".strip() or patient_id

        _check_deadline(start_time, 'prefetch_extraction')

        medications = prefetch.get('medications', {}).get('entry', [])
        medication_resources = [
            entry.get('resource') for entry in medications if entry.get('resource')]

        has_high_risk_meds, high_risk_medications = check_high_bleeding_risk_medications(
            medication_resources)

        if not has_high_risk_meds:
            _log_cds_event(
                action='precise_hbr_bleeding_risk',
                hook_request=hook_request,
                patient_id=patient_id,
                outcome='success',
                details={
                    'hook': 'medication-prescribe',
                    'cards_returned': 0,
                    'reason': 'no_high_risk_medications',
                    'elapsed_seconds': round(time.monotonic() - start_time, 3),
                },
            )
            return jsonify({"cards": []})

        _check_deadline(start_time, 'medication_check')

        raw_data = {
            'patient': patient_data,
            'HEMOGLOBIN': [entry['resource'] for entry in prefetch.get('hemoglobin', {}).get('entry', [])],
            'CREATININE': [entry['resource'] for entry in prefetch.get('creatinine', {}).get('entry', [])],
            'EGFR': [entry['resource'] for entry in prefetch.get('egfr', {}).get('entry', [])],
            'WBC': [entry['resource'] for entry in prefetch.get('wbc', {}).get('entry', [])],
            'conditions': [entry['resource'] for entry in prefetch.get('conditions', {}).get('entry', [])]
        }

        demographics = get_patient_demographics(patient_data)

        # New Safety Check: Validate inputs first
        inputs = get_calculator_inputs(raw_data, demographics)
        missing_fields = inputs.get('missing_fields', [])

        _check_deadline(start_time, 'input_extraction')

        if missing_fields:
            # SAFETY IMPROVEMENT: Do not calculate potentially misleading score
            logging.warning(f"CDS Hook skipped due to missing data: {missing_fields}")
            _log_cds_event(
                action='precise_hbr_bleeding_risk',
                hook_request=hook_request,
                patient_id=patient_id,
                outcome='success',
                details={
                    'hook': 'medication-prescribe',
                    'cards_returned': 0,
                    'reason': 'missing_fields',
                    'missing_fields': missing_fields,
                    'elapsed_seconds': round(time.monotonic() - start_time, 3),
                },
            )
            return jsonify({"cards": []})  # silence preferred over noise if uncertain

        # Calculate score using pure calculator (or legacy wrapper)
        total_score, _ = precise_hbr_calculator.calculate_pure_score(inputs)

        high_risk_threshold = config_loader.config.get('scoring_logic', {}).get('high_risk_threshold', 23)
        if total_score >= high_risk_threshold:
            # get_precise_hbr_display_info returns a dict with keys:
            # score, risk_category, score_range, bleeding_risk_percent,
            # color_class, full_label, recommendation
            display_info = get_precise_hbr_display_info(total_score)
            risk_category = display_info['risk_category']
            bleeding_risk_percentage = display_info['bleeding_risk_percent']

            warning_card = create_precise_hbr_warning_card(
                patient_name, total_score, risk_category,
                bleeding_risk_percentage, high_risk_medications
            )
            _log_cds_event(
                action='precise_hbr_bleeding_risk',
                hook_request=hook_request,
                patient_id=patient_id,
                outcome='success',
                details={
                    'hook': 'medication-prescribe',
                    'score': total_score,
                    'risk_category': str(risk_category),
                    'cards_returned': 1,
                    'elapsed_seconds': round(time.monotonic() - start_time, 3),
                },
            )
            return jsonify({"cards": [warning_card]})
        else:
            _log_cds_event(
                action='precise_hbr_bleeding_risk',
                hook_request=hook_request,
                patient_id=patient_id,
                outcome='success',
                details={
                    'hook': 'medication-prescribe',
                    'score': total_score,
                    'cards_returned': 0,
                    'reason': 'below_threshold',
                    'elapsed_seconds': round(time.monotonic() - start_time, 3),
                },
            )
            return jsonify({"cards": []})

    except _DeadlineExceeded as de:
        elapsed = time.monotonic() - start_time
        logging.warning(f"CDS Hook deadline exceeded: {de} ({elapsed:.2f}s)")
        _log_cds_event(
            action='precise_hbr_bleeding_risk',
            hook_request=hook_request if 'hook_request' in locals() else None,
            patient_id=patient_id if 'patient_id' in locals() else None,
            outcome='timeout',
            details={
                'hook': 'medication-prescribe',
                'stage': str(de),
                'elapsed_seconds': round(elapsed, 3),
            },
        )
        return jsonify({"cards": [_build_fallback_card('timeout')]})

    except Exception as e:
        elapsed = time.monotonic() - start_time
        logging.error(
            f"Error in PRECISE-HBR CDS Hook: {e}",
            exc_info=True)
        _log_cds_event(
            action='precise_hbr_bleeding_risk',
            hook_request=hook_request if 'hook_request' in locals() else None,
            patient_id=patient_id if 'patient_id' in locals() else None,
            outcome='error',
            details={
                'hook': 'medication-prescribe',
                'error': str(e),
                'elapsed_seconds': round(elapsed, 3),
            },
        )
        return jsonify({"cards": [_build_fallback_card('error')]}), 500


@hooks_bp.route('/cds-services/precise_hbr_patient_view', methods=['POST'])
def precise_hbr_patient_view():
    """
    CDS Hook for patient-view context.
    Displays PRECISE-HBR bleeding risk assessment when viewing a patient.
    This hook is triggered automatically when a clinician opens a patient's chart.

    Enforces a CDS deadline to ensure fast response to the EHR.
    """
    start_time = time.monotonic()
    try:
        data = request.get_json(silent=True)  # C-03
        if not data:
            return jsonify({"cards": []}), 400
        logging.info(f"Received patient-view CDS Hook request: {data.get('hook')}")

        # Extract context and prefetch data
        context = data.get('context', {})
        prefetch = data.get('prefetch', {})
        patient_id = context.get('patientId')

        if not patient_id:
            logging.warning("No patientId in context for patient-view hook")
            return jsonify({"cards": []})

        # Get patient data from prefetch
        patient_data = prefetch.get('patient')
        if not patient_data:
            logging.warning(f"No patient data in prefetch for patient {patient_id}")
            return jsonify({"cards": []})

        # Get patient name for display
        patient_name = "Patient"
        if patient_data.get('name') and len(patient_data['name']) > 0:
            name_parts = patient_data['name'][0]
            given = ' '.join(name_parts.get('given', []))
            family = name_parts.get('family', '')
            patient_name = f"{given} {family}".strip() or "Patient"

        _check_deadline(start_time, 'patient_view_prefetch')

        # Check medications for high bleeding risk
        medications = prefetch.get('medications', {}).get('entry', [])
        _, high_risk_medications = check_high_bleeding_risk_medications(medications)

        # Prepare raw data for risk calculation
        raw_data = {
            'patient': patient_data,
            'HEMOGLOBIN': [entry['resource'] for entry in prefetch.get('hemoglobin', {}).get('entry', [])],
            'CREATININE': [entry['resource'] for entry in prefetch.get('creatinine', {}).get('entry', [])],
            'EGFR': [entry['resource'] for entry in prefetch.get('egfr', {}).get('entry', [])],
            'WBC': [entry['resource'] for entry in prefetch.get('wbc', {}).get('entry', [])],
            'conditions': [entry['resource'] for entry in prefetch.get('conditions', {}).get('entry', [])]
        }

        # Calculate risk score with safety check
        demographics = get_patient_demographics(patient_data)
        
        # 1. Extract inputs & check missing
        inputs = get_calculator_inputs(raw_data, demographics)
        missing_fields = inputs.get('missing_fields', [])
        
        if missing_fields:
            # SAFETY WARNING CARD
            missing_str = ", ".join(missing_fields)
            source = _get_source_info()
            service_code = _get_service_request_code()
            warning_card = {
                "summary": "Data Missing: PRECISE-HBR Risk Assessment incomplete",
                "indicator": "warning",
                "detail": f"Cannot calculate reliable bleeding risk score. Missing data: {missing_str}. "
                          f"The score assumes normal values for missing fields, which may underestimate risk.",
                "source": source,
                "suggestions": [
                     {
                        "label": "Open Calculator to Edit Data",
                         "actions": [
                            {
                                "type": "create",
                                "description": "Launch detailed PRECISE-HBR risk calculator",
                                "resource": {
                                    "resourceType": "ServiceRequest",
                                    "status": "draft",
                                    "intent": "proposal",
                                    "code": {"coding": [service_code]},
                                    "subject": {"reference": f"Patient/{{{{context.patientId}}}}"}
                                }
                            }
                        ]
                    }
                ]
            }
            _log_cds_event(
                action='precise_hbr_patient_view',
                hook_request=data,
                patient_id=patient_id,
                outcome='success',
                details={
                    'hook': 'patient-view',
                    'cards_returned': 1,
                    'reason': 'missing_fields',
                    'missing_fields': missing_fields,
                    'elapsed_seconds': round(time.monotonic() - start_time, 3),
                },
            )
            return jsonify({"cards": [warning_card]})

        # 2. Calculate if data complete
        total_score, _ = precise_hbr_calculator.calculate_pure_score(inputs)
        
        # get_precise_hbr_display_info returns a dict with keys:
        # score, risk_category, score_range, bleeding_risk_percent,
        # color_class, full_label, recommendation
        display_info = get_precise_hbr_display_info(total_score)
        full_label = display_info['full_label']
        recommendation = display_info['recommendation']

        # Always show an info card in patient-view (even for low risk)
        high_risk_threshold = config_loader.config.get('scoring_logic', {}).get('high_risk_threshold', 23)
        if total_score >= high_risk_threshold:
            # High risk - show warning card
            card = create_precise_hbr_warning_card(
                patient_name, total_score, display_info['risk_category'],
                display_info['bleeding_risk_percent'], high_risk_medications
            )
        else:
            # Low/moderate risk - show info card
            source = _get_source_info()
            card = {
                "summary": f"PRECISE-HBR Score: {total_score} - {full_label}",
                "indicator": "info",
                "detail": f"{patient_name} has a {full_label.lower()} for major bleeding. "
                         f"PRECISE-HBR score: {total_score}. {recommendation}",
                "source": source,
                "links": []
            }
        
        _log_cds_event(
            action='precise_hbr_patient_view',
            hook_request=data,
            patient_id=patient_id,
            outcome='success',
            details={
                'hook': 'patient-view',
                'score': total_score,
                'risk_category': str(full_label),
                'cards_returned': 1,
                'elapsed_seconds': round(time.monotonic() - start_time, 3),
            },
        )
        return jsonify({"cards": [card]})

    except _DeadlineExceeded as de:
        elapsed = time.monotonic() - start_time
        logging.warning(f"Patient-view CDS Hook deadline exceeded: {de} ({elapsed:.2f}s)")
        _log_cds_event(
            action='precise_hbr_patient_view',
            hook_request=data if 'data' in locals() else None,
            patient_id=patient_id if 'patient_id' in locals() else None,
            outcome='timeout',
            details={
                'hook': 'patient-view',
                'stage': str(de),
                'elapsed_seconds': round(elapsed, 3),
            },
        )
        return jsonify({"cards": [_build_fallback_card('timeout')]})

    except Exception as e:
        elapsed = time.monotonic() - start_time
        logging.error(f"Error in patient-view CDS Hook: {e}", exc_info=True)
        _log_cds_event(
            action='precise_hbr_patient_view',
            hook_request=data if 'data' in locals() else None,
            patient_id=patient_id if 'patient_id' in locals() else None,
            outcome='error',
            details={
                'hook': 'patient-view',
                'error': str(e),
                'elapsed_seconds': round(elapsed, 3),
            },
        )
        return jsonify({"cards": [_build_fallback_card('error')]}), 500
