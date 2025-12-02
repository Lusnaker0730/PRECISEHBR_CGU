import base64
import hashlib
import logging
import os
import secrets
import uuid
from urllib.parse import urlencode

import jwt
import requests
from flask import (Blueprint, redirect, render_template, request,
                   session, jsonify, url_for)

from config import Config
# ONC Compliance: Audit logging
from audit_logger import log_user_authentication

auth_bp = Blueprint('auth', __name__)

# Get client secret from environment (for confidential clients)
CLIENT_SECRET = os.environ.get('SMART_CLIENT_SECRET')


# --- SMART 2.0 PKCE Support ---

def generate_pkce_parameters():
    """
    Generate PKCE parameters for SMART 2.0 authentication.
    Returns code_verifier and code_challenge according to RFC 7636.
    """
    # Generate code_verifier (43-128 characters from unreserved character set)
    code_verifier = base64.urlsafe_b64encode(
        secrets.token_bytes(32)).decode('utf-8').rstrip('=')

    # Generate code_challenge using SHA256 hash of code_verifier
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(
            code_verifier.encode('utf-8')).digest()).decode('utf-8').rstrip('=')

    return code_verifier, code_challenge


def validate_pkce_parameters(code_verifier, code_challenge):
    """
    Validate PKCE parameters to ensure they match.
    Used for security verification during token exchange.
    """
    if not code_verifier or not code_challenge:
        return False

    # Recreate the challenge from the verifier
    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(
            code_verifier.encode('utf-8')).digest()).decode('utf-8').rstrip('=')

    return expected_challenge == code_challenge

# --- Utility Functions (from original APP.py, moved here for auth context) ---


def get_smart_config(fhir_server_url):
    # This function is tightly coupled with the auth flow.
    # It might be refactored into a more generic `fhir_utils.py` later.
    from urllib.parse import urljoin
    if not fhir_server_url.endswith('/'):
        fhir_server_url += '/'
    try:
        url = urljoin(fhir_server_url, ".well-known/smart-configuration")
        response = requests.get(url, headers={'Accept': 'application/json'}, timeout=10)
        response.raise_for_status()
        config = response.json()
        if 'authorization_endpoint' in config and 'token_endpoint' in config:
            return config
    except requests.exceptions.RequestException as e:
        logging.warning(
            f"Failed to fetch from .well-known: {e}. Falling back to /metadata.")
    try:
        url = urljoin(fhir_server_url, "metadata")
        response = requests.get(url, headers={'Accept': 'application/json'}, timeout=10)
        response.raise_for_status()
        capability_statement = response.json()
        for rest in capability_statement.get('rest', []):
            security = rest.get('security')
            if security:
                for extension in security.get('extension', []):
                    if extension.get('url') == "http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris":
                        auth_uris = {}
                        for ext in extension.get('extension', []):
                            if ext.get('url') == 'authorize':
                                auth_uris['authorization_endpoint'] = ext.get(
                                    'valueUri')
                            elif ext.get('url') == 'token':
                                auth_uris['token_endpoint'] = ext.get(
                                    'valueUri')
                        if 'authorization_endpoint' in auth_uris and 'token_endpoint' in auth_uris:
                            return auth_uris
        return None
    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        logging.error(f"Error fetching/parsing metadata: {e}")
        return None


def render_error_page(
        title=None,
        message=None,
        suggestions=None,
        status_code=500):
    """Renders the unified error page with a custom message."""
    error_info = {
        'title': title or "An Error Occurred",
        'message': message or "We encountered a problem and couldn't complete your request.",
        'suggestions': suggestions or [
            "Please try relaunching the application from your EHR system.",
            "If the problem persists, please contact support."]}
    logging.warning(f"Rendering error page with title: {error_info['title']}")
    return render_template("error.html", error_info=error_info), status_code


# --- Auth Routes ---

@auth_bp.route('/launch')
def launch():
    """
    Entry point for the SMART on FHIR launch.
    """
    iss = request.args.get('iss')
    launch_token = request.args.get('launch')
    if not iss:
        return render_error_page(
            title="Launch Error",
            message="'iss' (issuer) parameter is missing.")

    session['launch_params'] = {'iss': iss, 'launch': launch_token}

    smart_config = get_smart_config(iss)
    if not smart_config:
        return render_error_page(
            title="Configuration Discovery Error",
            message="Could not discover the SMART on FHIR configuration.",
            suggestions=[f"Failed to get config from issuer: {iss}"])

    session['smart_config'] = smart_config
    state = str(uuid.uuid4())
    session['state'] = state

    code_verifier, code_challenge = generate_pkce_parameters()
    session['code_verifier'] = code_verifier
    session['code_challenge'] = code_challenge

    auth_url = smart_config.get('authorization_endpoint')
    if not auth_url:
        return render_error_page(
            title="Configuration Error",
            message="SMART configuration is missing 'authorization_endpoint'.")

    auth_params = {
        "response_type": "code",
        "client_id": Config.CLIENT_ID,
        "redirect_uri": Config.REDIRECT_URI,
        "scope": Config.SCOPES,
        "state": state,
        "aud": iss,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    if launch_token:
        auth_params["launch"] = launch_token

    full_auth_url = f"{auth_url}?{urlencode(auth_params)}"
    return redirect(full_auth_url)


@auth_bp.route('/launch/cerner-sandbox')
def launch_cerner_sandbox():
    """Direct launch for Cerner sandbox testing."""
    # Security: Only allow sandbox endpoint in development/testing environments
    if os.environ.get('GAE_ENV', '').startswith('standard') or os.environ.get('FLASK_ENV') == 'production':
        logging.warning("Sandbox endpoint access attempted in production environment")
        return render_error_page(
            title="Endpoint Disabled",
            message="This testing endpoint is not available in production.",
            status_code=403)
    
    iss = Config.CERNER_SANDBOX_CONFIG['fhir_base']
    session['launch_params'] = {'iss': iss, 'launch': None}
    smart_config = {
        "authorization_endpoint": Config.CERNER_SANDBOX_CONFIG['authorization_endpoint'],
        "token_endpoint": Config.CERNER_SANDBOX_CONFIG['token_endpoint']}
    session['smart_config'] = smart_config
    state = str(uuid.uuid4())
    session['state'] = state
    code_verifier, code_challenge = generate_pkce_parameters()
    session['code_verifier'] = code_verifier
    session['code_challenge'] = code_challenge
    auth_params = {
        "response_type": "code",
        "client_id": Config.CLIENT_ID,
        "redirect_uri": Config.REDIRECT_URI,
        "scope": Config.SCOPES,
        "state": state,
        "aud": iss,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    full_auth_url = (f"{smart_config['authorization_endpoint']}"
                     f"?{urlencode(auth_params)}")
    return redirect(full_auth_url)


@auth_bp.route('/callback')
def callback():
    """Handles the OAuth2 callback."""
    if 'error' in request.args:
        error_type = request.args.get('error')
        error_desc = request.args.get(
            'error_description', 'No description provided.')
        return render_error_page(
            title="Authorization Failed",
            message=(
                "The EHR authorization server returned an error: "
                f"{error_type.replace('_', ' ').title()}"),
            suggestions=[
                "You must grant permission to the application to proceed.",
                f"Error details: {error_desc}"],
            status_code=400)
    if 'code' in request.args:
        return render_template('callback.html')
    return render_error_page(
        title="Invalid Callback",
        message="This endpoint expects an authorization code from your EHR system.")


@auth_bp.route('/api/exchange-code', methods=['POST'])
def exchange_code():
    """
    Receives auth code, exchanges it for a token, and sets up the session.
    """
    data = request.get_json()
    code = data.get('code')
    received_state = data.get('state')

    session_state = session.pop('state', None)
    if not session_state or received_state != session_state:
        return jsonify(
            {"status": "error", "error": "State parameter mismatch."}), 400

    smart_config = session.get('smart_config')
    if not smart_config or 'token_endpoint' not in smart_config:
        return jsonify(
            {"status": "error", "error": "SMART configuration not in session."}), 400

    code_verifier = session.get('code_verifier')
    if not validate_pkce_parameters(code_verifier, session.get('code_challenge')):
        return jsonify(
            {"status": "error", "error": "PKCE parameter validation failed."}), 400

    token_url = smart_config['token_endpoint']
    token_params = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': Config.REDIRECT_URI,
        'client_id': Config.CLIENT_ID,
        'code_verifier': code_verifier
    }
    
    # Build headers with required Content-Type
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Support confidential clients with client_secret
    if CLIENT_SECRET:
        auth_str = f"{Config.CLIENT_ID}:{CLIENT_SECRET}"
        auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        headers['Authorization'] = f"Basic {auth_b64}"
        # Remove client_id from params when using Basic auth
        token_params.pop('client_id', None)

    try:
        response = requests.post(
            token_url,
            data=token_params,
            headers=headers,
            timeout=15)
        response.raise_for_status()
        token_response = response.json()

        fhir_data = {
            'token': token_response.get('access_token'),
            'patient': token_response.get('patient'),
            'server': session.get('launch_params', {}).get('iss'),
            'client_id': Config.CLIENT_ID,
            'token_type': token_response.get('token_type', 'Bearer'),
            'expires_in': token_response.get('expires_in'),
            'scope': token_response.get('scope'),
            'refresh_token': token_response.get('refresh_token')
        }
        session['fhir_data'] = fhir_data
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

        return jsonify({
            "status": "ok",
            "redirect_url": url_for('views.main_page')
        })

    except requests.exceptions.HTTPError as e:
        logging.error(
            (f"Token exchange failed. Status: {e.response.status_code}, "
             f"Body: {e.response.text}"))
        
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
        
        return jsonify(
            {"error": "Failed to exchange authorization code for token.", "details": e.response.text}), 500
