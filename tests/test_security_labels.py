"""
Tests for FHIR Security Labels Handler.

Tests security label extraction, analysis, and filtering.
"""

import pytest

from utils.security_labels import (
    ConfidentialityLevel,
    SecurityLabelResult,
    analyze_resource_security,
    check_resources_security,
    extract_security_labels,
    filter_restricted_fields,
    get_confidentiality_level,
    get_security_summary,
)



pytestmark = [
    pytest.mark.requirement("SRS-006"),
]

class TestExtractSecurityLabels:
    """Test security label extraction from resources."""
    
    def test_extracts_labels_from_meta_security(self):
        """Test extraction of security labels from meta.security."""
        resource = {
            'resourceType': 'Patient',
            'id': '123',
            'meta': {
                'security': [
                    {
                        'system': 'http://terminology.hl7.org/CodeSystem/v3-Confidentiality',
                        'code': 'R',
                        'display': 'Restricted'
                    }
                ]
            }
        }
        
        labels = extract_security_labels(resource)
        
        assert len(labels) == 1
        assert labels[0]['code'] == 'R'
    
    def test_returns_empty_list_for_no_labels(self):
        """Test that missing labels returns empty list."""
        resource = {'resourceType': 'Patient', 'id': '123'}
        
        labels = extract_security_labels(resource)
        
        assert labels == []
    
    def test_handles_none_resource(self):
        """Test that None resource returns empty list."""
        labels = extract_security_labels(None)
        
        assert labels == []


class TestConfidentialityLevel:
    """Test ConfidentialityLevel enum."""
    
    def test_from_code_returns_correct_level(self):
        """Test code to level conversion."""
        assert ConfidentialityLevel.from_code('N') == ConfidentialityLevel.NORMAL
        assert ConfidentialityLevel.from_code('R') == ConfidentialityLevel.RESTRICTED
        assert ConfidentialityLevel.from_code('V') == ConfidentialityLevel.VERY_RESTRICTED
    
    def test_from_code_returns_none_for_invalid(self):
        """Test invalid code returns None."""
        assert ConfidentialityLevel.from_code('X') is None
        assert ConfidentialityLevel.from_code('') is None
    
    def test_requires_elevated_access(self):
        """Test which levels require elevated access."""
        assert ConfidentialityLevel.RESTRICTED.requires_elevated_access() is True
        assert ConfidentialityLevel.VERY_RESTRICTED.requires_elevated_access() is True
        assert ConfidentialityLevel.NORMAL.requires_elevated_access() is False


class TestGetConfidentialityLevel:
    """Test confidentiality level extraction from labels."""
    
    def test_gets_level_from_labels(self):
        """Test extraction of level from security labels."""
        labels = [
            {
                'system': 'http://terminology.hl7.org/CodeSystem/v3-Confidentiality',
                'code': 'R'
            }
        ]
        
        level = get_confidentiality_level(labels)
        
        assert level == ConfidentialityLevel.RESTRICTED
    
    def test_returns_highest_level(self):
        """Test that highest level is returned when multiple present."""
        labels = [
            {'system': 'http://terminology.hl7.org/CodeSystem/v3-Confidentiality', 'code': 'N'},
            {'system': 'http://terminology.hl7.org/CodeSystem/v3-Confidentiality', 'code': 'R'},
        ]
        
        level = get_confidentiality_level(labels)
        
        assert level == ConfidentialityLevel.RESTRICTED
    
    def test_returns_none_for_no_confidentiality(self):
        """Test returns None when no confidentiality labels."""
        labels = [
            {'system': 'http://example.com/other', 'code': 'OTHER'}
        ]
        
        level = get_confidentiality_level(labels)
        
        assert level is None


class TestAnalyzeResourceSecurity:
    """Test resource security analysis."""
    
    def test_detects_restricted_resource(self):
        """Test detection of restricted resource."""
        resource = {
            'resourceType': 'Condition',
            'id': '456',
            'meta': {
                'security': [
                    {
                        'system': 'http://terminology.hl7.org/CodeSystem/v3-Confidentiality',
                        'code': 'R'
                    }
                ]
            }
        }
        
        result = analyze_resource_security(resource)
        
        assert result.is_restricted is True
        assert result.is_very_restricted is False
        assert result.requires_elevated_access is True
        assert result.warning_message is not None
        assert 'RESTRICTED' in result.warning_message
    
    def test_detects_very_restricted_resource(self):
        """Test detection of very restricted resource."""
        resource = {
            'resourceType': 'Observation',
            'id': '789',
            'meta': {
                'security': [
                    {
                        'system': 'http://terminology.hl7.org/CodeSystem/v3-Confidentiality',
                        'code': 'V'
                    }
                ]
            }
        }
        
        result = analyze_resource_security(resource)
        
        assert result.is_very_restricted is True
        assert result.should_mask_in_ui is True
        assert 'VERY RESTRICTED' in result.warning_message
    
    def test_normal_resource_no_restrictions(self):
        """Test that normal resource has no restrictions."""
        resource = {
            'resourceType': 'Patient',
            'id': '123',
            'meta': {
                'security': [
                    {
                        'system': 'http://terminology.hl7.org/CodeSystem/v3-Confidentiality',
                        'code': 'N'
                    }
                ]
            }
        }
        
        result = analyze_resource_security(resource)
        
        assert result.is_restricted is False
        assert result.is_very_restricted is False
        assert result.requires_elevated_access is False
        assert result.warning_message is None


class TestFilterRestrictedFields:
    """Test field filtering for restricted resources."""
    
    def test_masks_fields_for_very_restricted(self):
        """Test that sensitive fields are masked for very restricted resources."""
        resource = {
            'resourceType': 'Observation',
            'id': '123',
            'text': {'div': 'Sensitive narrative'},
            'valueString': 'Sensitive value',
        }
        
        security_result = SecurityLabelResult(
            has_labels=True,
            confidentiality_level=ConfidentialityLevel.VERY_RESTRICTED,
            is_restricted=False,
            is_very_restricted=True,
            requires_elevated_access=True,
            all_labels=[],
            warning_message='Test warning'
        )
        
        filtered = filter_restricted_fields(resource, security_result)
        
        assert '[REDACTED' in filtered['text']
        assert '[REDACTED' in filtered['valueString']
        assert filtered['meta']['_securityFiltered'] is True
    
    def test_no_filtering_for_normal(self):
        """Test that normal resources are not filtered."""
        resource = {
            'resourceType': 'Observation',
            'id': '123',
            'text': {'div': 'Normal narrative'},
        }
        
        security_result = SecurityLabelResult(
            has_labels=True,
            confidentiality_level=ConfidentialityLevel.NORMAL,
            is_restricted=False,
            is_very_restricted=False,
            requires_elevated_access=False,
            all_labels=[],
            warning_message=None
        )
        
        filtered = filter_restricted_fields(resource, security_result)
        
        assert filtered['text'] == {'div': 'Normal narrative'}


class TestGetSecuritySummary:
    """Test security summary generation."""
    
    def test_summarizes_multiple_resources(self):
        """Test summary of multiple resources."""
        resources = [
            {'resourceType': 'Patient', 'id': '1'},
            {
                'resourceType': 'Condition',
                'id': '2',
                'meta': {
                    'security': [
                        {'system': 'http://terminology.hl7.org/CodeSystem/v3-Confidentiality', 'code': 'R'}
                    ]
                }
            },
            {
                'resourceType': 'Observation',
                'id': '3',
                'meta': {
                    'security': [
                        {'system': 'http://terminology.hl7.org/CodeSystem/v3-Confidentiality', 'code': 'V'}
                    ]
                }
            },
        ]
        
        summary = get_security_summary(resources)
        
        assert summary['total_resources'] == 3
        assert summary['restricted_count'] == 1
        assert summary['very_restricted_count'] == 1
        assert summary['requires_elevated_access'] is True
        assert len(summary['warnings']) == 2
