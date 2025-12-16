import logging
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
import os
import datetime
from fhirclient import client
import fhir_data_service
from dotenv import load_dotenv
import base64
import hashlib
import re
from functools import wraps
import requests
from urllib.parse import urlparse
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session  # For server-side session storage
# ONC Compliance: Audit logging
from audit_logger import get_audit_logger, audit_ephi_access, log_user_authentication
# ONC Compliance: CCD Export
from ccd_generator import generate_ccd_from_session_data
# Security: Input validation
import input_validator

# --- Google Secret Manager Helper ---
# Import the Secret Manager client library.
try:
    from google.cloud import secretmanager
    HAS_SECRET_MANAGER = True
except ImportError:
    HAS_SECRET_MANAGER = False

def get_secret(env_var, default=None):
    """
    Retrieves a secret from environment variables or Google Secret Manager.
    If the value of the env_var looks like a GCP secret path, it fetches it.
    Otherwise, it returns the environment variable's value directly.
    """
    value = os.environ.get(env_var)
    if not value:
        return default

    # Check if the value is a GCP secret resource name
    if HAS_SECRET_MANAGER and value.startswith('projects/'):
        resolved_value = value
        try:
            # Handle placeholder for project ID in GAE environment
            if '${PROJECT_ID}' in resolved_value:
                gcp_project = os.environ.get('GOOGLE_CLOUD_PROJECT')
                if not gcp_project:
                    logging.error("GOOGLE_CLOUD_PROJECT env var not set, cannot resolve secret path.")
                    return default
                resolved_value = resolved_value.replace('${PROJECT_ID}', gcp_project)

            secret_client = secretmanager.SecretManagerServiceClient()
            response = secret_client.access_secret_version(name=resolved_value)
            return response.payload.data.decode('UTF-8')
        except Exception as e:
            logging.error(f"Failed to access secret for {env_var} at path '{resolved_value}'. Error: {e}")
            return default
    
    return value

# Import the blueprints
from tradeoff_analysis_routes import tradeoff_bp, calculate_tradeoff_api # Import the blueprint and view
from hooks import hooks_bp  # Import CDS Hooks blueprint
from flask_talisman import Talisman
from flask_cors import CORS

# --- Constants for Cerner ---
# This is now a more generic check for any Cerner domain.
CERNER_DOMAIN = 'cerner.com'

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# R-01 Risk Mitigation: Ensure FLASK_SECRET_KEY is set from environment
SECRET_KEY = get_secret('FLASK_SECRET_KEY')
if not SECRET_KEY:
    app.logger.error("FATAL: FLASK_SECRET_KEY environment variable must be set for security.")
    raise ValueError("FLASK_SECRET_KEY environment variable is required but not set.")

app.secret_key = SECRET_KEY

# Configure Flask-Session for server-side session storage
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
# Determine session directory based on environment
if os.environ.get('GAE_ENV', '').startswith('standard'):
    # Use secure temp directory for Google App Engine
    import tempfile
    app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'flask_session')
else:
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'flask_session')

# Enable secure and HttpOnly cookies
app.config['SESSION_COOKIE_HTTPONLY'] = True
# Only require HTTPS cookies in production (App Engine)
# For local development with HTTP, this must be False
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('GAE_ENV', '').startswith('standard')  # True only on App Engine
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow cookies in SMART launch context

# Initialize Flask-Session for server-side storage
Session(app)

# R-03 Risk Mitigation: Configure logging with ePHI protection
from logging_filter import setup_ephi_logging_filter

logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.DEBUG)

# Install ePHI logging filter for HIPAA compliance
setup_ephi_logging_filter(app)

# Environment variables are now fetched using our helper function
CLIENT_ID = get_secret('SMART_CLIENT_ID')
REDIRECT_URI = get_secret('SMART_REDIRECT_URI')
CLIENT_SECRET = get_secret('SMART_CLIENT_SECRET')
SMART_SCOPES = get_secret('SMART_SCOPES', 'launch openid fhirUser profile user/Patient.rs user/Observation.rs user/Condition.rs user/MedicationRequest.rs user/Procedure.rs')

if not CLIENT_ID or not REDIRECT_URI:
    app.logger.error("FATAL: SMART_CLIENT_ID and SMART_REDIRECT_URI must be set.")

# --- Helper Functions & Decorators ---

def is_session_valid():
    required_keys = ['server', 'token', 'client_id']
    fhir_data = session.get('fhir_data')
    return bool(fhir_data and all(key in fhir_data for key in required_keys))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_session_valid():
            app.logger.warning(f"Access to '{request.path}' denied. No valid session.")
            if request.path.startswith('/api/'):
                return jsonify({"error": "Authentication required."}), 401
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def render_error_page(title="Error", message="An unexpected error has occurred."):
    app.logger.error(f"Rendering error page: {title} - {message}")
    return render_template('error.html', error_title=title, error_message=message), 500

# --- API Endpoints ---

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    Returns the application health status.
    """
    try:
        # Basic health check - can be expanded to check database, FHIR server, etc.
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'service': 'PRECISE-HBR SMART on FHIR',
            'version': '1.0.0'
        }
        return jsonify(health_status), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 503

@app.route('/api/calculate_risk', methods=['POST'])
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
            app.logger.warning(f"Invalid patient ID rejected: {patient_id_preview}")
            return jsonify({'error': f'Invalid patient ID: {error_msg}'}), 400
        fhir_session_data = session['fhir_data']
        raw_data, error = fhir_data_service.get_fhir_data(
            fhir_server_url=fhir_session_data.get('server'),
            access_token=fhir_session_data.get('token'),
            patient_id=patient_id,
            client_id=fhir_session_data.get('client_id')
        )
        # R-05 Risk Mitigation: Improved error handling for external service failures
        if error:
            if "timeout" in error.lower() or "504" in error or "gateway time-out" in error.lower():
                app.logger.warning(f"FHIR server timeout for patient {patient_id}: {error}")
                return jsonify({
                    'error': 'The FHIR data service is currently experiencing delays. Please try again in a moment.',
                    'error_type': 'service_timeout',
                    'details': 'External health record system is temporarily slow'
                }), 503
            elif "connection" in error.lower() or "network" in error.lower():
                app.logger.error(f"FHIR server connection error for patient {patient_id}: {error}")
                return jsonify({
                    'error': 'Unable to connect to the health record system. Please check your connection and try again.',
                    'error_type': 'connection_error',
                    'details': 'Network connectivity issue with external service'
                }), 503
            else:
                app.logger.error(f"FHIR data service error for patient {patient_id}: {error}")
                return jsonify({
                    'error': 'An error occurred while retrieving patient data from the health record system.',
                    'error_type': 'service_error',
                    'details': str(error)
                }), 500
        
        # Explicitly check if the patient data is missing after the call
        if not raw_data or not raw_data.get('patient'):
            app.logger.warning(f"No patient data retrieved for patient {patient_id}")
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
        app.logger.error(f"Error in calculate_risk_api: {str(e)}", exc_info=True)
        if "FHIR server is down" in str(e):
            return jsonify({'error': 'FHIR data service is unavailable.', 'details': str(e)}), 503
        return jsonify({'error': 'An internal server error occurred.'}), 500

@app.route('/api/export-ccd', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
@audit_ephi_access(action='export_ccd_document', resource_type='Patient,Observation,Condition')
def export_ccd_api():
    """
    ONC Compliance: 45 CFR 170.315 (b)(6) - Data Export
    API endpoint to generate and download C-CDA CCD document
    """
    try:
        data = request.get_json()
        
        if not data:
            app.logger.error("No JSON data received in CCD export request")
            return jsonify({'error': 'No data provided in request.'}), 400
        
        # Log received data for debugging
        app.logger.info(f"CCD export request received")
        
        # Get patient data from session
        patient_id = session.get('patient_id', 'N/A')
        
        # Get risk assessment data
        risk_data = data.get('risk_data')
        if not risk_data:
            return jsonify({'error': 'Risk assessment data is required.'}), 400
        
        # Security Issue A: Clinical Data Integrity / Forgery Protection
        # Recalculate score server-side based on inputs to ensure consistency
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
                app.logger.warning(f"SECURITY ADVISORY: Client score ({client_score}) mismatches server calculation ({calculated_score}). Enforcing server calculation.")
                risk_data['total_score'] = calculated_score
                from services.risk_classifier import risk_classifier
                display_info = risk_classifier.get_precise_hbr_display_info(calculated_score)
                risk_data['risk_category'] = display_info['full_label']
            
        except Exception as calc_err:
            app.logger.error(f"Error verifying risk score: {calc_err}")
            
        # Prepare patient demographics
        patient_data = {
            'id': patient_id,
            'name': data.get('patient_name', 'Unknown Patient'),
            'gender': data.get('patient_gender', 'Unknown'),
            'birth_date': data.get('patient_birth_date', '1970-01-01'),
            'age': data.get('patient_age', 'Unknown')
        }
        
        # Generate CCD document
        try:
            ccd_xml = generate_ccd_from_session_data(
                patient_data=patient_data,
                risk_data=risk_data,
                raw_fhir_data={}
            )
        except Exception as ccd_error:
            app.logger.error(f"Error generating CCD document: {str(ccd_error)}")
            return jsonify({'error': 'Failed to generate CCD document', 'details': str(ccd_error)}), 500
        
        # Sanitize patient_id
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
        app.logger.error(f"Error generating CCD: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to generate CCD document.', 'details': str(e)}), 500

@app.route('/api/exchange-code', methods=['POST'])
def exchange_code():
    """API to exchange authorization code for an access token."""
    try:
        data = request.get_json()
        # Log request without sensitive authorization code
        app.logger.info(f"Exchange code request received (code length: {len(data.get('code', '')) if data else 0})")
        code = data.get('code')
        if not code:
            app.logger.error("Authorization code is missing from request")
            return jsonify({"error": "Authorization code is missing."}), 400
        launch_params = session.get('launch_params')
        app.logger.info(f"Launch params from session: {launch_params}")
        if not launch_params:
            app.logger.error("Launch context not found in session")
            return jsonify({"error": "Launch context not found in session."}), 400
        token_url = launch_params['token_url']
        code_verifier = launch_params['code_verifier']
        token_params = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'code_verifier': code_verifier
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
        if CLIENT_SECRET:
            auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
            auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
            headers['Authorization'] = f"Basic {auth_b64}"
            token_params.pop('client_id', None)
        response = requests.post(token_url, data=token_params, headers=headers, timeout=15)
        response.raise_for_status()
        token_response = response.json()
        # Log token response without sensitive data
        safe_token_info = {
            'patient': token_response.get('patient'),
            'scope': token_response.get('scope'),
            'token_type': token_response.get('token_type'),
            'expires_in': token_response.get('expires_in'),
            'has_access_token': bool(token_response.get('access_token')),
            'has_refresh_token': bool(token_response.get('refresh_token'))
        }
        app.logger.info(f"Token exchange successful: {safe_token_info}")
        granted_scopes = token_response.get('scope', 'No scopes returned from EHR')
        app.logger.debug(f"Granted scopes from EHR: {granted_scopes}")
        # --- END DEBUG ---
        session['fhir_data'] = {
            'token': token_response.get('access_token'),
            'patient': token_response.get('patient'),
            'server': launch_params.get('iss'),
            'client_id': CLIENT_ID,
            'token_type': token_response.get('token_type', 'Bearer'),
            'expires_in': token_response.get('expires_in'),
            'scope': token_response.get('scope'),
            'refresh_token': token_response.get('refresh_token')
        }
        if 'patient' in token_response:
            session['patient_id'] = token_response['patient']
        
        # ONC Compliance: Audit successful authentication
        log_user_authentication(
            user_id=session.get('session_id', 'unknown'),
            outcome='success',
            details={
                'patient_id': token_response.get('patient'),
                'scope': token_response.get('scope'),
                'authentication_method': 'SMART_on_FHIR_OAuth2'
            }
        )
        
        return jsonify({"status": "ok", "redirect_url": url_for('main_page')})
    except requests.exceptions.HTTPError as e:
        app.logger.error(f"Token exchange failed: {e.response.status_code} {e.response.text}")
        
        # ONC Compliance: Audit failed authentication
        log_user_authentication(
            user_id=session.get('session_id', 'unknown'),
            outcome='failure',
            details={
                'error': 'token_exchange_failed',
                'status_code': e.response.status_code,
                'authentication_method': 'SMART_on_FHIR_OAuth2'
            }
        )
        
        return jsonify({"error": "Failed to exchange code for token.", "details": e.response.text}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Unexpected error during token exchange: {e}", exc_info=True)
        
        # ONC Compliance: Audit failed authentication
        log_user_authentication(
            user_id=session.get('session_id', 'unknown'),
            outcome='failure',
            details={
                'error': 'unexpected_error',
                'error_message': str(e),
                'authentication_method': 'SMART_on_FHIR_OAuth2'
            }
        )
        
        return jsonify({"error": "An internal server error occurred."}), 500

# --- Frontend Routes ---

@app.route('/')
def index():
    if is_session_valid():
        return redirect(url_for('main_page'))
    return redirect(url_for('standalone_launch_page'))

@app.route('/standalone')
def standalone_launch_page():
    return render_template('standalone_launch.html')

@app.route('/initiate-launch', methods=['POST'])
def initiate_launch():
    iss = request.form.get('iss')
    if not iss:
        return render_error_page("Launch Error", "'iss' (FHIR Server URL) is missing.")
    return redirect(url_for('launch', iss=iss))

@app.route('/docs')
def docs_page():
    """Renders the documentation page."""
    return render_template('docs.html')

@app.route('/launch')
def launch():
    """SMART on FHIR launch sequence."""
    try:
        iss = request.args.get('iss')
        if not iss:
            return render_error_page("Launch Error", "Required 'iss' parameter is missing.")
        
        # Validate ISS URL
        is_valid, error_msg = input_validator.validate_url(iss, allow_localhost=app.config.get('TESTING', False))
        if not is_valid:
            app.logger.warning(f"Invalid ISS URL rejected: {iss[:100]}")
            return render_template('error.html', 
                                 error_title="Launch Error", 
                                 error_message=f"Invalid FHIR server URL: {error_msg}"), 400

        auth_url = None
        token_url = None

        # Standard discovery mechanism.
        smart_config_url = f"{iss.rstrip('/')}/.well-known/smart-configuration"
        try:
            config_response = requests.get(smart_config_url, headers={'Accept': 'application/json'}, timeout=10)
            config_response.raise_for_status()
            smart_config = config_response.json()
            auth_url = smart_config.get('authorization_endpoint')
            token_url = smart_config.get('token_endpoint')
        except (requests.exceptions.RequestException, ValueError) as e:
            app.logger.warning(f"Failed to fetch .well-known/smart-configuration: {e}. Falling back.")
            try:
                fhir_client = client.FHIRClient(settings={'app_id': 'my_app', 'api_base': iss})
                auth_url = fhir_client.server.auth_settings.get('authorize_uri')
                token_url = fhir_client.server.auth_settings.get('token_uri')
            except Exception as conf_e:
                app.logger.error(f"FHIR config error for ISS {iss}: {conf_e}")
                return render_error_page("FHIR Config Error", "Could not retrieve authorization endpoints from the FHIR server. Please verify the server URL and try again.")

        if not auth_url or not token_url:
            app.logger.error(f"Missing auth/token URLs for ISS {iss}")
            return render_error_page("FHIR Config Error", "Could not determine authorization and token endpoints. Please contact your system administrator.")

        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('utf-8')
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).rstrip(b'=').decode('utf-8')
        session['launch_params'] = {'iss': iss, 'token_url': token_url, 'code_verifier': code_verifier}
        
        auth_params = {
            'response_type': 'code',
            'client_id': CLIENT_ID,
            'redirect_uri': REDIRECT_URI,
            'scope': SMART_SCOPES,
            'state': base64.urlsafe_b64encode(os.urandom(16)).rstrip(b'=').decode('utf-8'),
            'aud': iss,
            'launch': request.args.get('launch'),
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        full_auth_url = f"{auth_url}?{requests.compat.urlencode(auth_params)}"
        return redirect(full_auth_url)
    except Exception as e:
        app.logger.error(f"Unexpected error in /launch: {e}", exc_info=True)
        return render_error_page("Launch Error", f"An unexpected error occurred during launch: {e}")

@app.route('/callback')
def callback():
    return render_template('callback.html')

@app.route('/main')
@login_required
@audit_ephi_access(action='view_risk_calculator', resource_type='Patient')
def main_page():
    patient_id = session.get('patient_id', 'N/A')
    return render_template('main.html', patient_id=patient_id)

@app.route('/report-issue')
def report_issue_page():
    """
    ONC Compliance: 45 CFR 170.523 (n) - Complaint Process
    Display the complaint/issue reporting form
    """
    return render_template('report_issue.html')

@app.route('/submit-complaint', methods=['POST'])
def submit_complaint():
    """
    ONC Compliance: 45 CFR 170.523 (n) - Complaint Process
    Handle complaint submission and storage
    """
    import datetime
    import json
    import uuid
    
    # Generate unique reference ID
    reference_id = f"COMP-{datetime.datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    # Collect complaint data
    complaint_data = {
        'reference_id': reference_id,
        'timestamp': datetime.datetime.now().isoformat(),
        'complainant_type': request.form.get('complainant_type', 'unknown'),
        'category': request.form.get('category', 'other'),
        'severity': request.form.get('severity', 'medium'),
        'subject': request.form.get('subject', '').strip(),
        'description': request.form.get('description', '').strip(),
        'contact_email': request.form.get('contact_email', '').strip(),
        'user_agent': request.headers.get('User-Agent', 'unknown'),
        'ip_address': request.remote_addr,
        'session_patient_id': session.get('patient_id', 'N/A')  # Non-PHI context only
    }
    
    # Validate required fields
    if not all([complaint_data['complainant_type'], complaint_data['category'], 
                complaint_data['severity'], complaint_data['subject'], 
                complaint_data['description']]):
        return render_template('report_issue.html', 
                             error="Please fill in all required fields."), 400
    
    # Save complaint to file (JSON Lines format for easy parsing)
    complaints_dir = os.path.join(os.getcwd(), 'instance', 'complaints')
    os.makedirs(complaints_dir, exist_ok=True)
    
    complaints_file = os.path.join(complaints_dir, 'complaints.jsonl')
    
    try:
        with open(complaints_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(complaint_data, ensure_ascii=False) + '\n')
        
        app.logger.info(f"Complaint submitted: {reference_id} - Category: {complaint_data['category']} - Severity: {complaint_data['severity']}")
        
        # Send email notification for critical complaints (if email configured)
        if complaint_data['severity'] == 'critical':
            app.logger.warning(f"CRITICAL COMPLAINT RECEIVED: {reference_id} - {complaint_data['subject']}")
            # TODO: Add email notification here in production
        
        return render_template('report_issue.html', 
                             success=True, 
                             reference_id=reference_id)
    
    except Exception as e:
        app.logger.error(f"Error saving complaint: {e}")
        return render_template('report_issue.html', 
                             error="An error occurred while submitting your complaint. Please try again."), 500

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """
    ONC Compliance: 45 CFR 170.315 (d)(5) - Automatic Access Time-out
    This endpoint is called when a user's session expires due to inactivity
    or when they manually log out.
    """
    # ONC Compliance: Audit logout event
    audit_logger = get_audit_logger()
    user_id = session.get('session_id', 'unknown')
    patient_id = session.get('patient_id')
    logout_reason = 'manual' if request.method == 'GET' else 'timeout_or_manual'
    
    audit_logger.log_event(
        event_type='AUTHENTICATION',
        action='user_logout',
        user_id=user_id,
        patient_id=patient_id,
        outcome='success',
        details={'logout_reason': logout_reason},
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    session.clear()
    
    # If it's a POST request (from JavaScript), return JSON
    if request.method == 'POST':
        return jsonify({'status': 'logged_out', 'message': 'Session cleared successfully'}), 200
    
    # If it's a GET request (direct navigation), redirect to index
    return redirect(url_for('index'))

@app.after_request
def add_security_headers(response: Response):
    """Add security and cache control headers to all responses."""
    # HSTS header for transport security
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Cache control to prevent sensitive data caching
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

# --- Rate Limiting ---
# Initialize Flask-Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://" 
)

# --- Main Execution ---

# Enable security headers with Flask-Talisman
# The CSP allows loading styles/scripts from trusted CDNs.
csp = {
    'default-src': '\'self\'',
    'script-src': [
        '\'self\'',
        'cdn.jsdelivr.net',
        'cdnjs.cloudflare.com',
    ],
    'style-src': [
        '\'self\'',
        'cdn.jsdelivr.net',
        'cdnjs.cloudflare.com',
    ],
    'font-src': ['cdnjs.cloudflare.com', 'cdn.jsdelivr.net'],
    'img-src': ['\'self\'', 'data:'],  # Allow images from self and data URIs
    'connect-src': [
        '\'self\'',
        'cdn.jsdelivr.net',  # Allow source map connections for debugging
        'cdnjs.cloudflare.com'
    ]
}
# Security Issue C: Add nonce support
# Note: We only apply nonce to script-src. Applying it to style-src would disable 'unsafe-inline' 
# which is required for Bootstrap and other inline styles in this legacy app.
Talisman(app, content_security_policy=csp, content_security_policy_nonce_in=['script-src'])

# Initialize CSRF protection
csrf = CSRFProtect()
csrf.init_app(app)

# Exempt specific routes from CSRF protection
csrf.exempt(launch)
csrf.exempt(callback)
csrf.exempt(exchange_code)
# Security Issue B: Remove exemptions for sensitive endpoints
# calculate_risk_api, export_ccd_api, tradeoff_bp are now protected.
csrf.exempt(hooks_bp) # Exempt CDS Hooks blueprint (external services)

# Enable CORS for CDS Hooks endpoints (required for external CDS Hooks clients)
# This allows CDS Hooks Sandbox and EHR systems to call our hooks
CORS(app, resources={
    r"/cds-services/*": {
        "origins": "*",  # Allow all origins for CDS Hooks discovery and invocation
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False
    }
})

# Register blueprints
app.register_blueprint(tradeoff_bp)  # Tradeoff analysis
app.register_blueprint(hooks_bp)  # CDS Hooks

if __name__ == '__main__':
    # R-08 Risk Mitigation: Enhanced production environment checks
    is_production = (
        os.environ.get('FLASK_ENV') == 'production' or 
        os.environ.get('PRODUCTION') == 'true' or
        os.environ.get('GAE_ENV') == 'standard'  # Google App Engine
    )
    
    # Strict production security checks
    if is_production:
        # Ensure debug mode is disabled in production
        if os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1', 't']:
            app.logger.error("SECURITY VIOLATION: Debug mode attempted in production environment!")
            app.logger.error("This is a security risk that could expose sensitive information.")
            raise ValueError("Debug mode is not allowed in production environments.")
        
        # Ensure HTTPS in production
        if not app.config.get('SESSION_COOKIE_SECURE'):
            app.logger.warning("SESSION_COOKIE_SECURE should be True in production with HTTPS")
        
        # Log production startup
        app.logger.info("Starting application in PRODUCTION mode with enhanced security")
        debug_mode = False
    else:
        # Development mode
        debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1', 't']
        if debug_mode:
            app.logger.warning("Running in DEBUG mode - only use in development!")
        
        app.logger.info("Starting application in DEVELOPMENT mode")
    
    # Security: Only bind to all interfaces if explicitly set in production
    # For local development, bind to localhost for better security
    if is_production:
        host = os.environ.get("HOST", "0.0.0.0")  # nosec B104 - Required for cloud deployment
    else:
        host = os.environ.get("HOST", "127.0.0.1")  # Localhost only for development
    
    # Use port 8080 for cloud deployments, but allow override
    port = int(os.environ.get("PORT", 8080))
    
    app.logger.info(f"Server starting on {host}:{port} (debug={debug_mode}, production={is_production})")
    app.run(host=host, port=port, debug=debug_mode)
