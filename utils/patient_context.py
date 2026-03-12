"""
Patient Context Validator

Provides BOLA (Broken Object Level Authorization) protection for FHIR API
endpoints by ensuring requests only access patient data that was authorized
during the OAuth flow.

Security Features:
- Validates requested patient_id matches session-authorized patient
- Logs security violations to audit trail
- Provides decorator for easy route protection
"""

import logging
from functools import wraps
from typing import Callable, Optional

from flask import current_app, jsonify, request, session

from services.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)


class PatientContextError(Exception):
    """Exception raised when patient context validation fails."""
    
    def __init__(self, message: str, authorized_patient: Optional[str] = None, 
                 requested_patient: Optional[str] = None):
        self.message = message
        self.authorized_patient = authorized_patient
        self.requested_patient = requested_patient
        super().__init__(self.message)


def get_authorized_patient_id() -> Optional[str]:
    """
    Get the patient ID authorized during OAuth token exchange.
    
    Returns:
        The authorized patient ID from session, or None if not set
    """
    # Primary location: set during token exchange
    patient_id = session.get('patient_id')
    
    if not patient_id:
        # Fallback: check fhir_data for patient context
        fhir_data = session.get('fhir_data', {})
        patient_id = fhir_data.get('patient')
    
    return patient_id


def validate_patient_context(requested_patient_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate that the requested patient ID matches the authorized patient context.
    
    This is a critical security check to prevent BOLA attacks where an attacker
    might try to access data for a patient they are not authorized to view.
    
    Args:
        requested_patient_id: The patient ID being requested in the API call
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not requested_patient_id:
        return False, "Patient ID is required"
    
    authorized_patient_id = get_authorized_patient_id()
    
    if not authorized_patient_id:
        logger.warning("Patient context validation failed: No authorized patient in session")
        return False, "No patient context found in session. Please re-authenticate."
    
    # Normalize IDs for comparison (handle potential format differences)
    normalized_requested = str(requested_patient_id).strip()
    normalized_authorized = str(authorized_patient_id).strip()
    
    if normalized_requested != normalized_authorized:
        # Log security violation
        _log_context_violation(normalized_requested, normalized_authorized)
        return False, "Access denied: You are not authorized to access this patient's data."
    
    return True, None


def _log_context_violation(requested: str, authorized: str) -> None:
    """Log a patient context violation to the audit trail."""
    audit_logger = get_audit_logger()
    
    # Mask patient IDs in logs for privacy (show first/last chars only)
    def mask_id(patient_id: str) -> str:
        if len(patient_id) <= 4:
            return '***'
        return f"{patient_id[:2]}...{patient_id[-2:]}"
    
    audit_logger.log_event(
        event_type='SECURITY_VIOLATION',
        action='patient_context_mismatch',
        patient_id=authorized,  # The legitimately authorized patient
        user_id=session.get('session_id', 'unknown'),
        outcome='failure',
        details={
            'violation_type': 'BOLA_ATTEMPT',
            'requested_patient': mask_id(requested),
            'authorized_patient': mask_id(authorized),
            'description': 'Attempt to access unauthorized patient data'
        },
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None
    )
    
    logger.warning(
        f"SECURITY: Patient context violation - "
        f"Requested: {mask_id(requested)}, Authorized: {mask_id(authorized)}"
    )


def require_patient_context(f: Callable) -> Callable:
    """
    Decorator to enforce patient context validation on API routes.
    
    Extracts patient_id from request JSON body and validates it against
    the authorized patient context from the OAuth session.
    
    Usage:
        @app.route('/api/patient/<patient_id>')
        @require_patient_context
        def get_patient_data(patient_id):
            # patient_id is guaranteed to match authorized context
            pass
    
    Or for routes that take patient_id in request body:
        @app.route('/api/calculate_risk', methods=['POST'])
        @require_patient_context
        def calculate_risk():
            data = request.get_json()
            patient_id = data.get('patientId')  # Already validated
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get patient ID from various sources
        patient_id = None
        
        # 1. Check URL parameters
        if 'patient_id' in kwargs:
            patient_id = kwargs['patient_id']
        
        # 2. Check request JSON body
        if not patient_id and request.is_json:
            data = request.get_json(silent=True)
            if data:
                patient_id = data.get('patientId') or data.get('patient_id')
        
        # 3. Check query parameters
        if not patient_id:
            patient_id = request.args.get('patient_id') or request.args.get('patientId')
        
        if not patient_id:
            # M-01: Strict mode - require patient_id for decorated endpoints
            current_app.logger.warning("Patient context validation failed: No patient ID in request")
            return jsonify({
                'error': 'Patient ID is required',
                'error_type': 'validation_error'
            }), 400
        
        # Validate patient context
        is_valid, error_message = validate_patient_context(patient_id)
        
        if not is_valid:
            current_app.logger.warning(f"Patient context validation failed: {error_message}")
            return jsonify({
                'error': error_message,
                'error_type': 'authorization_error'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def verify_patient_access(patient_id: str) -> None:
    """
    Verify access to a specific patient ID, raising an exception if denied.
    
    Use this for explicit validation within route handlers when the decorator
    approach is not suitable.
    
    Args:
        patient_id: The patient ID to verify access for
    
    Raises:
        PatientContextError: If access is denied
    
    Example:
        try:
            verify_patient_access(requested_patient_id)
            # Proceed with data access
        except PatientContextError as e:
            return error_response(e.message)
    """
    is_valid, error_message = validate_patient_context(patient_id)
    
    if not is_valid:
        authorized = get_authorized_patient_id()
        raise PatientContextError(
            message=error_message or "Access denied",
            authorized_patient=authorized,
            requested_patient=patient_id
        )
