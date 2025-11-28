"""
Input Validation Module
Provides validation functions for user inputs to prevent injection attacks
"""

import re
from urllib.parse import urlparse
from typing import Optional, Tuple


def validate_url(url: str, allow_localhost: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format and check for security issues.
    
    Args:
        url: URL string to validate
        allow_localhost: Whether to allow localhost URLs (for testing)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL is required and must be a string"
    
    # Check length
    if len(url) > 2048:
        return False, "URL is too long"
    
    # Check for dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '`', '\x00', '\r', '\n']
    if any(char in url for char in dangerous_chars):
        return False, "URL contains invalid characters"
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"
    
    # Check scheme
    if parsed.scheme not in ['http', 'https']:
        return False, "URL must use http or https scheme"
    
    # Check for hostname
    if not parsed.netloc:
        return False, "URL must have a valid hostname"
    
    # Check for internal/private IPs (unless localhost is allowed)
    if not allow_localhost:
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid hostname"
        
        # Block localhost
        if hostname.lower() in ['localhost', '127.0.0.1', '0.0.0.0', '::1']:
            return False, "Localhost URLs are not allowed"
        
        # Block private IP ranges
        if hostname.startswith('192.168.') or hostname.startswith('10.') or hostname.startswith('172.'):
            # More precise check for 172.16-31.x.x
            if hostname.startswith('172.'):
                parts = hostname.split('.')
                if len(parts) >= 2:
                    try:
                        second_octet = int(parts[1])
                        if 16 <= second_octet <= 31:
                            return False, "Private IP addresses are not allowed"
                    except ValueError:
                        pass
            else:
                return False, "Private IP addresses are not allowed"
        
        # Block link-local addresses
        if hostname.startswith('169.254.'):
            return False, "Link-local addresses are not allowed"
    
    return True, None


def validate_patient_id(patient_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate patient ID format.
    
    Args:
        patient_id: Patient ID to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not patient_id or not isinstance(patient_id, str):
        return False, "Patient ID is required and must be a string"
    
    # Check length
    if len(patient_id) > 255:
        return False, "Patient ID is too long"
    
    # Allow alphanumeric, hyphens, and underscores only
    if not re.match(r'^[a-zA-Z0-9_-]+$', patient_id):
        return False, "Patient ID contains invalid characters"
    
    return True, None


def validate_fhir_resource_type(resource_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate FHIR resource type.
    
    Args:
        resource_type: FHIR resource type to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # List of allowed FHIR resource types
    allowed_resources = [
        'Patient', 'Observation', 'Condition', 'MedicationRequest',
        'Procedure', 'DiagnosticReport', 'Encounter', 'AllergyIntolerance',
        'Immunization', 'CarePlan', 'Goal', 'DocumentReference'
    ]
    
    if not resource_type or not isinstance(resource_type, str):
        return False, "Resource type is required and must be a string"
    
    if resource_type not in allowed_resources:
        return False, f"Resource type '{resource_type}' is not allowed"
    
    return True, None


def sanitize_string(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by removing dangerous characters.
    
    Args:
        input_str: String to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    """
    if not input_str or not isinstance(input_str, str):
        return ""
    
    # Truncate to max length
    sanitized = input_str[:max_length]
    
    # Remove control characters except newline and tab
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in ['\n', '\t'])
    
    # Remove null bytes
    sanitized = sanitized.replace('\x00', '')
    
    return sanitized


def validate_json_structure(data: dict, required_fields: list = None, max_depth: int = 10) -> Tuple[bool, Optional[str]]:
    """
    Validate JSON structure.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        max_depth: Maximum nesting depth allowed
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"
    
    # Check required fields
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Check nesting depth
    def check_depth(obj, current_depth=0):
        if current_depth > max_depth:
            return False
        if isinstance(obj, dict):
            return all(check_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            return all(check_depth(item, current_depth + 1) for item in obj)
        return True
    
    if not check_depth(data):
        return False, f"JSON nesting depth exceeds maximum of {max_depth}"
    
    return True, None


def validate_scope(scope: str) -> Tuple[bool, Optional[str]]:
    """
    Validate SMART on FHIR scope.
    
    Args:
        scope: Scope string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not scope or not isinstance(scope, str):
        return False, "Scope is required and must be a string"
    
    # Split scopes
    scopes = scope.split()
    
    # Validate each scope
    valid_scope_pattern = re.compile(r'^(patient|user|system)/([A-Z][a-zA-Z]+)\.(read|write|\*)$|^(openid|profile|fhirUser|launch(/patient)?|online_access|offline_access)$')
    
    for s in scopes:
        if not valid_scope_pattern.match(s):
            return False, f"Invalid scope format: {s}"
    
    return True, None


def validate_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate OAuth authorization code.
    
    Args:
        code: Authorization code to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not code or not isinstance(code, str):
        return False, "Authorization code is required and must be a string"
    
    # Check length (typical OAuth codes are 20-255 characters)
    if len(code) < 10 or len(code) > 512:
        return False, "Authorization code has invalid length"
    
    # Allow alphanumeric, hyphens, underscores, and some special chars
    if not re.match(r'^[a-zA-Z0-9_\-\.~]+$', code):
        return False, "Authorization code contains invalid characters"
    
    return True, None


def validate_state(state: str) -> Tuple[bool, Optional[str]]:
    """
    Validate OAuth state parameter.
    
    Args:
        state: State parameter to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not state or not isinstance(state, str):
        return False, "State parameter is required and must be a string"
    
    # Check length
    if len(state) < 10 or len(state) > 512:
        return False, "State parameter has invalid length"
    
    # Allow alphanumeric, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9_\-]+$', state):
        return False, "State parameter contains invalid characters"
    
    return True, None

