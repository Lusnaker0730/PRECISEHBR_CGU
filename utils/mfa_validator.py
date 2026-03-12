"""
MFA (Multi-Factor Authentication) Validator

Provides MFA verification based on the 'amr' (Authentication Methods Reference)
claim from OIDC id_tokens, per SMART on FHIR security standards.

Features:
- Check if authentication included MFA methods
- Decorator to require MFA for sensitive operations
- Audit logging of MFA status

Reference: RFC 8176 - Authentication Method Reference Values
"""

import functools
import logging
from typing import Any, Optional

from flask import jsonify, session

logger = logging.getLogger(__name__)


# Standard MFA methods per RFC 8176
# https://www.rfc-editor.org/rfc/rfc8176.html
MFA_METHODS = frozenset([
    'mfa',      # Multiple-factor authentication
    'otp',      # One-time password
    'sms',      # SMS verification
    'tel',      # Telephone verification
    'hwk',      # Hardware key (e.g., YubiKey)
    'swk',      # Software key (e.g., authenticator app)
    'fpt',      # Fingerprint biometric
    'face',     # Facial recognition
    'iris',     # Iris scan
    'retina',   # Retina scan
    'vbm',      # Voice biometric
    'pin',      # PIN (when combined with another factor)
    'geo',      # Geolocation (additional factor)
    'kba',      # Knowledge-based authentication
    'sc',       # Smart card
])

# Single-factor password methods (not MFA)
PASSWORD_METHODS = frozenset([
    'pwd',      # Password
    'user',     # User presence (basic)
])


def get_auth_methods_from_session() -> list[str]:
    """
    Get authentication methods from current session.
    
    Returns:
        List of authentication method strings from session
    """
    user_identity = session.get('user_identity', {})
    return user_identity.get('auth_methods', [])


def check_mfa_status(auth_methods: Optional[list[str]] = None) -> dict[str, Any]:
    """
    Check if authentication included MFA methods.
    
    Args:
        auth_methods: List of amr claim values. If None, reads from session.
    
    Returns:
        Dictionary with MFA status details:
        - has_mfa: Whether MFA was used
        - mfa_methods: List of MFA methods that were used
        - all_methods: All authentication methods used
        - requires_password_only: Whether only password was used
    """
    if auth_methods is None:
        auth_methods = get_auth_methods_from_session()
    
    if not auth_methods:
        return {
            'has_mfa': False,
            'mfa_methods': [],
            'all_methods': [],
            'requires_password_only': False,
            'unknown_status': True,  # No amr claim available
        }
    
    # Find which MFA methods were used
    mfa_methods_used = [m for m in auth_methods if m in MFA_METHODS]
    password_only = all(m in PASSWORD_METHODS for m in auth_methods if m not in MFA_METHODS)
    
    has_mfa = len(mfa_methods_used) > 0 or 'mfa' in auth_methods
    
    return {
        'has_mfa': has_mfa,
        'mfa_methods': mfa_methods_used,
        'all_methods': auth_methods,
        'requires_password_only': password_only and not has_mfa,
        'unknown_status': False,
    }


def is_mfa_authenticated() -> bool:
    """
    Check if current session was authenticated with MFA.
    
    Returns:
        True if MFA was used, False otherwise
    """
    status = check_mfa_status()
    return status.get('has_mfa', False)


def log_mfa_access(
    operation: str,
    mfa_required: bool,
    mfa_present: bool,
    outcome: str
) -> None:
    """
    Log MFA-related access attempt to audit log.
    
    Args:
        operation: Name of the operation attempted
        mfa_required: Whether MFA was required
        mfa_present: Whether MFA was present in session
        outcome: 'success' or 'denied'
    """
    try:
        from services.audit_logger import get_audit_logger
        
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type='AUTHENTICATION',
            action='mfa_check',
            user_id=session.get('session_id', 'unknown'),
            patient_id=session.get('patient_id'),
            outcome=outcome,
            details={
                'operation': operation,
                'mfa_required': mfa_required,
                'mfa_present': mfa_present,
                'auth_methods': get_auth_methods_from_session(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to log MFA access: {e}")


def require_mfa(operation_name: str = "sensitive_operation"):
    """
    Decorator to require MFA for sensitive operations.
    
    Usage:
        @require_mfa("view_sensitive_data")
        def view_sensitive_data():
            ...
    
    Args:
        operation_name: Name of the operation for logging
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            mfa_status = check_mfa_status()
            has_mfa = mfa_status.get('has_mfa', False)
            unknown = mfa_status.get('unknown_status', False)
            
            # M-05: Fail-closed when MFA status unknown
            if unknown:
                logger.error(
                    f"MFA status unknown for operation: {operation_name}. "
                    "Access denied per fail-closed policy."
                )
                log_mfa_access(operation_name, True, False, 'denied')
                return jsonify({
                    'error': 'MFA verification unavailable',
                    'code': 'mfa_status_unknown',
                    'operation': operation_name,
                }), 403
            
            if not has_mfa:
                log_mfa_access(operation_name, True, False, 'denied')
                logger.warning(
                    f"MFA required but not present for operation: {operation_name}"
                )
                return jsonify({
                    'error': 'Multi-factor authentication required',
                    'code': 'mfa_required',
                    'operation': operation_name,
                }), 403
            
            log_mfa_access(operation_name, True, True, 'success')
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_mfa_summary() -> dict[str, Any]:
    """
    Get a summary of MFA status for the current session.
    
    Useful for displaying MFA status in UI or logs.
    
    Returns:
        Dictionary with MFA summary information
    """
    status = check_mfa_status()
    
    # Determine human-readable status
    if status.get('unknown_status'):
        readable_status = 'unknown'
    elif status.get('has_mfa'):
        readable_status = 'mfa_verified'
    elif status.get('requires_password_only'):
        readable_status = 'password_only'
    else:
        readable_status = 'single_factor'
    
    return {
        'status': readable_status,
        'has_mfa': status.get('has_mfa', False),
        'methods_used': status.get('all_methods', []),
        'mfa_methods': status.get('mfa_methods', []),
    }
