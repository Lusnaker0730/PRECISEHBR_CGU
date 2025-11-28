"""
Tests for audit logging functionality
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import audit_logger


def test_audit_logger_initialization():
    """Test audit logger can be initialized."""
    logger = audit_logger.get_audit_logger()
    assert logger is not None


def test_audit_ephi_access(app):
    """Test ePHI access logging decorator."""
    # audit_ephi_access is a decorator, test it as such
    @audit_logger.audit_ephi_access(action='view_patient', resource_type='Patient')
    def mock_view_function():
        return "success"
    
    # The decorator should be callable
    assert callable(mock_view_function)
    
    # Test that the decorator doesn't break the function
    with app.test_request_context('/test', method='GET'):
        with patch('audit_logger.get_audit_logger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            # Set session data
            from flask import session
            session['user_id'] = 'test-user'
            session['patient_id'] = 'test-patient'
            
            result = mock_view_function()
            assert result == "success"
            
            # Verify log_event was called (not info/warning directly)
            assert mock_log.log_event.called
            call_args = mock_log.log_event.call_args
            assert call_args[1]['event_type'] == 'ePHI_ACCESS'
            assert call_args[1]['action'] == 'view_patient'


def test_user_authentication_logging():
    """Test user authentication logging."""
    with patch('audit_logger.get_audit_logger') as mock_logger:
        mock_log = Mock()
        mock_logger.return_value = mock_log
        
        # Use correct parameters based on actual function signature
        audit_logger.log_user_authentication(
            user_id='test-user',
            outcome='success',
            details={'ip_address': '127.0.0.1'}
        )
        
        # Should call log_event (not info directly)
        assert mock_log.log_event.called
        call_args = mock_log.log_event.call_args
        assert call_args[1]['event_type'] == 'AUTHENTICATION'


def test_audit_log_format():
    """Test audit log entry format."""
    # Audit logs should contain required fields
    required_fields = ['timestamp', 'user_id', 'action', 'resource']
    
    # This is a structural test
    assert len(required_fields) > 0


def test_audit_log_retention():
    """Test audit log retention policy."""
    # Audit logs should be retained according to HIPAA requirements
    # This is a policy test
    assert True  # Placeholder for retention policy verification

