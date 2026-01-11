"""
Input Validation Module
Provides validation functions for user inputs to prevent injection attacks
"""

import re
from typing import Optional
from urllib.parse import urlparse

ValidationResult = tuple[bool, Optional[str]]

DANGEROUS_URL_CHARS = frozenset(['<', '>', '"', "'", '`', '\x00', '\r', '\n'])
LOCALHOST_HOSTNAMES = frozenset(['localhost', '127.0.0.1', '0.0.0.0', '::1'])


def _require_string(value: str, field_name: str) -> Optional[str]:
    """Return error message if value is not a non-empty string, None otherwise."""
    if not value or not isinstance(value, str):
        return f"{field_name} is required and must be a string"
    return None


def _is_private_ip(hostname: str) -> bool:
    """Check if hostname is a private IP address."""
    if hostname.startswith('192.168.') or hostname.startswith('10.'):
        return True

    if hostname.startswith('172.'):
        parts = hostname.split('.')
        if len(parts) >= 2:
            try:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return True
            except ValueError:
                pass

    return False


def validate_url(url: str, allow_localhost: bool = False) -> ValidationResult:
    """
    Validate URL format and check for security issues.

    Args:
        url: URL string to validate
        allow_localhost: Whether to allow localhost URLs (for testing)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if error := _require_string(url, "URL"):
        return False, error

    if len(url) > 2048:
        return False, "URL is too long"

    if any(char in url for char in DANGEROUS_URL_CHARS):
        return False, "URL contains invalid characters"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    if parsed.scheme not in ('http', 'https'):
        return False, "URL must use http or https scheme"

    if not parsed.netloc:
        return False, "URL must have a valid hostname"

    if not allow_localhost:
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid hostname"

        if hostname.lower() in LOCALHOST_HOSTNAMES:
            return False, "Localhost URLs are not allowed"

        if _is_private_ip(hostname):
            return False, "Private IP addresses are not allowed"

        if hostname.startswith('169.254.'):
            return False, "Link-local addresses are not allowed"

    return True, None


def validate_patient_id(patient_id: str) -> ValidationResult:
    """
    Validate patient ID format.

    Args:
        patient_id: Patient ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if error := _require_string(patient_id, "Patient ID"):
        return False, error

    if len(patient_id) > 255:
        return False, "Patient ID is too long"

    if not re.match(r'^[a-zA-Z0-9_-]+$', patient_id):
        return False, "Patient ID contains invalid characters"

    return True, None


ALLOWED_FHIR_RESOURCES = frozenset([
    'Patient', 'Observation', 'Condition', 'MedicationRequest',
    'Procedure', 'DiagnosticReport', 'Encounter', 'AllergyIntolerance',
    'Immunization', 'CarePlan', 'Goal', 'DocumentReference'
])


def validate_fhir_resource_type(resource_type: str) -> ValidationResult:
    """
    Validate FHIR resource type.

    Args:
        resource_type: FHIR resource type to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if error := _require_string(resource_type, "Resource type"):
        return False, error

    if resource_type not in ALLOWED_FHIR_RESOURCES:
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

    truncated = input_str[:max_length]

    # Keep printable characters (ord >= 32) plus newline and tab, exclude null byte
    return ''.join(
        char for char in truncated
        if (ord(char) >= 32 or char in '\n\t') and char != '\x00'
    )


def _check_depth(obj: object, max_depth: int, current_depth: int = 0) -> bool:
    """Recursively check if object nesting depth exceeds maximum."""
    if current_depth > max_depth:
        return False

    if isinstance(obj, dict):
        return all(_check_depth(v, max_depth, current_depth + 1) for v in obj.values())

    if isinstance(obj, list):
        return all(_check_depth(item, max_depth, current_depth + 1) for item in obj)

    return True


def validate_json_structure(
    data: dict,
    required_fields: Optional[list[str]] = None,
    max_depth: int = 10
) -> ValidationResult:
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

    if required_fields:
        missing = [field for field in required_fields if field not in data]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"

    if not _check_depth(data, max_depth):
        return False, f"JSON nesting depth exceeds maximum of {max_depth}"

    return True, None


SCOPE_PATTERN = re.compile(
    r'^(patient|user|system)/([A-Z][a-zA-Z]+)\.(read|write|\*)$'
    r'|^(openid|profile|fhirUser|launch(/patient)?|online_access|offline_access)$'
)


def validate_scope(scope: str) -> ValidationResult:
    """
    Validate SMART on FHIR scope.

    Args:
        scope: Scope string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if error := _require_string(scope, "Scope"):
        return False, error

    for s in scope.split():
        if not SCOPE_PATTERN.match(s):
            return False, f"Invalid scope format: {s}"

    return True, None


def validate_code(code: str) -> ValidationResult:
    """
    Validate OAuth authorization code.

    Args:
        code: Authorization code to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if error := _require_string(code, "Authorization code"):
        return False, error

    if len(code) < 10 or len(code) > 512:
        return False, "Authorization code has invalid length"

    if not re.match(r'^[a-zA-Z0-9_\-\.~]+$', code):
        return False, "Authorization code contains invalid characters"

    return True, None


def validate_state(state: str) -> ValidationResult:
    """
    Validate OAuth state parameter.

    Args:
        state: State parameter to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if error := _require_string(state, "State parameter"):
        return False, error

    if len(state) < 10 or len(state) > 512:
        return False, "State parameter has invalid length"

    if not re.match(r'^[a-zA-Z0-9_\-]+$', state):
        return False, "State parameter contains invalid characters"

    return True, None

