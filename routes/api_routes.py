from flask import Blueprint, request, jsonify, session, Response, current_app
from extensions import limiter
from utils.web_utils import login_required
from services.audit_logger import audit_ephi_access
import utils.input_validator as input_validator
from services import fhir_data_service
from services.ccd_generator import generate_ccd_from_session_data
import re
import datetime

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/calculate_risk', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
@audit_ephi_access(action='calculate_risk_score', resource_type='Patient,Observation,Condition')
def calculate_risk_api():
    """API endpoint for risk score calculation."""
    try:
        data = request.get_json()
        if not data or 'patientId' not in data:
            return jsonify({'error': 'Patient ID is required.'}), 400
        
        patient_id = data['patientId']
        
        # Check for null/empty patient ID
        if not patient_id:
            return jsonify({'error': 'Patient ID is required.'}), 400
        
        # Validate patient ID
        is_valid, error_msg = input_validator.validate_patient_id(patient_id)
        if not is_valid:
            patient_id_preview = str(patient_id)[:50] if patient_id else 'None'
            current_app.logger.warning(f"Invalid patient ID rejected: {patient_id_preview}")
            return jsonify({'error': f'Invalid patient ID: {error_msg}'}), 400
        
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
                    'error_type': 'service_error',
                    'details': str(error)
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
        score_components, total_score = fhir_data_service.calculate_precise_hbr_score(raw_data, demographics)
        display_info = fhir_data_service.get_precise_hbr_display_info(total_score)
        
        final_response = {
            "patient_info": {"patient_id": patient_id, **demographics},
            "total_score": total_score,
            "risk_level": display_info.get('full_label'),
            "recommendation": display_info.get('recommendation'),
            "score_components": score_components
        }
        return jsonify(final_response)
    
    except Exception as e:
        current_app.logger.error(f"Error in calculate_risk_api: {str(e)}", exc_info=True)
        if "FHIR server is down" in str(e):
            return jsonify({'error': 'FHIR data service is unavailable.', 'details': str(e)}), 503
        return jsonify({'error': 'An internal server error occurred.'}), 500

@api_bp.route('/api/export-ccd', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
@audit_ephi_access(action='export_ccd_document', resource_type='Patient,Observation,Condition')
def export_ccd_api():
    """API endpoint to generate and download C-CDA CCD document."""
    try:
        data = request.get_json()
        
        if not data:
            current_app.logger.error("No JSON data received in CCD export request")
            return jsonify({'error': 'No data provided in request.'}), 400
        
        current_app.logger.info(f"CCD export request received")
        
        patient_id = session.get('patient_id', 'N/A')
        
        risk_data = data.get('risk_data')
        if not risk_data:
            return jsonify({'error': 'Risk assessment data is required.'}), 400
        
        # Recalculate score server-side
        try:
            # Construct inputs for calculator
            calc_inputs = {
                'age': float(data.get('patient_age')) if data.get('patient_age') and str(data.get('patient_age')) != 'Unknown' else None,
                'hb': float(risk_data.get('hemoglobin')) if risk_data.get('hemoglobin') and risk_data.get('hemoglobin') != 'Not available' else None,
                'egfr': float(risk_data.get('egfr')) if risk_data.get('egfr') and risk_data.get('egfr') != 'Not available' else None,
                'wbc': float(risk_data.get('wbc')) if risk_data.get('wbc') and risk_data.get('wbc') != 'Not available' else None,
                'prior_bleeding': 'Prior spontaneous bleeding' in str(risk_data.get('arc_hbr_factors', [])),
                'oral_anticoag': 'oral anticoagulation' in str(risk_data.get('arc_hbr_factors', [])),
                'arc_hbr_count': 0,
                'missing_fields': [],
                'metadata': {'age_effective': 0, 'hb_effective': 0, 'egfr_effective': 0, 'wbc_effective': 0}
            }
            
            # Recalculate effective values
            # Dynamic import to avoid circular dependencies if any, though regular import is fine here if path is correct
            from services.precise_hbr_calculator import precise_hbr_calculator
            
            if calc_inputs['age']: calc_inputs['metadata']['age_effective'] = max(30, min(80, calc_inputs['age']))
            if calc_inputs['hb']: calc_inputs['metadata']['hb_effective'] = max(5.0, min(15.0, calc_inputs['hb']))
            if calc_inputs['egfr']: calc_inputs['metadata']['egfr_effective'] = max(5, min(100, calc_inputs['egfr']))
            if calc_inputs['wbc']: calc_inputs['metadata']['wbc_effective'] = min(15.0, calc_inputs['wbc'])
            
            arc_factors = risk_data.get('arc_hbr_factors', [])
            count_factors = 0
            for f in arc_factors:
                f_lower = f.lower()
                if ('prior spontaneous bleeding' not in f_lower and 'oral anticoagulation' not in f_lower):
                    count_factors += 1
            calc_inputs['arc_hbr_count'] = count_factors
            
            # Perform calculation
            calculated_score, _ = precise_hbr_calculator.calculate_pure_score(calc_inputs)
            client_score = float(risk_data.get('total_score', 0))
            
            if abs(calculated_score - client_score) > 1.0:
                current_app.logger.warning(f"SECURITY ADVISORY: Client score ({client_score}) mismatches server calculation ({calculated_score}). Enforcing server calculation.")
                risk_data['total_score'] = calculated_score
                from services.risk_classifier import risk_classifier
                display_info = risk_classifier.get_precise_hbr_display_info(calculated_score)
                risk_data['risk_category'] = display_info['full_label']
            
        except Exception as calc_err:
            current_app.logger.error(f"Error verifying risk score: {calc_err}")
            
        patient_data = {
            'id': patient_id,
            'name': data.get('patient_name', 'Unknown Patient'),
            'gender': data.get('patient_gender', 'Unknown'),
            'birth_date': data.get('patient_birth_date', '1970-01-01'),
            'age': data.get('patient_age', 'Unknown')
        }
        
        try:
            ccd_xml = generate_ccd_from_session_data(
                patient_data=patient_data,
                risk_data=risk_data,
                raw_fhir_data={}
            )
        except Exception as ccd_error:
            current_app.logger.error(f"Error generating CCD document: {str(ccd_error)}")
            return jsonify({'error': 'Failed to generate CCD document', 'details': str(ccd_error)}), 500
        
        safe_patient_id = re.sub(r'[^\w\-]', '_', str(patient_id))
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return Response(
            ccd_xml,
            mimetype='application/xml',
            headers={
                'Content-Disposition': f'attachment; filename=PRECISE_HBR_CCD_{safe_patient_id}_{timestamp}.xml',
                'Content-Type': 'application/xml; charset=utf-8'
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating CCD: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to generate CCD document.', 'details': str(e)}), 500
