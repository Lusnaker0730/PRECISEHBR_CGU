import base64
import hashlib
import os

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
import requests
from fhirclient import client

from extensions import csrf
from services.app_config import Config
from services.audit_logger import get_audit_logger, log_user_authentication
from utils.input_validator import validate_url
from utils.web_utils import render_error_page


AUTH_METHOD = 'SMART_on_FHIR_OAuth2'


def generate_pkce_parameters():
    """Generate PKCE (Proof Key for Code Exchange) parameters.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('utf-8')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).rstrip(b'=').decode('utf-8')
    return code_verifier, code_challenge


def validate_pkce_parameters(code_verifier, code_challenge):
    """Validate that a code_verifier matches its code_challenge.

    Args:
        code_verifier: The original PKCE code verifier
        code_challenge: The expected code challenge

    Returns:
        True if valid, False otherwise
    """
    if not code_verifier or not code_challenge:
        return False

    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).rstrip(b'=').decode('utf-8')

    return expected_challenge == code_challenge


def generate_oauth_state():
    """Generate a cryptographically secure OAuth state parameter."""
    return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('utf-8')


def log_auth_failure(error_type, details=None):
    """Log an authentication failure with consistent formatting."""
    log_user_authentication(
        user_id=session.get('session_id', 'unknown'),
        outcome='failure',
        details={
            'error': error_type,
            'authentication_method': AUTH_METHOD,
            **(details or {})
        }
    )


auth_bp = Blueprint('auth', __name__)


def get_smart_config(iss):
    """Get SMART configuration from the FHIR server.

    This is an alias for fetch_smart_configuration that returns a dict format
    for backward compatibility with tests.

    Args:
        iss: The FHIR server base URL

    Returns:
        Dict with authorization_endpoint and token_endpoint, or None on failure
    """
    auth_url, token_url = fetch_smart_configuration(iss)
    if auth_url and token_url:
        return {
            'authorization_endpoint': auth_url,
            'token_endpoint': token_url
        }
    return None


def fetch_smart_configuration(iss):
    """Fetch SMART configuration from the FHIR server.

    Attempts .well-known/smart-configuration first, then falls back to FHIRClient discovery.

    Returns:
        Tuple of (auth_url, token_url) or (None, None) on failure
    """
    smart_config_url = f"{iss.rstrip('/')}/.well-known/smart-configuration"

    try:
        response = requests.get(smart_config_url, headers={'Accept': 'application/json'}, timeout=10)
        response.raise_for_status()
        config = response.json()
        return config.get('authorization_endpoint'), config.get('token_endpoint')
    except (requests.exceptions.RequestException, ValueError) as e:
        current_app.logger.warning(f"Failed to fetch .well-known/smart-configuration: {e}. Falling back.")

    try:
        fhir_client = client.FHIRClient(settings={'app_id': 'my_app', 'api_base': iss})
        auth_settings = fhir_client.server.auth_settings
        return auth_settings.get('authorize_uri'), auth_settings.get('token_uri')
    except Exception as e:
        current_app.logger.error(f"FHIR config error for ISS {iss}: {e}")
        return None, None


@auth_bp.route('/launch')
@csrf.exempt
def launch():
    """SMART on FHIR launch sequence."""
    iss = request.args.get('iss')
    if not iss:
        return render_error_page("Launch Error", "Required 'iss' parameter is missing.")

    is_valid, error_msg = validate_url(iss, allow_localhost=current_app.config.get('TESTING', False))
    if not is_valid:
        current_app.logger.warning(f"Invalid ISS URL rejected: {iss[:100]}")
        return render_template('error.html', error_title="Launch Error",
                               error_message=f"Invalid FHIR server URL: {error_msg}"), 400

    smart_config = get_smart_config(iss)
    auth_url = smart_config.get('authorization_endpoint') if smart_config else None
    token_url = smart_config.get('token_endpoint') if smart_config else None

    if not auth_url or not token_url:
        current_app.logger.error(f"Missing auth/token URLs for ISS {iss}")
        return render_error_page("FHIR Config Error",
                                 "Could not determine authorization and token endpoints. "
                                 "Please verify the server URL or contact your system administrator.")

    code_verifier, code_challenge = generate_pkce_parameters()
    oauth_state = generate_oauth_state()

    session['launch_params'] = {
        'iss': iss,
        'token_url': token_url,
        'code_verifier': code_verifier,
        'state': oauth_state
    }

    auth_params = {
        'response_type': 'code',
        'client_id': Config.CLIENT_ID,
        'redirect_uri': Config.REDIRECT_URI,
        'scope': Config.SMART_SCOPES,
        'state': oauth_state,
        'aud': iss,
        'launch': request.args.get('launch'),
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }

    full_auth_url = f"{auth_url}?{requests.compat.urlencode(auth_params)}"
    return redirect(full_auth_url)

@auth_bp.route('/callback')
@csrf.exempt
def callback():
    """OAuth callback page that handles the authorization code."""
    return render_template('callback.html')


def validate_exchange_request(data, launch_params):
    """Validate the code exchange request parameters.

    Returns:
        Tuple of (error_response, status_code) or (None, None) if valid
    """
    if not data or not data.get('code'):
        current_app.logger.error("Authorization code is missing from request")
        return jsonify({"error": "Authorization code is missing."}), 400

    if not data.get('state'):
        current_app.logger.error("State parameter is missing from request")
        return jsonify({"error": "State parameter is missing."}), 400

    if not launch_params:
        current_app.logger.error("Launch context not found in session")
        return jsonify({"error": "Launch context not found in session."}), 400

    expected_state = launch_params.get('state')
    if not expected_state or data.get('state') != expected_state:
        current_app.logger.error("State parameter mismatch - possible CSRF attack")
        log_auth_failure('state_mismatch')
        return jsonify({"error": "Invalid state parameter."}), 400

    return None, None


def build_token_request(code, launch_params):
    """Build the token exchange request parameters and headers.

    Returns:
        Tuple of (token_params, headers)
    """
    token_params = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': Config.REDIRECT_URI,
        'client_id': Config.CLIENT_ID,
        'code_verifier': launch_params['code_verifier']
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    if Config.CLIENT_SECRET:
        auth_str = f"{Config.CLIENT_ID}:{Config.CLIENT_SECRET}"
        auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        headers['Authorization'] = f"Basic {auth_b64}"
        token_params.pop('client_id', None)

    return token_params, headers


def store_token_response(token_response, launch_params):
    """Store the token response in the session."""
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

    safe_token_info = {
        'patient': token_response.get('patient'),
        'scope': token_response.get('scope'),
        'token_type': token_response.get('token_type'),
        'expires_in': token_response.get('expires_in'),
        'has_access_token': bool(token_response.get('access_token')),
        'has_refresh_token': bool(token_response.get('refresh_token'))
    }
    current_app.logger.info(f"Token exchange successful: {safe_token_info}")


@auth_bp.route('/api/exchange-code', methods=['POST'])
@csrf.exempt
def exchange_code():
    """Exchange authorization code for an access token."""
    data = request.get_json()
    launch_params = session.get('launch_params')

    code_length = len(data.get('code', '')) if data else 0
    current_app.logger.info(f"Exchange code request received (code length: {code_length})")
    current_app.logger.info(f"Exchange code request - has launch_params: {launch_params is not None}")

    error_response, status_code = validate_exchange_request(data, launch_params)
    if error_response:
        return error_response, status_code

    token_params, headers = build_token_request(data['code'], launch_params)

    try:
        response = requests.post(launch_params['token_url'], data=token_params, headers=headers, timeout=15)
        response.raise_for_status()
        token_response = response.json()
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(f"Token exchange failed: {e.response.status_code} {e.response.text}")
        log_auth_failure('token_exchange_failed', {'status_code': e.response.status_code})
        return jsonify({"error": "Failed to exchange code for token.", "details": e.response.text}), e.response.status_code
    except Exception as e:
        current_app.logger.error(f"Unexpected error during token exchange: {e}", exc_info=True)
        log_auth_failure('unexpected_error', {'error_message': str(e)})
        return jsonify({"error": "An internal server error occurred."}), 500

    store_token_response(token_response, launch_params)

    log_user_authentication(
        user_id=session.get('session_id', 'unknown'),
        outcome='success',
        details={
            'patient_id': token_response.get('patient'),
            'scope': token_response.get('scope'),
            'authentication_method': AUTH_METHOD
        }
    )

    return jsonify({"status": "ok", "redirect_url": url_for('web.main_page')})

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Handle user logout and session cleanup."""
    audit_logger = get_audit_logger()
    is_post_request = request.method == 'POST'

    audit_logger.log_event(
        event_type='AUTHENTICATION',
        action='user_logout',
        user_id=session.get('session_id', 'unknown'),
        patient_id=session.get('patient_id'),
        outcome='success',
        details={'logout_reason': 'timeout_or_manual' if is_post_request else 'manual'},
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    session.clear()

    if is_post_request:
        return jsonify({'status': 'logged_out', 'message': 'Session cleared successfully'}), 200

    return redirect(url_for('web.index'))
