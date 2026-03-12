"""
Consent Resource Service

Provides functionality to query and process FHIR Consent resources
for privacy compliance. Implements privacy controls per FHIR standard.

Features:
- Query patient consent status
- Filter resources based on consent permissions
- Support for consent categories and actors
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConsentStatus(Enum):
    """FHIR Consent status values."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ENTERED_IN_ERROR = "entered-in-error"
    NOT_FOUND = "not-found"


class ConsentProvision(Enum):
    """Consent provision types."""
    PERMIT = "permit"
    DENY = "deny"


@dataclass
class ConsentResult:
    """Result of consent check."""
    status: ConsentStatus
    has_active_consent: bool
    permitted_resources: list[str]
    denied_resources: list[str]
    provision_type: Optional[ConsentProvision]
    consent_id: Optional[str]
    details: dict[str, Any]


# Resource types that typically require consent checks
CONSENT_SENSITIVE_RESOURCES = frozenset([
    'Observation',
    'Condition',
    'MedicationRequest',
    'DiagnosticReport',
    'Procedure',
    'ImagingStudy',
    'DocumentReference',
])


class ConsentService:
    """
    Service for handling FHIR Consent resources.
    
    Provides methods to check patient consent before accessing
    sensitive health data.
    """
    
    def __init__(self, smart_client=None):
        """
        Initialize Consent Service.
        
        Args:
            smart_client: SMART on FHIR client instance
        """
        self.smart = smart_client
    
    def set_client(self, smart_client):
        """Set the SMART client after initialization."""
        self.smart = smart_client
    
    def check_patient_consent(
        self,
        patient_id: str,
        resource_types: Optional[list[str]] = None
    ) -> ConsentResult:
        """
        Check if patient has active consent for data access.
        
        Args:
            patient_id: FHIR Patient ID
            resource_types: Optional list of resource types to check
        
        Returns:
            ConsentResult with consent status and permissions
        """
        if not self.smart:
            logger.warning("SMART client not configured for consent check")
            return self._default_permit_result()
        
        try:
            from fhirclient.models import consent
            
            # Query for active consents for this patient
            # Note: Consent is not part of TWCDI CapabilityStatement.
            # This query may fail on strictly TWCDI-compliant servers;
            # the except block handles graceful degradation.
            search_params = {
                'patient': patient_id,
                'status': 'active',
            }
            
            result = consent.Consent.where(search_params).perform(self.smart.server)
            
            if not result.entry:
                logger.info(f"No active consents found for patient {patient_id}")
                return self._no_consent_result(patient_id)
            
            # Process consent resources
            return self._process_consent_entries(result.entry, resource_types)
            
        except ImportError:
            logger.warning("fhirclient Consent model not available")
            return self._default_permit_result()
        except Exception as e:
            logger.error(f"Error checking consent for patient {patient_id}: {e}")
            return self._error_result(str(e))
    
    def _process_consent_entries(
        self,
        entries: list,
        resource_types: Optional[list[str]] = None
    ) -> ConsentResult:
        """
        Process consent bundle entries.
        
        Args:
            entries: Bundle entries containing Consent resources
            resource_types: Resource types to check
        
        Returns:
            ConsentResult based on consent provisions
        """
        permitted = []
        denied = []
        consent_id = None
        provision_type = ConsentProvision.PERMIT
        
        for entry in entries:
            consent_resource = entry.resource
            consent_id = consent_resource.id
            
            # Check provision if present
            if hasattr(consent_resource, 'provision') and consent_resource.provision:
                provision = consent_resource.provision
                
                # Get provision type
                if hasattr(provision, 'type') and provision.type:
                    if provision.type == 'deny':
                        provision_type = ConsentProvision.DENY
                
                # Check for specific data restrictions
                if hasattr(provision, 'data') and provision.data:
                    for data_item in provision.data:
                        if hasattr(data_item, 'reference') and data_item.reference:
                            ref = data_item.reference.reference
                            if provision_type == ConsentProvision.DENY:
                                denied.append(ref)
                            else:
                                permitted.append(ref)
        
        # If no specific restrictions, permit all requested resources
        if not permitted and not denied:
            permitted = list(resource_types) if resource_types else []
        
        return ConsentResult(
            status=ConsentStatus.ACTIVE,
            has_active_consent=True,
            permitted_resources=permitted,
            denied_resources=denied,
            provision_type=provision_type,
            consent_id=consent_id,
            details={'entries_processed': len(entries)}
        )
    
    def _default_permit_result(self) -> ConsentResult:
        """C-02: Default DENY when consent cannot be checked."""
        logger.warning("Consent check unavailable - defaulting to DENY")
        return ConsentResult(
            status=ConsentStatus.INACTIVE,
            has_active_consent=False,
            permitted_resources=[],
            denied_resources=list(CONSENT_SENSITIVE_RESOURCES),
            provision_type=ConsentProvision.DENY,
            consent_id=None,
            details={'default': True, 'reason': 'Client not configured - deny by default'}
        )
    
    def _no_consent_result(self, patient_id: str) -> ConsentResult:
        """Return result when no consent is found."""
        return ConsentResult(
            status=ConsentStatus.NOT_FOUND,
            has_active_consent=False,
            permitted_resources=[],
            denied_resources=[],
            provision_type=None,
            consent_id=None,
            details={'patient_id': patient_id, 'message': 'No active consent found'}
        )
    
    def _error_result(self, error: str) -> ConsentResult:
        """Return result for error conditions."""
        return ConsentResult(
            status=ConsentStatus.INACTIVE,
            has_active_consent=False,
            permitted_resources=[],
            denied_resources=[],
            provision_type=None,
            consent_id=None,
            details={'error': error}
        )
    
    def filter_resources_by_consent(
        self,
        resources: list[dict],
        consent_result: ConsentResult
    ) -> list[dict]:
        """
        Filter resources based on consent permissions.
        
        Args:
            resources: List of FHIR resources
            consent_result: Result from consent check
        
        Returns:
            Filtered list of permitted resources
        """
        if not consent_result.has_active_consent:
            logger.warning("No active consent, returning empty resource list")
            return []
        
        if consent_result.provision_type == ConsentProvision.DENY:
            # Deny by default, only return permitted
            return [
                r for r in resources
                if self._resource_type(r) in consent_result.permitted_resources
            ]
        else:
            # Permit by default, exclude denied
            return [
                r for r in resources
                if self._resource_type(r) not in consent_result.denied_resources
            ]
    
    def _resource_type(self, resource: dict) -> str:
        """Extract resource type from FHIR resource."""
        return resource.get('resourceType', '')
    
    def is_resource_permitted(
        self,
        resource_type: str,
        consent_result: ConsentResult
    ) -> bool:
        """
        Check if a specific resource type is permitted.
        
        Args:
            resource_type: FHIR resource type
            consent_result: Result from consent check
        
        Returns:
            True if resource access is permitted
        """
        if not consent_result.has_active_consent:
            return False
        
        if resource_type in consent_result.denied_resources:
            return False
        
        if consent_result.provision_type == ConsentProvision.DENY:
            return resource_type in consent_result.permitted_resources
        
        return True


def check_consent_before_access(
    smart_client,
    patient_id: str,
    resource_types: Optional[list[str]] = None
) -> ConsentResult:
    """
    Convenience function to check consent before accessing patient data.
    
    Args:
        smart_client: SMART on FHIR client
        patient_id: Patient ID
        resource_types: Optional list of resource types
    
    Returns:
        ConsentResult
    """
    service = ConsentService(smart_client)
    return service.check_patient_consent(patient_id, resource_types)


def log_consent_access(
    patient_id: str,
    consent_result: ConsentResult,
    accessed_resources: list[str]
) -> None:
    """
    Log consent-based access to audit trail.
    
    Args:
        patient_id: Patient ID
        consent_result: Consent check result
        accessed_resources: Resources that were accessed
    """
    try:
        from services.audit_logger import get_audit_logger
        
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type='CONSENT',
            action='data_access',
            user_id=None,
            patient_id=patient_id,
            outcome='success' if consent_result.has_active_consent else 'denied',
            details={
                'consent_status': consent_result.status.value,
                'consent_id': consent_result.consent_id,
                'accessed_resources': accessed_resources,
                'permitted': consent_result.permitted_resources,
                'denied': consent_result.denied_resources,
            }
        )
    except Exception as e:
        logger.error(f"Failed to log consent access: {e}")
