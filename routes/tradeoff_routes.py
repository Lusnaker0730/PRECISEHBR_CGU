from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from services import fhir_data_service
from fhirclient import client
import logging
from utils.web_utils import login_required

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

        fhir_session_data = session['fhir_data']
        raw_data, error = fhir_data_service.get_fhir_data(
            fhir_server_url=fhir_session_data.get('server'),
            access_token=fhir_session_data.get('token'),
            patient_id=patient_id,
            client_id=fhir_session_data.get('client_id')
        )
        if error:
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
