"""
Tests for MFA (Multi-Factor Authentication) Validator.

Tests security features including:
- MFA status detection from amr claims
- require_mfa decorator behavior
- Session integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, session

from utils.mfa_validator import (
    MFA_METHODS,
    PASSWORD_METHODS,
    check_mfa_status,
    is_mfa_authenticated,
    get_mfa_summary,
    require_mfa,
    get_auth_methods_from_session,
)



pytestmark = [
    pytest.mark.requirement("SRS-005"),
]

class TestMFAMethodsConstants:
    """Test MFA method constants are correctly defined."""
    
    def test_mfa_methods_contains_standard_methods(self):
        """Test that standard MFA methods are defined."""
        standard_methods = ['mfa', 'otp', 'sms', 'hwk', 'fpt']
        for method in standard_methods:
            assert method in MFA_METHODS
    
    def test_password_methods_defined(self):
        """Test that password methods are defined."""
        assert 'pwd' in PASSWORD_METHODS
        assert 'user' in PASSWORD_METHODS
    
    def test_mfa_and_password_methods_are_disjoint(self):
        """Test that MFA and password methods don't overlap."""
        overlap = MFA_METHODS & PASSWORD_METHODS
        assert len(overlap) == 0


class TestCheckMFAStatus:
    """Test MFA status checking."""
    
    def test_returns_has_mfa_true_for_mfa_method(self):
        """Test detection of MFA when 'mfa' is in auth methods."""
        result = check_mfa_status(['pwd', 'mfa'])
        
        assert result['has_mfa'] is True
        assert 'mfa' in result['mfa_methods']
    
    def test_returns_has_mfa_true_for_otp(self):
        """Test detection of MFA when OTP is used."""
        result = check_mfa_status(['pwd', 'otp'])
        
        assert result['has_mfa'] is True
        assert 'otp' in result['mfa_methods']
    
    def test_returns_has_mfa_true_for_hardware_key(self):
        """Test detection of MFA when hardware key is used."""
        result = check_mfa_status(['pwd', 'hwk'])
        
        assert result['has_mfa'] is True
        assert 'hwk' in result['mfa_methods']
    
    def test_returns_has_mfa_false_for_password_only(self):
        """Test that password-only auth returns no MFA."""
        result = check_mfa_status(['pwd'])
        
        assert result['has_mfa'] is False
        assert result['requires_password_only'] is True
    
    def test_returns_unknown_status_for_empty_methods(self):
        """Test that empty auth methods returns unknown status."""
        result = check_mfa_status([])
        
        assert result['has_mfa'] is False
        assert result['unknown_status'] is True
    
    def test_returns_all_mfa_methods_used(self):
        """Test that all MFA methods are returned."""
        result = check_mfa_status(['pwd', 'otp', 'fpt'])
        
        assert result['has_mfa'] is True
        assert len(result['mfa_methods']) == 2
        assert 'otp' in result['mfa_methods']
        assert 'fpt' in result['mfa_methods']
    
    def test_preserves_all_auth_methods(self):
        """Test that all auth methods are preserved."""
        methods = ['pwd', 'otp', 'custom']
        result = check_mfa_status(methods)
        
        assert result['all_methods'] == methods


class TestIsMFAAuthenticated:
    """Test session-based MFA check."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret'
        app.config['TESTING'] = True
        return app
    
    def test_returns_true_when_mfa_in_session(self, app):
        """Test that MFA is detected from session."""
        with app.test_request_context():
            session['user_identity'] = {'auth_methods': ['pwd', 'mfa']}
            
            assert is_mfa_authenticated() is True
    
    def test_returns_false_when_no_mfa_in_session(self, app):
        """Test that no MFA is detected when only password."""
        with app.test_request_context():
            session['user_identity'] = {'auth_methods': ['pwd']}
            
            assert is_mfa_authenticated() is False
    
    def test_returns_false_when_no_session(self, app):
        """Test that no MFA when no session data."""
        with app.test_request_context():
            assert is_mfa_authenticated() is False


class TestRequireMFADecorator:
    """Test the require_mfa decorator."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret'
        app.config['TESTING'] = True
        return app
    
    def test_allows_access_with_mfa(self, app):
        """Test that access is allowed when MFA is present."""
        @require_mfa("test_operation")
        def protected_function():
            return {"status": "success"}
        
        with app.test_request_context():
            session['user_identity'] = {'auth_methods': ['pwd', 'mfa']}
            
            with patch('utils.mfa_validator.log_mfa_access'):
                result = protected_function()
                assert result == {"status": "success"}
    
    def test_denies_access_without_mfa(self, app):
        """Test that access is denied when MFA is not present."""
        @require_mfa("test_operation")
        def protected_function():
            return {"status": "success"}
        
        with app.test_request_context():
            session['user_identity'] = {'auth_methods': ['pwd']}
            
            with patch('utils.mfa_validator.log_mfa_access'):
                result, status_code = protected_function()
                
                assert status_code == 403
                data = result.get_json()
                assert data['code'] == 'mfa_required'
    
    def test_denies_access_with_unknown_status(self, app):
        """M-05: Access denied when MFA status unknown (fail-closed)."""
        @require_mfa("test_operation")
        def protected_function():
            return {"status": "success"}

        with app.test_request_context():
            with patch('utils.mfa_validator.log_mfa_access'):
                result, status_code = protected_function()
                assert status_code == 403
                data = result.get_json()
                assert data['code'] == 'mfa_status_unknown'
    
    def test_logs_mfa_access_on_success(self, app):
        """Test that successful MFA access is logged."""
        @require_mfa("test_operation")
        def protected_function():
            return {"status": "success"}
        
        with app.test_request_context():
            session['user_identity'] = {'auth_methods': ['pwd', 'mfa']}
            
            with patch('utils.mfa_validator.log_mfa_access') as mock_log:
                protected_function()
                
                mock_log.assert_called_once()
                args = mock_log.call_args[0]
                assert args[0] == "test_operation"  # operation_name
                assert args[1] is True  # mfa_required
                assert args[2] is True  # mfa_present
                assert args[3] == 'success'  # outcome
    
    def test_logs_mfa_access_on_denial(self, app):
        """Test that denied MFA access is logged."""
        @require_mfa("test_operation")
        def protected_function():
            return {"status": "success"}
        
        with app.test_request_context():
            session['user_identity'] = {'auth_methods': ['pwd']}
            
            with patch('utils.mfa_validator.log_mfa_access') as mock_log:
                protected_function()
                
                mock_log.assert_called_once()
                args = mock_log.call_args[0]
                assert args[3] == 'denied'  # outcome


class TestGetMFASummary:
    """Test MFA summary generation."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret'
        app.config['TESTING'] = True
        return app
    
    def test_returns_mfa_verified_status(self, app):
        """Test summary shows mfa_verified when MFA used."""
        with app.test_request_context():
            session['user_identity'] = {'auth_methods': ['pwd', 'mfa']}
            
            summary = get_mfa_summary()
            
            assert summary['status'] == 'mfa_verified'
            assert summary['has_mfa'] is True
    
    def test_returns_password_only_status(self, app):
        """Test summary shows password_only when only password used."""
        with app.test_request_context():
            session['user_identity'] = {'auth_methods': ['pwd']}
            
            summary = get_mfa_summary()
            
            assert summary['status'] == 'password_only'
            assert summary['has_mfa'] is False
    
    def test_returns_unknown_status(self, app):
        """Test summary shows unknown when no auth methods."""
        with app.test_request_context():
            summary = get_mfa_summary()
            
            assert summary['status'] == 'unknown'
