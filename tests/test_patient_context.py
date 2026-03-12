"""
Tests for Patient Context Validator (BOLA Protection).

Tests security features including:
- Patient context validation
- Security violation logging
- Decorator functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, session

from utils.patient_context import (
    validate_patient_context,
    get_authorized_patient_id,
    require_patient_context,
    verify_patient_access,
    PatientContextError
)



pytestmark = [
    pytest.mark.requirement("SRS-006"),
    pytest.mark.risk("RISK-009"),
    pytest.mark.design("SDS-006"),
]

@pytest.fixture
def app():
    """Create a test Flask app."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestGetAuthorizedPatientId:
    """Test authorized patient ID retrieval."""
    
    def test_returns_patient_id_from_session(self, app):
        """Test retrieval from session patient_id."""
        with app.test_request_context():
            session['patient_id'] = 'patient-123'
            
            result = get_authorized_patient_id()
            
            assert result == 'patient-123'
    
    def test_falls_back_to_fhir_data(self, app):
        """Test fallback to fhir_data.patient."""
        with app.test_request_context():
            session['fhir_data'] = {'patient': 'patient-456'}
            
            result = get_authorized_patient_id()
            
            assert result == 'patient-456'
    
    def test_returns_none_when_not_set(self, app):
        """Test returns None when no patient context."""
        with app.test_request_context():
            result = get_authorized_patient_id()
            
            assert result is None


class TestValidatePatientContext:
    """Test patient context validation."""
    
    def test_valid_context_passes(self, app):
        """Test that matching patient ID passes validation."""
        with app.test_request_context():
            session['patient_id'] = 'patient-123'
            
            is_valid, error = validate_patient_context('patient-123')
            
            assert is_valid is True
            assert error is None
    
    def test_mismatched_context_fails(self, app):
        """Test that mismatched patient ID fails validation."""
        with app.test_request_context():
            session['patient_id'] = 'patient-123'
            
            with patch('utils.patient_context.get_audit_logger') as mock_audit:
                mock_logger = Mock()
                mock_audit.return_value = mock_logger
                
                is_valid, error = validate_patient_context('patient-456')
                
                assert is_valid is False
                assert 'not authorized' in error.lower()
                
                # Verify security violation was logged
                mock_logger.log_event.assert_called_once()
                call_kwargs = mock_logger.log_event.call_args.kwargs
                assert call_kwargs['event_type'] == 'SECURITY_VIOLATION'
                assert call_kwargs['action'] == 'patient_context_mismatch'
    
    def test_missing_patient_id_fails(self, app):
        """Test that missing patient ID fails."""
        with app.test_request_context():
            session['patient_id'] = 'patient-123'
            
            is_valid, error = validate_patient_context('')
            
            assert is_valid is False
            assert 'required' in error.lower()
    
    def test_no_authorized_patient_fails(self, app):
        """Test that no authorized patient in session fails."""
        with app.test_request_context():
            # No patient_id in session
            
            is_valid, error = validate_patient_context('patient-123')
            
            assert is_valid is False
            assert 'No patient context' in error
    
    def test_whitespace_normalization(self, app):
        """Test that whitespace is normalized."""
        with app.test_request_context():
            session['patient_id'] = '  patient-123  '
            
            is_valid, error = validate_patient_context('patient-123')
            
            assert is_valid is True


class TestRequirePatientContextDecorator:
    """Test the @require_patient_context decorator."""
    
    def test_passes_with_valid_context(self, app):
        """Test that valid context allows request."""
        @require_patient_context
        def test_route():
            return {'success': True}
        
        with app.test_request_context(
            '/test',
            method='POST',
            json={'patientId': 'patient-123'}
        ):
            session['patient_id'] = 'patient-123'
            
            result = test_route()
            
            assert result == {'success': True}
    
    def test_rejects_invalid_context(self, app):
        """Test that invalid context returns 403."""
        @require_patient_context
        def test_route():
            return {'success': True}
        
        with app.test_request_context(
            '/test',
            method='POST',
            json={'patientId': 'patient-456'}
        ):
            session['patient_id'] = 'patient-123'
            
            with patch('utils.patient_context.get_audit_logger') as mock_audit:
                mock_audit.return_value = Mock()
                
                result, status_code = test_route()
                
                assert status_code == 403
                assert 'error' in result.get_json()
    
    def test_rejects_request_without_patient_id(self, app):
        """M-01: Requests without patient_id are now rejected (strict mode)."""
        @require_patient_context
        def test_route():
            return {'success': True}

        with app.test_request_context(
            '/test',
            method='POST',
            json={'someOtherField': 'value'}
        ):
            result, status_code = test_route()
            assert status_code == 400
            assert 'error' in result.get_json()


class TestVerifyPatientAccess:
    """Test the verify_patient_access function."""
    
    def test_passes_with_valid_access(self, app):
        """Test that valid access doesn't raise."""
        with app.test_request_context():
            session['patient_id'] = 'patient-123'
            
            # Should not raise
            verify_patient_access('patient-123')
    
    def test_raises_on_invalid_access(self, app):
        """Test that invalid access raises PatientContextError."""
        with app.test_request_context():
            session['patient_id'] = 'patient-123'
            
            with patch('utils.patient_context.get_audit_logger') as mock_audit:
                mock_audit.return_value = Mock()
                
                with pytest.raises(PatientContextError) as exc_info:
                    verify_patient_access('patient-456')
                
                assert exc_info.value.authorized_patient == 'patient-123'
                assert exc_info.value.requested_patient == 'patient-456'
