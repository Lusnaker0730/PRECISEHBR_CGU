"""
FHIR Resource Security Labels Handler

Implements meta.security label handling per SMART on FHIR and TW Core IG
security standards. Checks for Confidentiality codes (N, R, V) and provides
appropriate handling recommendations.

Security Labels:
- N (Normal): Standard confidentiality, normal access
- R (Restricted): Requires elevated privileges  
- V (Very Restricted): Highly sensitive, requires explicit authorization

Reference: HL7 Confidentiality Code System
http://terminology.hl7.org/CodeSystem/v3-Confidentiality
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConfidentialityLevel(Enum):
    """FHIR Confidentiality levels per HL7 v3 Confidentiality."""
    
    UNRESTRICTED = "U"      # Unrestricted access
    LOW = "L"               # Low sensitivity
    NORMAL = "N"            # Normal (default)
    MODERATE = "M"          # Moderate sensitivity  
    RESTRICTED = "R"        # Restricted access
    VERY_RESTRICTED = "V"   # Very restricted
    
    @classmethod
    def from_code(cls, code: str) -> Optional['ConfidentialityLevel']:
        """Get ConfidentialityLevel from code string."""
        for level in cls:
            if level.value == code:
                return level
        return None
    
    def requires_elevated_access(self) -> bool:
        """Check if this level requires elevated access."""
        return self in (ConfidentialityLevel.RESTRICTED, ConfidentialityLevel.VERY_RESTRICTED)
    
    def is_sensitive(self) -> bool:
        """Check if this level indicates sensitive data."""
        return self in (
            ConfidentialityLevel.MODERATE,
            ConfidentialityLevel.RESTRICTED, 
            ConfidentialityLevel.VERY_RESTRICTED
        )


@dataclass
class SecurityLabelResult:
    """Result of security label analysis."""
    
    has_labels: bool
    confidentiality_level: Optional[ConfidentialityLevel]
    is_restricted: bool
    is_very_restricted: bool
    requires_elevated_access: bool
    all_labels: list[dict[str, Any]]
    warning_message: Optional[str]
    
    @property
    def should_mask_in_ui(self) -> bool:
        """Whether the resource should be masked in UI."""
        return self.is_restricted or self.is_very_restricted
    
    @property
    def level_code(self) -> Optional[str]:
        """Get the confidentiality level code."""
        if self.confidentiality_level:
            return self.confidentiality_level.value
        return None


# HL7 Confidentiality CodeSystem URI
CONFIDENTIALITY_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-Confidentiality"

# Alternative system URIs that might be used
ALTERNATIVE_CONFIDENTIALITY_SYSTEMS = [
    "http://hl7.org/fhir/v3/Confidentiality",
    "urn:oid:2.16.840.1.113883.5.25",
]


def extract_security_labels(resource: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract security labels from a FHIR resource's meta.security element.
    
    Args:
        resource: FHIR resource as dictionary
    
    Returns:
        List of security label coding objects
    """
    if not resource:
        return []
    
    meta = resource.get('meta', {})
    security_labels = meta.get('security', [])
    
    return security_labels if isinstance(security_labels, list) else []


def get_confidentiality_level(
    security_labels: list[dict[str, Any]]
) -> Optional[ConfidentialityLevel]:
    """
    Extract the highest confidentiality level from security labels.
    
    Args:
        security_labels: List of security label coding objects
    
    Returns:
        The highest ConfidentialityLevel found, or None
    """
    all_systems = [CONFIDENTIALITY_SYSTEM] + ALTERNATIVE_CONFIDENTIALITY_SYSTEMS
    
    highest_level = None
    level_priority = {
        ConfidentialityLevel.UNRESTRICTED: 0,
        ConfidentialityLevel.LOW: 1,
        ConfidentialityLevel.NORMAL: 2,
        ConfidentialityLevel.MODERATE: 3,
        ConfidentialityLevel.RESTRICTED: 4,
        ConfidentialityLevel.VERY_RESTRICTED: 5,
    }
    
    for label in security_labels:
        system = label.get('system', '')
        code = label.get('code', '')
        
        # Check if this is a confidentiality code
        if system in all_systems or not system:  # Accept codes without system too
            level = ConfidentialityLevel.from_code(code)
            if level:
                current_priority = level_priority.get(level, 0)
                highest_priority = level_priority.get(highest_level, -1)
                
                if current_priority > highest_priority:
                    highest_level = level
    
    return highest_level


def analyze_resource_security(resource: dict[str, Any]) -> SecurityLabelResult:
    """
    Analyze a FHIR resource for security labels and restrictions.
    
    Per TW Core IG and SMART on FHIR security standards:
    - R (Restricted): Requires elevated privileges, UI warning
    - V (Very Restricted): Requires explicit authorization, consider masking
    
    Args:
        resource: FHIR resource as dictionary
    
    Returns:
        SecurityLabelResult with analysis details
    """
    labels = extract_security_labels(resource)
    confidentiality = get_confidentiality_level(labels)
    
    is_restricted = confidentiality == ConfidentialityLevel.RESTRICTED
    is_very_restricted = confidentiality == ConfidentialityLevel.VERY_RESTRICTED
    requires_elevated = is_restricted or is_very_restricted
    
    # Generate warning message for restricted resources
    warning_message = None
    resource_type = resource.get('resourceType', 'Resource')
    resource_id = resource.get('id', 'unknown')
    
    if is_very_restricted:
        warning_message = (
            f"⚠️ VERY RESTRICTED: {resource_type}/{resource_id} contains highly "
            "sensitive data requiring explicit authorization."
        )
        logger.warning(f"Very Restricted resource accessed: {resource_type}/{resource_id}")
    elif is_restricted:
        warning_message = (
            f"⚠️ RESTRICTED: {resource_type}/{resource_id} contains sensitive data "
            "requiring elevated privileges."
        )
        logger.info(f"Restricted resource accessed: {resource_type}/{resource_id}")
    
    return SecurityLabelResult(
        has_labels=len(labels) > 0,
        confidentiality_level=confidentiality,
        is_restricted=is_restricted,
        is_very_restricted=is_very_restricted,
        requires_elevated_access=requires_elevated,
        all_labels=labels,
        warning_message=warning_message
    )


def check_resources_security(
    resources: list[dict[str, Any]]
) -> tuple[list[SecurityLabelResult], list[str]]:
    """
    Check multiple FHIR resources for security labels.
    
    Args:
        resources: List of FHIR resources
    
    Returns:
        Tuple of (list of SecurityLabelResults, list of warning messages)
    """
    results = []
    warnings = []
    
    for resource in resources:
        if not resource:
            continue
            
        result = analyze_resource_security(resource)
        results.append(result)
        
        if result.warning_message:
            warnings.append(result.warning_message)
    
    return results, warnings


def filter_restricted_fields(
    resource: dict[str, Any],
    security_result: SecurityLabelResult,
    fields_to_mask: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Filter/mask sensitive fields in a restricted resource.
    
    This creates a copy of the resource with sensitive fields masked.
    Default fields to consider masking for Very Restricted resources:
    - text (narrative)
    - note (clinical notes)
    - valueString (free text values)
    
    Args:
        resource: FHIR resource dictionary
        security_result: Result from analyze_resource_security
        fields_to_mask: Optional list of field names to mask
    
    Returns:
        Copy of resource with sensitive fields masked (if applicable)
    """
    if not security_result.should_mask_in_ui:
        return resource
    
    # Default sensitive fields for Very Restricted
    if fields_to_mask is None:
        fields_to_mask = ['text', 'note', 'valueString', 'comment']
    
    # Create a shallow copy
    filtered = dict(resource)
    
    for field in fields_to_mask:
        if field in filtered:
            if security_result.is_very_restricted:
                filtered[field] = "[REDACTED - Very Restricted]"
            else:
                filtered[field] = "[REDACTED - Restricted]"
    
    # Add security notice to meta
    if 'meta' not in filtered:
        filtered['meta'] = {}
    filtered['meta']['_securityFiltered'] = True
    filtered['meta']['_securityLevel'] = security_result.level_code
    
    return filtered


def get_security_summary(resources: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Get a summary of security labels across multiple resources.
    
    Args:
        resources: List of FHIR resources
    
    Returns:
        Dictionary with security summary statistics
    """
    results, warnings = check_resources_security(resources)
    
    restricted_count = sum(1 for r in results if r.is_restricted)
    very_restricted_count = sum(1 for r in results if r.is_very_restricted)
    
    return {
        'total_resources': len(resources),
        'resources_with_labels': sum(1 for r in results if r.has_labels),
        'restricted_count': restricted_count,
        'very_restricted_count': very_restricted_count,
        'requires_elevated_access': restricted_count + very_restricted_count > 0,
        'warnings': warnings,
        'highest_level': max(
            (r.confidentiality_level for r in results if r.confidentiality_level),
            key=lambda x: ['U', 'L', 'N', 'M', 'R', 'V'].index(x.value) if x else -1,
            default=None
        )
    }
