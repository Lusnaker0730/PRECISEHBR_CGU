import time
from functools import wraps
from flask import session, request, redirect, url_for, jsonify, render_template, current_app


def is_session_valid():
    required_keys = ['server', 'token', 'client_id']
    fhir_data = session.get('fhir_data')
    return bool(fhir_data and all(key in fhir_data for key in required_keys))


def is_token_expired():
    """Check if the access token has expired based on stored expiry time."""
    fhir_data = session.get('fhir_data')
    if not fhir_data:
        return True
    expires_at = fhir_data.get('token_expires_at')
    if expires_at is None:
        return False  # Unknown expiry — assume valid
    return time.time() >= expires_at


def try_server_side_refresh():
    """Attempt to refresh the token server-side.

    Returns True if refresh succeeded and session was updated,
    False if refresh is not possible or failed.
    """
    import requests as http_requests
    from services.app_config import Config
    from utils.input_validator import validate_url

    fhir_data = session.get('fhir_data')
    if not fhir_data:
        return False

    refresh_token = fhir_data.get('refresh_token')
    if not refresh_token:
        return False

    # Enforce minimum interval
    last_refresh = session.get('last_refresh_timestamp')
    now = time.time()
    if last_refresh and (now - last_refresh) < 30:
        return False

    # Get token endpoint
    smart_config = session.get('smart_config', {})
    token_url = smart_config.get('token_endpoint')
    if not token_url:
        launch_params = session.get('launch_params', {})
        token_url = launch_params.get('token_url')
    if not token_url:
        return False

    is_valid, _ = validate_url(token_url)
    if not is_valid:
        return False

    client_id = fhir_data.get('client_id', Config.CLIENT_ID)
    token_params = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    if Config.CLIENT_SECRET:
        import base64
        credentials = base64.b64encode(
            f"{client_id}:{Config.CLIENT_SECRET}".encode()
        ).decode()
        headers['Authorization'] = f'Basic {credentials}'
        token_params.pop('client_id', None)

    try:
        response = http_requests.post(token_url, data=token_params, headers=headers, timeout=10)
        response.raise_for_status()
        token_response = response.json()
    except Exception:
        current_app.logger.warning("Server-side token refresh failed during pre-check")
        return False

    new_access_token = token_response.get('access_token')
    if not new_access_token:
        return False

    new_expires_in = token_response.get('expires_in')
    fhir_data['token'] = new_access_token
    fhir_data['expires_in'] = new_expires_in
    fhir_data['token_expires_at'] = (time.time() + int(new_expires_in)) if new_expires_in else None
    fhir_data['token_type'] = token_response.get('token_type', 'Bearer')

    new_refresh_token = token_response.get('refresh_token')
    if new_refresh_token:
        fhir_data['refresh_token'] = new_refresh_token

    session['fhir_data'] = fhir_data
    session['last_refresh_timestamp'] = time.time()
    session.modified = True

    current_app.logger.info("Server-side token refresh succeeded (pre-check)")
    return True


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_session_valid():
            current_app.logger.warning(f"Access to '{request.path}' denied. No valid session.")
            if request.path.startswith('/api/'):
                return jsonify({
                    "error": "Authentication required.",
                    "requires_reauth": True
                }), 401
            try:
                return redirect(url_for('web.index'))
            except Exception:
                return redirect(url_for('index'))

        # P3: If token is expired, attempt server-side refresh before proceeding
        if is_token_expired():
            current_app.logger.info(f"Token expired for '{request.path}', attempting refresh")
            if not try_server_side_refresh():
                current_app.logger.warning(f"Token refresh failed for '{request.path}'")
                if request.path.startswith('/api/'):
                    return jsonify({
                        "error": "Your session has expired. Please re-launch the application from your EHR.",
                        "error_type": "auth_expired",
                        "requires_reauth": True
                    }), 401
                try:
                    return redirect(url_for('web.index'))
                except Exception:
                    return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function


def render_error_page(title="Error", message="An unexpected error has occurred."):
    current_app.logger.error(f"Rendering error page: {title} - {message}")
    return render_template('error.html', error_title=title, error_message=message), 500
