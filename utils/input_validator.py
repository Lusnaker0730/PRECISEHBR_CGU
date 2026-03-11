"""
Input Validation Module
Provides validation functions for user inputs to prevent injection attacks
"""

import ipaddress
import re
import socket
from typing import Optional
from urllib.parse import urlparse

ValidationResult = tuple[bool, Optional[str]]

DANGEROUS_URL_CHARS = frozenset(['<', '>', '"', "'", '`', '\x00', '\r', '\n'])
LOCALHOST_HOSTNAMES = frozenset(['localhost', '127.0.0.1', '0.0.0.0', '::1'])
# Cloud metadata hostnames that must be blocked to prevent SSRF
BLOCKED_HOSTNAMES = frozenset([
    'metadata.google.internal',
    'metadata.goog',
    'instance-data',
])


def _require_string(value: str, field_name: str) -> Optional[str]:
    """Return error message if value is not a non-empty string, None otherwise."""
    if not value or not isinstance(value, str):
        return f"{field_name} is required and must be a string"
    return None


def _is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address is private, loopback, link-local, or otherwise unsafe.

    Uses Python's ipaddress module for robust checking that handles IPv4, IPv6,
    IPv4-mapped IPv6 (e.g., ::ffff:127.0.0.1), and all numeric representations.
    """
    try:
        addr = ipaddress.ip_address(ip_str)
        # Also handle IPv4-mapped IPv6 addresses (e.g., ::ffff:10.0.0.1)
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
            addr = addr.ipv4_mapped
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except ValueError:
        return False


def _resolve_and_check_hostname(hostname: str) -> Optional[str]:
    """Resolve hostname via DNS and check that all resolved IPs are safe.

    Returns an error message if the hostname resolves to a blocked IP, None if safe.
    If DNS resolution fails, returns None (allow) — the real HTTP request will
    also fail, so unresolvable hosts are not an SSRF risk.
    """
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        # Hostname doesn't resolve — not an SSRF risk (request will fail too)
        return None

    for family, _, _, _, sockaddr in results:
        ip = sockaddr[0]
        if _is_ip_blocked(ip):
            return "URL resolves to a blocked network address"

    return None


def validate_url(url: str, allow_localhost: bool = False) -> ValidationResult:
    """
    Validate URL format and check for security issues including SSRF.

    Performs both string-based and DNS-resolution-based checks to prevent
    SSRF bypasses via DNS rebinding, IPv6-mapped addresses, cloud metadata
    hostnames, and non-standard IP representations.

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

    hostname = parsed.hostname
    if not hostname:
        return False, "Invalid hostname"

    if not allow_localhost:
        # Block known cloud metadata hostnames
        hostname_lower = hostname.lower()
        if hostname_lower in LOCALHOST_HOSTNAMES:
            return False, "Localhost URLs are not allowed"

        if hostname_lower in BLOCKED_HOSTNAMES:
            return False, "Blocked hostname"

        # String-based IP check (fast path for obvious private IPs)
        if _is_ip_blocked(hostname):
            return False, "Private or reserved IP addresses are not allowed"

        # DNS resolution check: resolve the hostname and verify all resolved IPs
        dns_error = _resolve_and_check_hostname(hostname)
        if dns_error:
            return False, dns_error

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


# =============================================================================
# FHIR Search Injection Protection
# =============================================================================

# LOINC code format: 12345-6 (numeric with optional check digit)
LOINC_PATTERN = re.compile(r'^[0-9]{1,7}-[0-9]$')

# FHIR date formats: YYYY, YYYY-MM, YYYY-MM-DD, or with time
FHIR_DATE_PATTERN = re.compile(
    r'^([0-9]{4})(-[0-9]{2})?(-[0-9]{2})?(T[0-9]{2}:[0-9]{2}(:[0-9]{2})?(Z|[+-][0-9]{2}:[0-9]{2})?)?$'
)

# Dangerous patterns that could indicate injection attempts
INJECTION_PATTERNS = [
    r'[;\'"\\]',           # SQL-like injection chars
    r'\$\{',               # Template injection
    r'\{\{',               # Template injection
    r'<[a-zA-Z]',          # HTML/XML tags
    r'javascript:',        # XSS
    r'\\x[0-9a-fA-F]{2}',  # Hex encoded chars
    r'%[0-9a-fA-F]{2}',    # URL encoded (except allowed ones)
    r'\.\.',               # Path traversal
    r'[\r\n]',             # CRLF injection
]

# Allowed FHIR search parameter names (whitelist)
ALLOWED_SEARCH_PARAMS = frozenset([
    # Common parameters
    'patient', 'subject', '_id', '_count', '_sort', '_include', '_revinclude',
    # Observation parameters
    'code', 'category', 'date', 'status', 'value-quantity', 'component-code',
    # Condition parameters
    'clinical-status', 'verification-status', 'onset-date', 'recorded-date',
    # MedicationRequest parameters
    'medication', 'status', 'authoredon', 'intent',
    # Consent parameters
    'scope', 'action', 'actor', 'purpose',
    # General parameters
    'identifier', '_lastUpdated', '_profile', '_tag', '_security',
])


def validate_loinc_code(code: str) -> ValidationResult:
    """
    Validate LOINC code format.
    
    LOINC codes follow the pattern: 12345-6 (up to 7 digits, dash, check digit)
    
    Args:
        code: LOINC code to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if error := _require_string(code, "LOINC code"):
        return False, error
    
    if len(code) > 10:
        return False, "LOINC code is too long"
    
    if not LOINC_PATTERN.match(code):
        return False, f"Invalid LOINC code format: {code}"
    
    return True, None


def validate_fhir_date(date_str: str) -> ValidationResult:
    """
    Validate FHIR date/dateTime format.
    
    Valid formats:
    - YYYY
    - YYYY-MM
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SS
    - YYYY-MM-DDTHH:MM:SSZ
    - YYYY-MM-DDTHH:MM:SS+HH:MM
    
    Args:
        date_str: Date string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if error := _require_string(date_str, "Date"):
        return False, error
    
    if len(date_str) > 30:
        return False, "Date string is too long"
    
    # Remove FHIR date prefixes (eq, ne, lt, gt, le, ge, sa, eb, ap)
    cleaned = date_str
    for prefix in ['eq', 'ne', 'lt', 'gt', 'le', 'ge', 'sa', 'eb', 'ap']:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    
    if not FHIR_DATE_PATTERN.match(cleaned):
        return False, f"Invalid FHIR date format: {date_str}"
    
    return True, None


def detect_injection_patterns(value: str) -> Optional[str]:
    """
    Detect potential injection attack patterns in a value.
    
    Args:
        value: String value to check
    
    Returns:
        Description of detected pattern, or None if clean
    """
    if not value or not isinstance(value, str):
        return None
    
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return f"Potential injection pattern detected: {pattern}"
    
    return None


def validate_search_param_name(param_name: str) -> ValidationResult:
    """
    Validate FHIR search parameter name against whitelist.
    
    Args:
        param_name: Search parameter name to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if error := _require_string(param_name, "Parameter name"):
        return False, error
    
    # Allow modifier suffixes (e.g., :exact, :contains, :missing)
    base_name = param_name.split(':')[0]
    
    if base_name not in ALLOWED_SEARCH_PARAMS:
        return False, f"Search parameter '{param_name}' is not in whitelist"
    
    return True, None


def validate_search_param_value(value: str, param_name: str = "value") -> ValidationResult:
    """
    Validate a FHIR search parameter value for injection attacks.
    
    Args:
        value: Parameter value to validate
        param_name: Name of the parameter (for error messages)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value:
        return True, None  # Empty values are allowed
    
    if not isinstance(value, str):
        return False, f"{param_name} must be a string"
    
    if len(value) > 500:
        return False, f"{param_name} is too long"
    
    # Check for injection patterns
    injection = detect_injection_patterns(value)
    if injection:
        return False, f"{param_name}: {injection}"
    
    return True, None


def validate_fhir_search_params(
    params: dict[str, str],
    strict_whitelist: bool = True
) -> ValidationResult:
    """
    Validate a dictionary of FHIR search parameters.
    
    Performs:
    1. Parameter name whitelist validation (if strict_whitelist=True)
    2. Value injection pattern detection
    3. Special validation for known parameter types (LOINC, dates, etc.)
    
    Args:
        params: Dictionary of search parameters
        strict_whitelist: If True, reject unknown parameter names
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(params, dict):
        return False, "Search parameters must be a dictionary"
    
    if len(params) > 20:
        return False, "Too many search parameters"
    
    for name, value in params.items():
        # Validate parameter name
        if strict_whitelist:
            is_valid, error = validate_search_param_name(name)
            if not is_valid:
                return False, error
        
        # Skip None/empty values
        if value is None:
            continue
        
        # Convert to string if necessary
        str_value = str(value)
        
        # Validate value for injection
        is_valid, error = validate_search_param_value(str_value, name)
        if not is_valid:
            return False, error
        
        # Special validation for known types
        if name == 'code' and '|' in str_value:
            # LOINC code with system prefix: http://loinc.org|12345-6
            parts = str_value.split('|')
            if len(parts) == 2:
                code = parts[1]
                if LOINC_PATTERN.match(code):
                    continue  # Valid LOINC format
                # Not LOINC format, but could be valid other code
        
        elif name in ('date', '_lastUpdated', 'onset-date', 'recorded-date', 'authoredon'):
            is_valid, error = validate_fhir_date(str_value)
            if not is_valid:
                return False, error
        
        elif name in ('patient', 'subject') and '/' not in str_value:
            # Validate patient ID format
            is_valid, error = validate_patient_id(str_value)
            if not is_valid:
                return False, error
    
    return True, None


def sanitize_fhir_search_value(value: str, max_length: int = 500) -> str:
    """
    Sanitize a FHIR search parameter value.
    
    Removes dangerous characters while preserving valid FHIR syntax.
    
    Args:
        value: Value to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized value
    """
    if not value or not isinstance(value, str):
        return ""
    
    # Truncate to max length
    sanitized = value[:max_length]
    
    # Allow FHIR-specific characters: alphanumeric, pipe, colon, dash, dot, slash
    # Remove other potentially dangerous characters
    sanitized = re.sub(r'[^\w|:.\-/,=~\s]', '', sanitized)
    
    # Remove any remaining injection patterns
    sanitized = re.sub(r'[\r\n]', '', sanitized)
    
    return sanitized.strip()
