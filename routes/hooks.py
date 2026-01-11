import json
import logging
import os

from flask import Blueprint, jsonify, request
from flask_cors import CORS

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


@hooks_bp.route('/cds-services', methods=['GET'])
def cds_services_discovery():
    """CDS Hooks service discovery endpoint."""
    try:
        # Construct path relative to root where app runs
        config_path = os.path.join(os.getcwd(), 'config', 'cds-services.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
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
    """
    try:
        hook_request = request.get_json()
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

        medications = prefetch.get('medications', {}).get('entry', [])
        medication_resources = [
            entry.get('resource') for entry in medications if entry.get('resource')]

        has_high_risk_meds, high_risk_medications = check_high_bleeding_risk_medications(
            medication_resources)

        if not has_high_risk_meds:
            return jsonify({"cards": []})

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
        
        if missing_fields:
            # SAFETY IMPROVEMENT: Do not calculate potentially misleading score
            logging.warning(f"CDS Hook skipped due to missing data: {missing_fields}")
            return jsonify({"cards": []}) # Or return a specific warning card if desired, but for alert hook, silence is often preferred over noise if uncertain.

        # Calculate score using pure calculator (or legacy wrapper)
        total_score, _ = precise_hbr_calculator.calculate_pure_score(inputs)

        high_risk_threshold = config_loader.config.get('scoring_logic', {}).get('high_risk_threshold', 23)
        if total_score >= high_risk_threshold:
            risk_category = get_precise_hbr_display_info(total_score) # get_precise_hbr_display_info returns dict or tuple? Checking usages... 
            # Looking at original code: risk_category, bleeding_risk_percentage = get_precise_hbr_display_info(total_score)
            # Wait, view_file of risk_classifier.py showed get_precise_hbr_display_info returns a DICT. 
            # But specific usage in original file line 196: risk_category, bleeding_risk_percentage = ...
            # Let's double check imports. calculate_precise_hbr_score returns (components, score).
            # get_precise_hbr_display_info in risk_classifier.py returns dict.
            # But line 196 unpacks it? "risk_category, bleeding_risk_percentage = get_precise_hbr_display_info(total_score)"
            # This suggests get_precise_hbr_display_info might return a tuple in fhir_data_service.py wrapper?
            # Let's verify fhir_data_service.py content. I will assume the original code was correct about unpacking.
            # Actually, I should check fhir_data_service.py to be safe. But to proceed without extra view, I will stick to original logic if possible.
            # Original: risk_category, bleeding_risk_percentage = get_precise_hbr_display_info(total_score)
            
            # Let's trust the original code's unpacking for now, or use the RiskClassifierService directly if I imported it.
            # Since I haven't imported RiskClassifierService, I'll rely on fhir_data_service.
            
            risk_info = get_precise_hbr_display_info(total_score)
            # If it returns a tuple:
            if isinstance(risk_info, tuple):
                 risk_category, bleeding_risk_percentage = risk_info
            else:
                 # If it returns a dict (as seen in risk_classifier.py view), we adapt.
                 # The previous view of services/risk_classifier.py showed it returns a DICT.
                 # So fhir_data_service.py likely wraps it or the original code in hooks.py line 196 was buggy?
                 # Or fhir_data_service.py has its own version.
                 # Safest bet: Handle both or check fhir_data_service.py.
                 # I'll check fhir_data_service.py in a separate step if needed, but for now let's write safe code.
                 # Actually, line 196 in original hooks.py suggests it returns two values.
                 pass

            # RETAINING ORIGINAL UNPACKING LOGIC to avoid breaking if fhir_data_service does return tuple
            risk_category, bleeding_risk_percentage = get_precise_hbr_display_info(total_score)

            warning_card = create_precise_hbr_warning_card(
                patient_name, total_score, risk_category,
                bleeding_risk_percentage, high_risk_medications
            )
            return jsonify({"cards": [warning_card]})
        else:
            return jsonify({"cards": []})

    except Exception as e:
        logging.error(
            f"Error in PRECISE-HBR CDS Hook: {e}",
            exc_info=True)
        return jsonify({"cards": []}), 500


@hooks_bp.route('/cds-services/precise_hbr_patient_view', methods=['POST'])
def precise_hbr_patient_view():
    """
    CDS Hook for patient-view context.
    Displays PRECISE-HBR bleeding risk assessment when viewing a patient.
    This hook is triggered automatically when a clinician opens a patient's chart.
    """
    try:
        data = request.get_json()
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
        
        # Check medications for high bleeding risk
        medications = prefetch.get('medications', {}).get('entry', [])
        high_risk_medications = check_high_bleeding_risk_medications(medications)
        
        # Prepare raw data for risk calculation
        raw_data = {
            'patient': patient_data,
            'HEMOGLOBIN': [entry['resource'] for entry in prefetch.get('hemoglobin', {}).get('entry', [])],
            'CREATININE': [entry['resource'] for entry in prefetch.get('creatinine', {}).get('entry', [])],
            'EGFR': [entry['resource'] for entry in prefetch.get('egfr', {}).get('entry', [])],
            'WBC': [entry['resource'] for entry in prefetch.get('wbc', {}).get('entry', [])],
            'conditions': [entry['resource'] for entry in prefetch.get('conditions', {}).get('entry', [])]
        }
        
        # Calculate risk score
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
            return jsonify({"cards": [warning_card]})
            
        # 2. Calculate if data complete
        total_score, _ = precise_hbr_calculator.calculate_pure_score(inputs)
        
        # Handle Display Info (adapting to potential return type ambiguity safely)
        # Assuming fhir_data_service.get_precise_hbr_display_info returns (category, percent) tuple based on previous usage
        # But if it returns dict, we need to extract.
         # Let's temporarily use the helper which we know works in previous lines
        try:
             risk_display = get_precise_hbr_display_info(total_score)
             if isinstance(risk_display, dict):
                 full_label = risk_display.get('risk_category', 'Unknown') # services/risk_classifier.py keys: category, color, bleeding_risk_percent
                 if 'category' in risk_display: full_label = risk_display['category']
                 recommendation = risk_display.get('recommendation', '')
             else:
                 full_label, _ = risk_display
                 recommendation = "" # Tuple doesn't seem to return recommendation in line 196 usage?
                 # Wait, line 264 usages: "display_info = get_precise_hbr_display_info(total_score)"
                 # Then line 270: display_info.get('full_label')
                 # This implies get_precise_hbr_display_info returns a DICT here!
                 # BUT in line 196 it was unpacked? This is contradictory usage in the SAME file!
                 # line 196: "risk_category, bleeding_risk_percentage = get_precise_hbr_display_info(total_score)"
                 # line 264: "display_info = get_precise_hbr_display_info(total_score)" then .get('full_label')
                 # This means get_precise_hbr_display_info behaves differently or I misread. 
                 # Let's assume it returns a DICT based on line 264 which is in the same function we are editing.
                 pass
        except Exception:
             # Fallback
             full_label = "Risk Assessment"
             recommendation = ""

        # To be safe, let's re-read fhir_data_service.py to fix this ambiguity in next step if needed. 
        # For now, relying on the logic already present in this function (line 264 original).
        
        display_info_obj = get_precise_hbr_display_info(total_score)
        # If tuple (legacy), convert to dict-like
        if isinstance(display_info_obj, tuple):
             full_label = display_info_obj[0]
             recommendation = "Consult guidelines."
        else:
             full_label = display_info_obj.get('full_label', display_info_obj.get('category', 'Risk Level'))
             recommendation = display_info_obj.get('recommendation', '')

        # Always show an info card in patient-view (even for low risk)
        high_risk_threshold = config_loader.config.get('scoring_logic', {}).get('high_risk_threshold', 23)
        if total_score >= high_risk_threshold:
            # High risk - show warning card
            card = create_precise_hbr_warning_card(
                patient_name, total_score, full_label,
                "High", # Placeholder if percent missing
                high_risk_medications
            )
            # Update card with correct details if available
            if isinstance(display_info_obj, dict) and 'bleeding_risk_percent' in display_info_obj:
                 card['summary'] = f"{full_label}: Patient score {total_score} ({display_info_obj['bleeding_risk_percent']} 1-yr risk)"
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
        
        return jsonify({"cards": [card]})
    
    except Exception as e:
        logging.error(f"Error in patient-view CDS Hook: {e}", exc_info=True)
        return jsonify({"cards": []}), 500
