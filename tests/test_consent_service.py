"""
Tests for Consent Resource Service.

Tests consent checking, resource filtering, and integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

from services.consent_service import (
    ConsentService,
    ConsentStatus,
    ConsentProvision,
    ConsentResult,
    check_consent_before_access,
    CONSENT_SENSITIVE_RESOURCES,
)



pytestmark = [
    pytest.mark.requirement("SRS-011"),
    pytest.mark.design("SDS-011"),
]

class TestConsentStatus:
    """Test ConsentStatus enum."""
    
    def test_status_values_defined(self):
        """Test that all status values are defined."""
        assert ConsentStatus.ACTIVE.value == "active"
        assert ConsentStatus.INACTIVE.value == "inactive"
        assert ConsentStatus.NOT_FOUND.value == "not-found"
    
    def test_status_enum_members(self):
        """Test that expected status members exist."""
        expected = ['ACTIVE', 'INACTIVE', 'DRAFT', 'ENTERED_IN_ERROR', 'NOT_FOUND']
        for status in expected:
            assert hasattr(ConsentStatus, status)


class TestConsentProvision:
    """Test ConsentProvision enum."""
    
    def test_provision_values(self):
        """Test provision values."""
        assert ConsentProvision.PERMIT.value == "permit"
        assert ConsentProvision.DENY.value == "deny"


class TestConsentResult:
    """Test ConsentResult dataclass."""
    
    def test_create_consent_result(self):
        """Test creating a ConsentResult."""
        result = ConsentResult(
            status=ConsentStatus.ACTIVE,
            has_active_consent=True,
            permitted_resources=['Observation'],
            denied_resources=['Condition'],
            provision_type=ConsentProvision.PERMIT,
            consent_id='consent-123',
            details={'test': True}
        )
        
        assert result.status == ConsentStatus.ACTIVE
        assert result.has_active_consent is True
        assert 'Observation' in result.permitted_resources
        assert 'Condition' in result.denied_resources
        assert result.consent_id == 'consent-123'
    
    def test_consent_result_to_dict(self):
        """Test converting ConsentResult to dict."""
        result = ConsentResult(
            status=ConsentStatus.ACTIVE,
            has_active_consent=True,
            permitted_resources=[],
            denied_resources=[],
            provision_type=ConsentProvision.PERMIT,
            consent_id=None,
            details={}
        )
        
        data = asdict(result)
        assert 'status' in data
        assert 'has_active_consent' in data


class TestConsentService:
    """Test ConsentService class."""
    
    def test_init_without_client(self):
        """Test initialization without SMART client."""
        service = ConsentService()
        assert service.smart is None
    
    def test_init_with_client(self):
        """Test initialization with SMART client."""
        mock_client = Mock()
        service = ConsentService(mock_client)
        assert service.smart is mock_client
    
    def test_set_client(self):
        """Test setting client after initialization."""
        service = ConsentService()
        mock_client = Mock()
        service.set_client(mock_client)
        assert service.smart is mock_client
    
    def test_check_consent_without_client(self):
        """Test consent check when client not configured defaults to DENY (C-02)."""
        service = ConsentService()
        result = service.check_patient_consent('patient-123')

        # C-02: Should return default DENY when client not configured
        assert result.has_active_consent is False
        assert result.details.get('default') is True
    
    def test_check_consent_with_no_results(self):
        """Test consent check when no consent found."""
        import sys
        mock_smart = Mock()
        mock_smart.server = Mock()
        
        service = ConsentService(mock_smart)
        
        # Mock the fhirclient.models.consent module
        mock_consent_module = Mock()
        mock_bundle = Mock()
        mock_bundle.entry = None
        mock_consent_module.Consent.where.return_value.perform.return_value = mock_bundle
        
        with patch.dict(sys.modules, {'fhirclient.models.consent': mock_consent_module}):
            result = service.check_patient_consent('patient-123')
            
            assert result.status == ConsentStatus.NOT_FOUND
            assert result.has_active_consent is False
    
    def test_check_consent_with_active_consent(self):
        """Test consent check with active consent."""
        import sys
        mock_smart = Mock()
        mock_smart.server = Mock()
        
        service = ConsentService(mock_smart)
        
        # Mock consent resource
        mock_consent_resource = Mock()
        mock_consent_resource.id = 'consent-123'
        mock_consent_resource.provision = None
        
        mock_entry = Mock()
        mock_entry.resource = mock_consent_resource
        
        mock_bundle = Mock()
        mock_bundle.entry = [mock_entry]
        
        # Mock the fhirclient.models.consent module
        mock_consent_module = Mock()
        mock_consent_module.Consent.where.return_value.perform.return_value = mock_bundle
        
        with patch.dict(sys.modules, {'fhirclient.models.consent': mock_consent_module}):
            result = service.check_patient_consent('patient-123')
            
            assert result.status == ConsentStatus.ACTIVE
            assert result.has_active_consent is True
            assert result.consent_id == 'consent-123'


class TestConsentFiltering:
    """Test resource filtering based on consent."""
    
    def test_filter_with_active_consent(self):
        """Test filtering with active permit consent."""
        service = ConsentService()
        
        consent_result = ConsentResult(
            status=ConsentStatus.ACTIVE,
            has_active_consent=True,
            permitted_resources=['Observation', 'Condition'],
            denied_resources=['MedicationRequest'],
            provision_type=ConsentProvision.PERMIT,
            consent_id='consent-123',
            details={}
        )
        
        resources = [
            {'resourceType': 'Observation', 'id': 'obs-1'},
            {'resourceType': 'Condition', 'id': 'cond-1'},
            {'resourceType': 'MedicationRequest', 'id': 'med-1'},
        ]
        
        filtered = service.filter_resources_by_consent(resources, consent_result)
        
        # Should exclude denied resources
        assert len(filtered) == 2
        resource_types = [r['resourceType'] for r in filtered]
        assert 'MedicationRequest' not in resource_types
    
    def test_filter_with_no_consent(self):
        """Test filtering with no active consent."""
        service = ConsentService()
        
        consent_result = ConsentResult(
            status=ConsentStatus.NOT_FOUND,
            has_active_consent=False,
            permitted_resources=[],
            denied_resources=[],
            provision_type=None,
            consent_id=None,
            details={}
        )
        
        resources = [
            {'resourceType': 'Observation', 'id': 'obs-1'},
        ]
        
        filtered = service.filter_resources_by_consent(resources, consent_result)
        
        # Should return empty when no consent
        assert len(filtered) == 0
    
    def test_filter_with_deny_provision(self):
        """Test filtering with deny provision type."""
        service = ConsentService()
        
        consent_result = ConsentResult(
            status=ConsentStatus.ACTIVE,
            has_active_consent=True,
            permitted_resources=['Observation'],  # Only Observation permitted
            denied_resources=[],
            provision_type=ConsentProvision.DENY,
            consent_id='consent-123',
            details={}
        )
        
        resources = [
            {'resourceType': 'Observation', 'id': 'obs-1'},
            {'resourceType': 'Condition', 'id': 'cond-1'},
        ]
        
        filtered = service.filter_resources_by_consent(resources, consent_result)
        
        # Should only include explicitly permitted
        assert len(filtered) == 1
        assert filtered[0]['resourceType'] == 'Observation'


class TestIsResourcePermitted:
    """Test individual resource permission checks."""
    
    def test_permitted_resource(self):
        """Test check for permitted resource."""
        service = ConsentService()
        
        consent_result = ConsentResult(
            status=ConsentStatus.ACTIVE,
            has_active_consent=True,
            permitted_resources=['Observation'],
            denied_resources=[],
            provision_type=ConsentProvision.PERMIT,
            consent_id='consent-123',
            details={}
        )
        
        assert service.is_resource_permitted('Observation', consent_result) is True
    
    def test_denied_resource(self):
        """Test check for denied resource."""
        service = ConsentService()
        
        consent_result = ConsentResult(
            status=ConsentStatus.ACTIVE,
            has_active_consent=True,
            permitted_resources=[],
            denied_resources=['Condition'],
            provision_type=ConsentProvision.PERMIT,
            consent_id='consent-123',
            details={}
        )
        
        assert service.is_resource_permitted('Condition', consent_result) is False
    
    def test_no_consent_denies_all(self):
        """Test that no consent denies all resources."""
        service = ConsentService()
        
        consent_result = ConsentResult(
            status=ConsentStatus.NOT_FOUND,
            has_active_consent=False,
            permitted_resources=[],
            denied_resources=[],
            provision_type=None,
            consent_id=None,
            details={}
        )
        
        assert service.is_resource_permitted('Observation', consent_result) is False


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_check_consent_before_access(self):
        """Test convenience function for consent check."""
        mock_smart = Mock()
        mock_smart.server = Mock()
        
        # Without client configured properly, should return default
        with patch('services.consent_service.ConsentService') as MockService:
            mock_instance = Mock()
            mock_instance.check_patient_consent.return_value = ConsentResult(
                status=ConsentStatus.ACTIVE,
                has_active_consent=True,
                permitted_resources=['Observation'],
                denied_resources=[],
                provision_type=ConsentProvision.PERMIT,
                consent_id='consent-123',
                details={}
            )
            MockService.return_value = mock_instance
            
            result = check_consent_before_access(mock_smart, 'patient-123')
            
            assert result.has_active_consent is True


class TestConsentSensitiveResources:
    """Test sensitive resource constants."""
    
    def test_sensitive_resources_defined(self):
        """Test that sensitive resources are defined."""
        assert 'Observation' in CONSENT_SENSITIVE_RESOURCES
        assert 'Condition' in CONSENT_SENSITIVE_RESOURCES
        assert 'MedicationRequest' in CONSENT_SENSITIVE_RESOURCES
    
    def test_patient_not_in_sensitive(self):
        """Test that Patient is not in sensitive list."""
        # Patient resource typically doesn't require consent for basic access
        assert 'Patient' not in CONSENT_SENSITIVE_RESOURCES


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
