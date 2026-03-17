import base64
import hashlib
import os
import time

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
import requests
from fhirclient import client

from extensions import csrf, limiter
from services.app_config import Config
from services.audit_logger import get_audit_logger, log_user_authentication
from utils.input_validator import validate_url
from utils.oidc_validator import validate_id_token_safe
from utils.web_utils import render_error_page


AUTH_METHOD = 'SMART_on_FHIR_OAuth2'
PKCE_MAX_AGE_SECONDS = 600
REFRESH_TOKEN_MIN_INTERVAL_SECONDS = 30


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


def _apply_basic_auth(headers, client_id, client_secret):
    """Add HTTP Basic Auth header for confidential client authentication."""
    auth_str = f"{client_id}:{client_secret}"
    auth_b64 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    headers['Authorization'] = f"Basic {auth_b64}"


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

    Attempts .well-known/smart-configuration first, then falls back to metadata (Conformance/CapabilityStatement) parsing.

    Returns:
        Tuple of (auth_url, token_url) or (None, None) on failure
    """
    # 1. Try .well-known/smart-configuration (Standard for R4)
    smart_config_url = f"{iss.rstrip('/')}/.well-known/smart-configuration"

    MAX_METADATA_RESPONSE_SIZE = 1_000_000  # H-03

    try:
        response = requests.get(smart_config_url, headers={'Accept': 'application/json'}, timeout=10)
        response.raise_for_status()
        if hasattr(response, 'content') and hasattr(response.content, '__len__') and len(response.content) > MAX_METADATA_RESPONSE_SIZE:
            raise ValueError("SMART configuration response exceeds size limit")
        config = response.json()
        return config.get('authorization_endpoint'), config.get('token_endpoint')
    except (requests.exceptions.RequestException, ValueError) as e:
        current_app.logger.warning(f"Failed to fetch .well-known/smart-configuration: {e}. Falling back to metadata.")

    # 2. Try fetching metadata directly (Robust fallback for DSTU2/R4)
    metadata_url = f"{iss.rstrip('/')}/metadata"
    try:
        response = requests.get(metadata_url, headers={'Accept': 'application/json, application/fhir+json'}, timeout=15)
        response.raise_for_status()
        if hasattr(response, 'content') and hasattr(response.content, '__len__') and len(response.content) > MAX_METADATA_RESPONSE_SIZE:
            raise ValueError("Metadata response exceeds size limit")
        metadata = response.json()
        
        # Parse conformance/capability statement for oauth-uris extension
        # Structure: rest[0].security.extension[] where url is ...oauth-uris
        # Inside extension: extension[url=authorize].valueUri, extension[url=token].valueUri
        
        rest = metadata.get('rest', [])
        if not rest:
            raise ValueError("No 'rest' field in metadata")
            
        security = rest[0].get('security', {})
        extensions = security.get('extension', [])
        
        auth_url = None
        token_url = None
        
        SMART_OAUTH_URI = "http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris"
        
        for ext in extensions:
            if ext.get('url') == SMART_OAUTH_URI:
                for sub_ext in ext.get('extension', []):
                    if sub_ext.get('url') == 'authorize':
                        auth_url = sub_ext.get('valueUri')
                    elif sub_ext.get('url') == 'token':
                        token_url = sub_ext.get('valueUri')
                break
        
        if auth_url and token_url:
            current_app.logger.info(f"Discovered OAuth URLs from metadata: Auth={auth_url}, Token={token_url}")
            return auth_url, token_url
            
        current_app.logger.warning("Metadata fetched but SMART OAuth extensions not found.")
        
    except Exception as e:
        current_app.logger.error(f"Manual metadata fetch failed for ISS {iss}: {e}")

    # 3. Last resort: Try fhirclient library (though it often fails on DSTU2 auth_settings)
    try:
        fhir_client = client.FHIRClient(settings={'app_id': 'my_app', 'api_base': iss})
        auth_settings = fhir_client.server.auth_settings
        return auth_settings.get('authorize_uri'), auth_settings.get('token_uri')
    except Exception as e:
        current_app.logger.error(f"fhirclient fallback failed for ISS {iss}: {e}")
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

    # H-02: Validate both auth_url and token_url BEFORE use/storage (SSRF prevention)
    is_valid_auth, auth_url_err = validate_url(auth_url, allow_localhost=current_app.config.get('TESTING', False))
    if not is_valid_auth:
        current_app.logger.error(f"Invalid auth_url discovered: {auth_url_err}")
        return render_error_page("FHIR Config Error", "Invalid authorization endpoint URL discovered.")

    is_valid_token, url_err = validate_url(token_url, allow_localhost=current_app.config.get('TESTING', False))
    if not is_valid_token:
        current_app.logger.error(f"Invalid token_url discovered: {url_err}")
        return render_error_page("FHIR Config Error", "Invalid token endpoint URL discovered.")

    session['state'] = oauth_state
    session['code_verifier'] = code_verifier
    session['code_challenge'] = code_challenge
    session['pkce_timestamp'] = time.time()  # H-01
    session['smart_config'] = {'token_endpoint': token_url}

    client_id = Config.get_client_id_by_iss(iss)

    session['launch_params'] = {
        'iss': iss,
        'token_url': token_url,
        'code_verifier': code_verifier,
        'state': oauth_state,
        'client_id': client_id
    }

    auth_params = {
        'response_type': 'code',
        'client_id': client_id,
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
    client_id = launch_params.get('client_id', Config.CLIENT_ID)
    
    token_params = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': Config.REDIRECT_URI,
        'client_id': client_id,
        'code_verifier': launch_params['code_verifier']
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    # Confidential clients: use Basic Auth and remove client_id from body per spec
    # Public clients (no secret): client_id stays in body
    if Config.CLIENT_SECRET:
        _apply_basic_auth(headers, client_id, Config.CLIENT_SECRET)
        token_params.pop('client_id', None)

    return token_params, headers


def store_token_response(token_response, launch_params):
    """Store the token response in the session with id_token validation."""
    issuer = launch_params.get('iss')
    client_id = launch_params.get('client_id', Config.CLIENT_ID)
    
    # Validate id_token if present (OIDC security enhancement)
    id_token = token_response.get('id_token')
    user_identity = None
    
    if id_token:
        # Decode id_token without verification to get actual issuer
        # Cerner uses different issuers for FHIR server vs OAuth/OIDC server
        validation_issuer = issuer  # Default to FHIR server issuer
        try:
            import jwt as jwt_debug
            unverified_claims = jwt_debug.decode(id_token, options={"verify_signature": False})
            actual_issuer = unverified_claims.get('iss')
            
            if actual_issuer and actual_issuer != issuer:
                # Check if this is a Cerner authorization server issuer
                # Format: https://authorization.cerner.com/tenants/{tenant-id}/
                if 'authorization.cerner.com' in actual_issuer:
                    # Extract tenant ID from both URLs to verify they match
                    import re
                    fhir_tenant_match = re.search(r'/r4/([a-f0-9-]+)', issuer)
                    auth_tenant_match = re.search(r'/tenants/([a-f0-9-]+)', actual_issuer)
                    
                    if fhir_tenant_match and auth_tenant_match:
                        fhir_tenant = fhir_tenant_match.group(1)
                        auth_tenant = auth_tenant_match.group(1)
                        
                        if fhir_tenant == auth_tenant:
                            # Tenant IDs match - use actual issuer for validation
                            # Keep the exact issuer string (including trailing slash) for JWT validation
                            validation_issuer = actual_issuer
                            current_app.logger.info(
                                f"Using Cerner OAuth issuer for id_token validation: {validation_issuer}"
                            )
                        else:
                            current_app.logger.warning(
                                f"Tenant ID mismatch - FHIR: {fhir_tenant}, Auth: {auth_tenant}"
                            )
                else:
                    current_app.logger.info(
                        f"id_token issuer differs from FHIR server - "
                        f"Expected: {issuer}, Actual: {actual_issuer}"
                    )
        except Exception as debug_err:
            current_app.logger.debug(f"Could not decode id_token for issuer check: {debug_err}")
        
        claims, validation_error = validate_id_token_safe(
            id_token=id_token,
            issuer=validation_issuer,
            client_id=client_id
        )
        
        if validation_error:
            skip_validation = os.environ.get('SKIP_ID_TOKEN_VALIDATION', '').lower() in ('true', '1', 'yes')
            is_production = (
                os.environ.get('FLASK_ENV') == 'production'
                or os.environ.get('PRODUCTION') == 'true'
                or os.environ.get('GAE_ENV') == 'standard'
            )
            if skip_validation and is_production:
                # SECURITY: Block skip in production — fail-closed
                current_app.logger.error(
                    "SKIP_ID_TOKEN_VALIDATION is set in a PRODUCTION environment. "
                    "This is a security violation — ignoring the skip flag."
                )
                skip_validation = False
            if skip_validation:
                # Sandbox/testing mode: log warning but allow authentication to proceed
                current_app.logger.warning(
                    f"id_token validation failed: {validation_error}. "
                    "SKIP_ID_TOKEN_VALIDATION is enabled — proceeding without id_token verification. "
                    "DO NOT use this setting in production."
                )
            else:
                # C-01: Fail-closed - reject when id_token validation fails
                current_app.logger.error(
                    f"id_token validation failed: {validation_error}. "
                    "Rejecting authentication per fail-closed policy."
                )
                log_auth_failure('id_token_validation_failed', {'error': validation_error})
                raise ValueError(f"id_token validation failed: {validation_error}")
        elif claims:
            user_identity = {
                'subject': claims.get('sub'),
                'fhir_user': claims.get('fhirUser'),
                'name': claims.get('name'),
                'email': claims.get('email'),
                'auth_methods': claims.get('amr', []),
            }
            current_app.logger.info(
                f"id_token validated successfully. fhirUser: {claims.get('fhirUser')}"
            )
    
    expires_in = token_response.get('expires_in')
    session['fhir_data'] = {
        'token': token_response.get('access_token'),
        'patient': token_response.get('patient'),
        'server': issuer,
        'client_id': client_id,
        'token_type': token_response.get('token_type', 'Bearer'),
        'expires_in': expires_in,
        'token_expires_at': (time.time() + int(expires_in)) if expires_in else None,
        'scope': token_response.get('scope'),
        'refresh_token': token_response.get('refresh_token')
    }

    if 'patient' in token_response:
        session['patient_id'] = token_response['patient']
    
    # Store validated user identity if available
    if user_identity:
        session['user_identity'] = user_identity
        # Also set fhir_user for easy access
        if user_identity.get('fhir_user'):
            session['fhir_user'] = user_identity['fhir_user']

    safe_token_info = {
        'patient': token_response.get('patient'),
        'scope': token_response.get('scope'),
        'token_type': token_response.get('token_type'),
        'expires_in': token_response.get('expires_in'),
        'has_access_token': bool(token_response.get('access_token')),
        'has_refresh_token': bool(token_response.get('refresh_token')),
        'has_id_token': bool(id_token),
        'id_token_validated': user_identity is not None,
        'fhir_user': user_identity.get('fhir_user') if user_identity else None
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

    # H-01: Check PKCE parameter expiration
    pkce_ts = session.get('pkce_timestamp')
    if pkce_ts and (time.time() - pkce_ts) > PKCE_MAX_AGE_SECONDS:
        current_app.logger.error("PKCE parameters expired")
        log_auth_failure('pkce_expired')
        return jsonify({"error": "Authorization session expired. Please try again."}), 400

    token_params, headers = build_token_request(data['code'], launch_params)

    # Validate token_url to prevent SSRF via session tampering
    token_url = launch_params.get('token_url')
    is_valid, url_error = validate_url(token_url)
    if not is_valid:
        current_app.logger.error(f"Invalid token_url in session: {url_error}")
        return jsonify({"error": "Invalid token endpoint URL."}), 400

    try:
        response = requests.post(token_url, data=token_params, headers=headers, timeout=15)
        response.raise_for_status()
        token_response = response.json()
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(f"Token exchange failed: {e.response.status_code} {e.response.text}")
        log_auth_failure('token_exchange_failed', {'status_code': e.response.status_code})
        return jsonify({"error": "Failed to exchange code for token."}), e.response.status_code
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

    # M-06: Session fingerprint for concurrent session protection
    session['session_fingerprint'] = hashlib.sha256(
        f"{request.remote_addr}:{request.headers.get('User-Agent', '')}".encode()
    ).hexdigest()

    return jsonify({"status": "ok", "redirect_url": url_for('web.main_page')})


@auth_bp.route('/api/refresh-token', methods=['POST'])
@csrf.exempt
@limiter.limit("5 per hour")  # C-05: Rate limit refresh token
def refresh_token():
    """Refresh the access token using the refresh token."""
    fhir_data = session.get('fhir_data')

    if not fhir_data:
        current_app.logger.warning("Token refresh attempted without session data")
        return jsonify({"error": "No active session found."}), 401

    current_refresh_token = fhir_data.get('refresh_token')

    if not current_refresh_token:
        current_app.logger.info("Token refresh attempted but no refresh token available")
        return jsonify({"error": "No refresh token available."}), 400

    # C-05: Enforce minimum interval between refresh requests
    last_refresh = session.get('last_refresh_timestamp')
    now = time.time()
    if last_refresh and (now - last_refresh) < REFRESH_TOKEN_MIN_INTERVAL_SECONDS:
        current_app.logger.warning("Token refresh attempted too frequently")
        return jsonify({"error": "Please wait before refreshing again."}), 429
    
    # Get token endpoint from session
    smart_config = session.get('smart_config', {})
    token_url = smart_config.get('token_endpoint')
    
    if not token_url:
        # Try to rediscover from launch params
        launch_params = session.get('launch_params', {})
        token_url = launch_params.get('token_url')
    
    if not token_url:
        current_app.logger.error("Cannot refresh token: no token endpoint in session")
        return jsonify({"error": "Token endpoint not found."}), 400

    # Validate token_url to prevent SSRF via session tampering
    is_valid, url_error = validate_url(token_url)
    if not is_valid:
        current_app.logger.error(f"Invalid token_url in session for refresh: {url_error}")
        return jsonify({"error": "Invalid token endpoint URL."}), 400

    # Build refresh token request
    # Use client_id from original session data if available, otherwise fallback to configured default
    client_id = fhir_data.get('client_id', Config.CLIENT_ID)
    
    token_params = {
        'grant_type': 'refresh_token',
        'refresh_token': current_refresh_token,
        'client_id': client_id,
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    # Confidential clients: use Basic Auth and remove client_id from body
    if Config.CLIENT_SECRET:
        _apply_basic_auth(headers, client_id, Config.CLIENT_SECRET)
        token_params.pop('client_id', None)
    
    try:
        response = requests.post(token_url, data=token_params, headers=headers, timeout=15)
        response.raise_for_status()
        token_response = response.json()
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(f"Token refresh failed: {e.response.status_code}")
        
        # Log security event - refresh token may have been compromised
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type='AUTHENTICATION',
            action='token_refresh_failed',
            user_id=session.get('session_id', 'unknown'),
            patient_id=session.get('patient_id'),
            outcome='failure',
            details={
                'status_code': e.response.status_code,
                'reason': 'http_error'
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # If refresh token is invalid, clear session to force re-authentication
        if e.response.status_code in (400, 401):
            session.clear()
            return jsonify({
                "error": "Session expired. Please re-authenticate.",
                "requires_reauth": True
            }), 401
        
        return jsonify({"error": "Failed to refresh token."}), e.response.status_code
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error during token refresh: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500
    
    # Implement Token Rotation: update with new tokens
    new_access_token = token_response.get('access_token')
    new_refresh_token = token_response.get('refresh_token')
    
    if not new_access_token:
        current_app.logger.error("Token refresh response missing access_token")
        return jsonify({"error": "Invalid token response."}), 500
    
    # Update session with new tokens (rotation - old refresh token is now invalid)
    new_expires_in = token_response.get('expires_in')
    fhir_data['token'] = new_access_token
    fhir_data['expires_in'] = new_expires_in
    fhir_data['token_expires_at'] = (time.time() + int(new_expires_in)) if new_expires_in else None
    fhir_data['token_type'] = token_response.get('token_type', 'Bearer')
    
    # Rotate refresh token if a new one was provided
    if new_refresh_token:
        fhir_data['refresh_token'] = new_refresh_token
        current_app.logger.info("Refresh token rotated successfully")
    else:
        # Some servers don't return a new refresh token
        current_app.logger.info("Token refreshed (no new refresh token provided)")
    
    session['fhir_data'] = fhir_data
    session['last_refresh_timestamp'] = time.time()  # C-05
    session.modified = True

    # Log successful refresh
    audit_logger = get_audit_logger()
    audit_logger.log_event(
        event_type='AUTHENTICATION',
        action='token_refreshed',
        user_id=session.get('session_id', 'unknown'),
        patient_id=session.get('patient_id'),
        outcome='success',
        details={
            'new_expires_in': token_response.get('expires_in'),
            'refresh_token_rotated': bool(new_refresh_token)
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({
        "status": "ok",
        "expires_in": token_response.get('expires_in'),
        "token_type": token_response.get('token_type', 'Bearer')
    })


@auth_bp.route('/api/session-status', methods=['GET'])
@limiter.limit("30 per minute")
def session_status():
    """Return token expiry status for frontend monitoring."""
    fhir_data = session.get('fhir_data')
    if not fhir_data or not fhir_data.get('token'):
        return jsonify({"authenticated": False}), 401

    expires_at = fhir_data.get('token_expires_at')
    has_refresh = bool(fhir_data.get('refresh_token'))

    if expires_at:
        remaining = int(expires_at - time.time())
        return jsonify({
            "authenticated": True,
            "token_remaining_seconds": max(remaining, 0),
            "token_expired": remaining <= 0,
            "has_refresh_token": has_refresh
        })

    return jsonify({
        "authenticated": True,
        "token_remaining_seconds": None,
        "token_expired": False,
        "has_refresh_token": has_refresh
    })


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
