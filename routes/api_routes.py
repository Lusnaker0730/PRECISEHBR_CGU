from flask import Blueprint, request, jsonify, session, current_app
from extensions import limiter
from utils.web_utils import login_required
from utils.patient_context import require_patient_context
from services.audit_logger import audit_ephi_access, get_audit_logger
from services.config_loader import config_loader
import utils.input_validator as input_validator
from services import fhir_data_service

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/calculate_risk', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
@audit_ephi_access(action='calculate_risk_score', resource_type='Patient,Observation,Condition')
def calculate_risk_api():
    """API endpoint for risk score calculation."""
    try:
        data = request.get_json()
        patient_id = data.get('patientId') if data else None

        # C-04: Explicit BOLA validation immediately after extraction
        if patient_id:
            from utils.patient_context import validate_patient_context
            is_ctx_valid, ctx_err = validate_patient_context(patient_id)
            if not is_ctx_valid:
                current_app.logger.warning(f"BOLA violation: {ctx_err}")
                return jsonify({'error': ctx_err, 'error_type': 'authorization_error'}), 403

        # Check for missing/empty patient ID
        if not patient_id:
            return jsonify({
                'error': 'Patient ID is required.',
                'error_type': 'validation_error'
            }), 400

        # Validate patient ID format
        is_valid, error_msg = input_validator.validate_patient_id(patient_id)
        if not is_valid:
            patient_id_preview = str(patient_id)[:50] if patient_id else 'None'
            current_app.logger.warning(f"Invalid patient ID rejected: {patient_id_preview}")
            return jsonify({
                'error': f'Invalid patient ID: {error_msg}',
                'error_type': 'validation_error'
            }), 400
        
        fhir_session_data = session['fhir_data']
        raw_data, error = fhir_data_service.get_fhir_data(
            fhir_server_url=fhir_session_data.get('server'),
            access_token=fhir_session_data.get('token'),
            patient_id=patient_id,
            client_id=fhir_session_data.get('client_id')
        )
        
        if error:
            error_lower = error.lower()
            if "timeout" in error_lower or "504" in error or "gateway time-out" in error_lower:
                current_app.logger.warning(f"FHIR server timeout for patient {patient_id}: {error}")
                return jsonify({
                    'error': 'The FHIR data service is currently experiencing delays. Please try again in a moment.',
                    'error_type': 'service_timeout',
                    'details': 'External health record system is temporarily slow'
                }), 503
            elif "connection" in error_lower or "network" in error_lower:
                current_app.logger.error(f"FHIR server connection error for patient {patient_id}: {error}")
                return jsonify({
                    'error': 'Unable to connect to the health record system. Please check your connection and try again.',
                    'error_type': 'connection_error',
                    'details': 'Network connectivity issue with external service'
                }), 503
            else:
                current_app.logger.error(f"FHIR data service error for patient {patient_id}: {error}")
                return jsonify({
                    'error': 'An error occurred while retrieving patient data from the health record system.',
                    'error_type': 'service_error'
                    # C-07: Internal details removed - logged server-side only
                }), 500
        
        # Explicitly check if the patient data is missing after the call
        if not raw_data or not raw_data.get('patient'):
            current_app.logger.warning(f"No patient data retrieved for patient {patient_id}")
            return jsonify({
                'error': 'Patient data could not be found in the health record system.',
                'error_type': 'data_not_found',
                'details': 'The specified patient may not exist or you may not have access to their data'
            }), 404

        demographics = fhir_data_service.get_patient_demographics(raw_data.get('patient'))
        
        # calculate_precise_hbr_score now returns (components, score, data_warnings)
        result = fhir_data_service.calculate_precise_hbr_score(raw_data, demographics)
        
        # Handle both legacy (2-tuple) and new (3-tuple) return formats
        if len(result) == 3:
            score_components, total_score, data_warnings = result
        else:
            score_components, total_score = result
            data_warnings = []
        
        display_info = fhir_data_service.get_precise_hbr_display_info(total_score)
        
        final_response = {
            "patient_info": {"patient_id": patient_id, **demographics},
            "total_score": total_score,
            "risk_level": display_info.get('full_label'),
            "recommendation": display_info.get('recommendation'),
            "score_components": score_components,
            "data_warnings": data_warnings  # Include warnings about missing FHIR resources
        }
        return jsonify(final_response)
    
    except Exception as e:
        current_app.logger.error(f"Error in calculate_risk_api: {str(e)}", exc_info=True)
        if "FHIR server is down" in str(e):
            return jsonify({
                'error': 'FHIR data service is unavailable.',
                'error_type': 'service_unavailable'
            }), 503
        return jsonify({
            'error': 'An internal server error occurred.',
            'error_type': 'internal_error'
        }), 500

@api_bp.route('/api/config/scoring', methods=['GET'])
@limiter.limit("30 per minute")
def get_scoring_config():
    """
    API endpoint to expose PRECISE-HBR scoring configuration to frontend.

    This enables dynamic coefficient loading, eliminating the need for
    hardcoded values in JavaScript and ensuring frontend/backend consistency.

    Returns:
        JSON object with coefficients, thresholds, truncation limits, and binary scores
    """
    try:
        params = config_loader.get_precise_hbr_params()
        
        if not params:
            return jsonify({
                'error': 'Configuration not available',
                'error_type': 'config_error'
            }), 500
        
        config_response = {
            'base_score': params.get('base_score', 2),
            'coefficients': {
                'age': {
                    'threshold': params.get('age', {}).get('threshold', 30),
                    'coefficient': params.get('age', {}).get('coefficient', 0.25),
                    'truncation_min': params.get('age', {}).get('truncation_min', 30),
                    'truncation_max': params.get('age', {}).get('truncation_max', 80)
                },
                'hemoglobin': {
                    'threshold': params.get('hemoglobin', {}).get('threshold', 15.0),
                    'coefficient': params.get('hemoglobin', {}).get('coefficient', 2.5),
                    'truncation_min': params.get('hemoglobin', {}).get('truncation_min', 5.0),
                    'truncation_max': params.get('hemoglobin', {}).get('truncation_max', 15.0)
                },
                'egfr': {
                    'threshold': params.get('egfr', {}).get('threshold', 100),
                    'coefficient': params.get('egfr', {}).get('coefficient', 0.05),
                    'truncation_min': params.get('egfr', {}).get('truncation_min', 5),
                    'truncation_max': params.get('egfr', {}).get('truncation_max', 100)
                },
                'wbc': {
                    'threshold': params.get('white_blood_cell_count', {}).get('threshold', 3.0),
                    'coefficient': params.get('white_blood_cell_count', {}).get('coefficient', 0.8),
                    'truncation_min': params.get('white_blood_cell_count', {}).get('truncation_min', 3.0),
                    'truncation_max': params.get('white_blood_cell_count', {}).get('truncation_max', 15.0)
                }
            },
            'binary_scores': {
                'prior_bleeding': params.get('previous_bleeding', {}).get('score', 7),
                'oral_anticoagulation': params.get('oral_anticoagulation', {}).get('score', 5),
                'arc_hbr': params.get('arc_hbr_factors', {}).get('score', 3)
            }
        }
        
        return jsonify(config_response)
        
    except Exception as e:
        current_app.logger.error(f"Error loading scoring config: {str(e)}")
        return jsonify({
            'error': 'Failed to load configuration',
            'error_type': 'config_error'
        }), 500

@api_bp.route('/api/feedback', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def submit_feedback():
    """API endpoint for user feedback submission."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No data provided',
                'error_type': 'validation_error'
            }), 400

        patient_id = data.get('patient_id', 'unknown')
        feedback_type = data.get('feedback_type', 'unknown')
        comment = data.get('comment', '')
        score = data.get('score')
        risk_level = data.get('risk_level')

        # Log feedback for analysis
        current_app.logger.info(
            f"User feedback received - Type: {feedback_type}, "
            f"Patient: {patient_id}, Score: {score}, Risk: {risk_level}"
        )

        # Store feedback in audit log
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type='USER_FEEDBACK',
            action='submit_feedback',
            patient_id=patient_id,
            user_id=session.get('session_id', 'unknown'),
            outcome='success',
            details={
                'feedback_type': feedback_type,
                'comment': comment[:200] if comment else '',  # Limit comment length in log
                'score': score,
                'risk_level': risk_level
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Thank you for your feedback!'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in submit_feedback: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An internal server error occurred.',
            'error_type': 'internal_error'
        }), 500
