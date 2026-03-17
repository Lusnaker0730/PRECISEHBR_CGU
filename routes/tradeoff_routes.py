from flask import Blueprint, current_app, render_template, request, session, jsonify, redirect, url_for
from services import fhir_data_service
from fhirclient import client
import logging
from extensions import limiter
from utils.web_utils import login_required
from utils.patient_context import validate_patient_context
import utils.input_validator as input_validator

# Use Flask's logger
logger = logging.getLogger('werkzeug')

# Create a Blueprint
tradeoff_bp = Blueprint('tradeoff', __name__, template_folder='templates')

# --- Blueprint Routes ---

@tradeoff_bp.route('/tradeoff_analysis')
@login_required
def tradeoff_analysis_page():
    """Renders the tradeoff analysis page."""
    patient_id = session.get('patient_id', 'N/A')
    return render_template('tradeoff_analysis.html', patient_id=patient_id)

@tradeoff_bp.route('/api/calculate_tradeoff', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def calculate_tradeoff_api():
    """
    API endpoint for the bleeding vs. thrombosis tradeoff analysis.
    Handles both initial data load (with patientId) and recalculations (with active_factors).
    """
    try:
        data = request.get_json()
        model = fhir_data_service.get_tradeoff_model_predictors()

        # Check if model was loaded successfully
        if model is None:
            logger.error("Failed to load tradeoff model. arc-hbr-model.json may be missing or invalid.")
            return jsonify({'error': 'Tradeoff model configuration is not available. Please contact support.'}), 500

        # Case 1: Recalculation based on user-selected factors
        if 'active_factors' in data:
            active_factors = data.get('active_factors', {})
            recalculated_scores = fhir_data_service.calculate_tradeoff_scores_interactive(model, active_factors)
            return jsonify(recalculated_scores)

        # Case 2: Initial data load for a patient
        patient_id = data.get('patientId')
        if not patient_id:
            return jsonify({'error': 'Patient ID or active factors are required.'}), 400

        # BOLA protection: validate patient context matches OAuth session
        is_ctx_valid, ctx_err = validate_patient_context(patient_id)
        if not is_ctx_valid:
            current_app.logger.warning(f"BOLA violation in tradeoff: {ctx_err}")
            return jsonify({'error': ctx_err, 'error_type': 'authorization_error'}), 403

        # Validate patient ID format
        is_valid, error_msg = input_validator.validate_patient_id(patient_id)
        if not is_valid:
            return jsonify({'error': f'Invalid patient ID: {error_msg}', 'error_type': 'validation_error'}), 400

        fhir_session_data = session['fhir_data']
        raw_data, error = fhir_data_service.get_fhir_data(
            fhir_server_url=fhir_session_data.get('server'),
            access_token=fhir_session_data.get('token'),
            patient_id=patient_id,
            client_id=fhir_session_data.get('client_id')
        )
        if error:
            error_lower = error.lower()
            if "authentication failed" in error_lower or "re-launch" in error_lower:
                current_app.logger.warning(f"FHIR 401 in tradeoff for patient {patient_id}: token expired")
                return jsonify({
                    'error': 'Your session has expired. Please re-launch the application from your EHR.',
                    'error_type': 'auth_expired',
                    'requires_reauth': True
                }), 401
            raise Exception(f"FHIR data service failed: {error}")
            
        demographics = fhir_data_service.get_patient_demographics(raw_data.get('patient'))
        
        tradeoff_data = fhir_data_service.get_tradeoff_model_data(
            fhir_server_url=fhir_session_data.get('server'),
            access_token=fhir_session_data.get('token'),
            client_id=fhir_session_data.get('client_id'),
            patient_id=patient_id
        )

        detected_factors_list = fhir_data_service.detect_tradeoff_factors(raw_data, demographics, tradeoff_data)
        
        # Create a dictionary of all possible factors, marking detected ones as true
        all_factors = {p['factor']: False for p in model['bleedingEvents']['predictors']}
        all_factors.update({p['factor']: False for p in model['thromboticEvents']['predictors']})
        for factor in detected_factors_list:
            if factor in all_factors:
                all_factors[factor] = True

        initial_scores = fhir_data_service.calculate_tradeoff_scores_interactive(model, all_factors)

        return jsonify({
            'model': model, 
            'detected_factors': all_factors, # Send the dictionary so checkboxes are correctly checked
            'initial_scores': initial_scores
        })

    except Exception as e:
        logger.error(f"Error in calculate_tradeoff_api blueprint: {str(e)}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred during tradeoff analysis.'}), 500
