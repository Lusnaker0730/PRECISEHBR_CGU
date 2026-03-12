"""
Tests for OIDC Token Validator.

Tests security features including:
- Algorithm rejection (none, HS256)
- Signature validation
- Claims verification
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import jwt
import time

from utils.oidc_validator import (
    OIDCValidator,
    OIDCValidationError,
    validate_id_token_safe,
    ALLOWED_ALGORITHMS
)



pytestmark = [
    pytest.mark.requirement("SRS-005"),
    pytest.mark.risk("RISK-005"),
]

class TestOIDCValidatorAlgorithms:
    """Test algorithm security checks."""
    
    def test_rejects_none_algorithm(self):
        """Test that 'none' algorithm is rejected."""
        # Create a token with 'none' algorithm
        payload = {'sub': 'user123', 'iss': 'https://example.com', 'aud': 'client123'}
        none_token = jwt.encode(payload, key='', algorithm='none')
        
        validator = OIDCValidator(
            issuer='https://example.com',
            client_id='client123'
        )
        
        with pytest.raises(OIDCValidationError) as exc_info:
            validator.validate_id_token(none_token)
        
        assert exc_info.value.error_code == 'insecure_algorithm'
        assert "'none'" in exc_info.value.message
    
    def test_rejects_hs256_algorithm(self):
        """Test that HS256 (symmetric) algorithm is rejected."""
        payload = {
            'sub': 'user123',
            'iss': 'https://example.com',
            'aud': 'client123',
            'exp': int(time.time()) + 3600,
            'iat': int(time.time())
        }
        hs256_token = jwt.encode(payload, key='secret', algorithm='HS256')
        
        validator = OIDCValidator(
            issuer='https://example.com',
            client_id='client123'
        )
        
        with pytest.raises(OIDCValidationError) as exc_info:
            validator.validate_id_token(hs256_token)
        
        assert exc_info.value.error_code == 'insecure_algorithm'
        assert 'Symmetric' in exc_info.value.message or 'HS256' in exc_info.value.message
    
    def test_allowed_algorithms_are_asymmetric(self):
        """Test that only asymmetric algorithms are allowed."""
        for alg in ALLOWED_ALGORITHMS:
            assert alg.startswith('RS') or alg.startswith('ES') or alg.startswith('PS')
        
        # Ensure symmetric algorithms are NOT in the list
        assert 'HS256' not in ALLOWED_ALGORITHMS
        assert 'HS384' not in ALLOWED_ALGORITHMS
        assert 'HS512' not in ALLOWED_ALGORITHMS
        assert 'none' not in ALLOWED_ALGORITHMS


class TestOIDCValidatorClaimsValidation:
    """Test claims validation."""
    
    def test_missing_token_raises_error(self):
        """Test that missing token raises appropriate error."""
        validator = OIDCValidator(
            issuer='https://example.com',
            client_id='client123'
        )
        
        with pytest.raises(OIDCValidationError) as exc_info:
            validator.validate_id_token('')
        
        assert exc_info.value.error_code == 'missing_token'
    
    def test_invalid_token_format_raises_error(self):
        """Test that malformed token raises error."""
        validator = OIDCValidator(
            issuer='https://example.com',
            client_id='client123'
        )
        
        with pytest.raises(OIDCValidationError) as exc_info:
            validator.validate_id_token('not.a.valid.token')
        
        assert exc_info.value.error_code == 'invalid_format'


class TestOIDCValidatorJWKSDiscovery:
    """Test JWKS URI discovery."""
    
    def test_discovers_jwks_from_oidc_config(self):
        """Test JWKS URI discovery from .well-known/openid-configuration."""
        validator = OIDCValidator(
            issuer='https://example.com',
            client_id='client123'
        )
        
        with patch('utils.oidc_validator.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'jwks_uri': 'https://example.com/.well-known/jwks.json'
            }
            mock_get.return_value = mock_response
            
            jwks_uri = validator._get_jwks_uri()
            
            assert jwks_uri == 'https://example.com/.well-known/jwks.json'
    
    def test_falls_back_to_smart_config(self):
        """Test fallback to SMART configuration."""
        validator = OIDCValidator(
            issuer='https://example.com',
            client_id='client123'
        )
        
        with patch('utils.oidc_validator.requests.get') as mock_get:
            def side_effect(url, **kwargs):
                mock_response = Mock()
                if 'openid-configuration' in url:
                    mock_response.status_code = 404
                    return mock_response
                elif 'smart-configuration' in url:
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        'jwks_uri': 'https://example.com/smart-jwks.json'
                    }
                    return mock_response
                return Mock(status_code=404)
            
            mock_get.side_effect = side_effect
            
            jwks_uri = validator._get_jwks_uri()
            
            assert jwks_uri == 'https://example.com/smart-jwks.json'


class TestValidateIdTokenSafe:
    """Test the safe validation wrapper function."""
    
    def test_returns_none_for_empty_token(self):
        """Test that empty token returns None without error."""
        claims, error = validate_id_token_safe(
            id_token='',
            issuer='https://example.com',
            client_id='client123'
        )
        
        assert claims is None
        assert error is None  # No error for empty token
    
    def test_returns_none_for_none_token(self):
        """Test that None token returns None without error."""
        claims, error = validate_id_token_safe(
            id_token=None,
            issuer='https://example.com',
            client_id='client123'
        )
        
        assert claims is None
        assert error is None
    
    def test_returns_error_for_invalid_token(self):
        """Test that invalid token returns error message."""
        claims, error = validate_id_token_safe(
            id_token='invalid.token.here',
            issuer='https://example.com',
            client_id='client123'
        )
        
        assert claims is None
        assert error is not None


class TestFhirUserExtraction:
    """Test fhirUser claim extraction."""
    
    def test_extracts_fhir_user_from_claims(self):
        """Test extraction of fhirUser claim."""
        validator = OIDCValidator(
            issuer='https://example.com',
            client_id='client123'
        )
        
        claims = {
            'sub': 'user123',
            'fhirUser': 'Practitioner/456',
            'name': 'Dr. Smith'
        }
        
        fhir_user = validator.extract_fhir_user(claims)
        
        assert fhir_user == 'Practitioner/456'
    
    def test_returns_none_when_fhir_user_missing(self):
        """Test that missing fhirUser returns None."""
        validator = OIDCValidator(
            issuer='https://example.com',
            client_id='client123'
        )
        
        claims = {
            'sub': 'user123',
            'name': 'Dr. Smith'
        }
        
        fhir_user = validator.extract_fhir_user(claims)
        
        assert fhir_user is None
    
    def test_get_user_identity(self):
        """Test full user identity extraction."""
        validator = OIDCValidator(
            issuer='https://example.com',
            client_id='client123'
        )
        
        claims = {
            'sub': 'user123',
            'fhirUser': 'Practitioner/456',
            'name': 'Dr. Smith',
            'email': 'dr.smith@example.com',
            'amr': ['mfa', 'pwd']
        }
        
        identity = validator.get_user_identity(claims)
        
        assert identity['subject'] == 'user123'
        assert identity['fhir_user'] == 'Practitioner/456'
        assert identity['name'] == 'Dr. Smith'
        assert identity['email'] == 'dr.smith@example.com'
        assert 'mfa' in identity['auth_methods']
