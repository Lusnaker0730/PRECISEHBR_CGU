from flask import Blueprint, request, redirect, url_for, session, jsonify, render_template, current_app
import requests
import base64
import hashlib
import os
from fhirclient import client
import utils.input_validator as input_validator
from services.audit_logger import log_user_authentication, get_audit_logger
from services.app_config import Config, get_secret
from utils.web_utils import render_error_page
from extensions import csrf

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/launch')
@csrf.exempt
def launch():
    """SMART on FHIR launch sequence."""
    try:
        iss = request.args.get('iss')
        if not iss:
            return render_error_page("Launch Error", "Required 'iss' parameter is missing.")
        
        # Validate ISS URL
        is_valid, error_msg = input_validator.validate_url(iss, allow_localhost=current_app.config.get('TESTING', False))
        if not is_valid:
            current_app.logger.warning(f"Invalid ISS URL rejected: {iss[:100]}")
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
            current_app.logger.warning(f"Failed to fetch .well-known/smart-configuration: {e}. Falling back.")
            try:
                fhir_client = client.FHIRClient(settings={'app_id': 'my_app', 'api_base': iss})
                auth_url = fhir_client.server.auth_settings.get('authorize_uri')
                token_url = fhir_client.server.auth_settings.get('token_uri')
            except Exception as conf_e:
                current_app.logger.error(f"FHIR config error for ISS {iss}: {conf_e}")
                return render_error_page("FHIR Config Error", "Could not retrieve authorization endpoints from the FHIR server. Please verify the server URL and try again.")

        if not auth_url or not token_url:
            current_app.logger.error(f"Missing auth/token URLs for ISS {iss}")
            return render_error_page("FHIR Config Error", "Could not determine authorization and token endpoints. Please contact your system administrator.")

        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('utf-8')
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).rstrip(b'=').decode('utf-8')
        session['launch_params'] = {'iss': iss, 'token_url': token_url, 'code_verifier': code_verifier}
        
        auth_params = {
            'response_type': 'code',
            'client_id': Config.CLIENT_ID,
            'redirect_uri': Config.REDIRECT_URI,
            'scope': Config.SMART_SCOPES,
            'state': base64.urlsafe_b64encode(os.urandom(16)).rstrip(b'=').decode('utf-8'),
            'aud': iss,
            'launch': request.args.get('launch'),
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        full_auth_url = f"{auth_url}?{requests.compat.urlencode(auth_params)}"
        return redirect(full_auth_url)
    except Exception as e:
        current_app.logger.error(f"Unexpected error in /launch: {e}", exc_info=True)
        return render_error_page("Launch Error", f"An unexpected error occurred during launch: {e}")

@auth_bp.route('/callback')
@csrf.exempt
def callback():
    return render_template('callback.html')

@auth_bp.route('/api/exchange-code', methods=['POST'])
@csrf.exempt
def exchange_code():
    """API to exchange authorization code for an access token."""
    try:
        data = request.get_json()
        current_app.logger.info(f"Exchange code request received (code length: {len(data.get('code', '')) if data else 0})")
        code = data.get('code')
        if not code:
            current_app.logger.error("Authorization code is missing from request")
            return jsonify({"error": "Authorization code is missing."}), 400
        launch_params = session.get('launch_params')
        current_app.logger.info(f"Launch params from session: {launch_params}")
        if not launch_params:
            current_app.logger.error("Launch context not found in session")
            return jsonify({"error": "Launch context not found in session."}), 400
        token_url = launch_params['token_url']
        code_verifier = launch_params['code_verifier']
        token_params = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': Config.REDIRECT_URI,
            'client_id': Config.CLIENT_ID,
            'code_verifier': code_verifier
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
        if Config.CLIENT_SECRET:
            auth_str = f"{Config.CLIENT_ID}:{Config.CLIENT_SECRET}"
            auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
            headers['Authorization'] = f"Basic {auth_b64}"
            token_params.pop('client_id', None)
        response = requests.post(token_url, data=token_params, headers=headers, timeout=15)
        response.raise_for_status()
        token_response = response.json()
        
        safe_token_info = {
            'patient': token_response.get('patient'),
            'scope': token_response.get('scope'),
            'token_type': token_response.get('token_type'),
            'expires_in': token_response.get('expires_in'),
            'has_access_token': bool(token_response.get('access_token')),
            'has_refresh_token': bool(token_response.get('refresh_token'))
        }
        current_app.logger.info(f"Token exchange successful: {safe_token_info}")
        
        session['fhir_data'] = {
            'token': token_response.get('access_token'),
            'patient': token_response.get('patient'),
            'server': launch_params.get('iss'),
            'client_id': Config.CLIENT_ID,
            'token_type': token_response.get('token_type', 'Bearer'),
            'expires_in': token_response.get('expires_in'),
            'scope': token_response.get('scope'),
            'refresh_token': token_response.get('refresh_token')
        }
        if 'patient' in token_response:
            session['patient_id'] = token_response['patient']
        
        log_user_authentication(
            user_id=session.get('session_id', 'unknown'),
            outcome='success',
            details={
                'patient_id': token_response.get('patient'),
                'scope': token_response.get('scope'),
                'authentication_method': 'SMART_on_FHIR_OAuth2'
            }
        )
        
        return jsonify({"status": "ok", "redirect_url": url_for('web.main_page')})
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(f"Token exchange failed: {e.response.status_code} {e.response.text}")
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
        current_app.logger.error(f"Unexpected error during token exchange: {e}", exc_info=True)
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

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Manual logout."""
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
    
    if request.method == 'POST':
        return jsonify({'status': 'logged_out', 'message': 'Session cleared successfully'}), 200
    
    return redirect(url_for('web.index'))
