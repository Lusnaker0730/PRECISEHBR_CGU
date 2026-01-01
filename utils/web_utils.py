from functools import wraps
from flask import session, request, redirect, url_for, jsonify, render_template, current_app

def is_session_valid():
    required_keys = ['server', 'token', 'client_id']
    fhir_data = session.get('fhir_data')
    return bool(fhir_data and all(key in fhir_data for key in required_keys))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_session_valid():
            current_app.logger.warning(f"Access to '{request.path}' denied. No valid session.")
            if request.path.startswith('/api/'):
                return jsonify({"error": "Authentication required."}), 401
            # Note: We assume the index route is named 'web.index' or just 'index' depending on blueprint setup.
            # Using 'web.index' as default for the new structure.
            try:
                return redirect(url_for('web.index'))
            except Exception:
                # Fallback if blueprint not named 'web'
                return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def render_error_page(title="Error", message="An unexpected error has occurred."):
    current_app.logger.error(f"Rendering error page: {title} - {message}")
    return render_template('error.html', error_title=title, error_message=message), 500
