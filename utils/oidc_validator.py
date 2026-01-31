"""
OIDC Token Validator

Provides secure validation of OpenID Connect id_tokens for SMART on FHIR
applications. Implements security requirements from:
- SMART App Launch 2.0
- OAuth 2.0 Security Best Current Practice

Features:
- RS256/ES256 signature validation (rejects HS256 and none)
- JWT claims verification (iss, aud, exp, iat)
- JWKS caching for performance
- fhirUser claim extraction
"""

import logging
import time
from functools import lru_cache
from typing import Any, Optional
from urllib.parse import urljoin

import jwt
import requests
from jwt import PyJWKClient, PyJWKClientError

logger = logging.getLogger(__name__)

# Allowed signing algorithms (asymmetric only for security)
ALLOWED_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]

# Cache JWKS for 1 hour (3600 seconds)
JWKS_CACHE_TTL = 3600


class OIDCValidationError(Exception):
    """Exception raised when OIDC token validation fails."""
    
    def __init__(self, message: str, error_code: str = "validation_error"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class OIDCValidator:
    """
    Validates OpenID Connect id_tokens per SMART on FHIR security standards.
    
    Security Features:
    - Only accepts asymmetric algorithms (RS256, ES256, etc.)
    - Rejects 'none' algorithm and symmetric algorithms (HS256)
    - Validates issuer, audience, and expiration
    - Extracts and verifies fhirUser claim
    """
    
    def __init__(self, issuer: str, client_id: str, clock_skew_seconds: int = 30):
        """
        Initialize OIDC validator.
        
        Args:
            issuer: Expected token issuer (FHIR server base URL)
            client_id: OAuth client ID (expected audience)
            clock_skew_seconds: Allowed clock skew for expiration checks
        """
        # Keep original issuer for JWT validation (requires exact match)
        self.issuer = issuer
        # Stripped version for URL building (JWKS endpoint discovery)
        self._issuer_base = issuer.rstrip('/')
        self.client_id = client_id
        self.clock_skew_seconds = clock_skew_seconds
        self._jwks_client: Optional[PyJWKClient] = None
        self._jwks_cache_time: float = 0
    
    def _get_jwks_uri(self) -> str:
        """
        Discover JWKS URI from OIDC configuration.
        
        Returns:
            JWKS endpoint URL
        
        Raises:
            OIDCValidationError: If JWKS URI cannot be discovered
        """
        # Try .well-known/openid-configuration first
        oidc_config_url = f"{self._issuer_base}/.well-known/openid-configuration"
        
        try:
            response = requests.get(oidc_config_url, timeout=10)
            if response.status_code == 200:
                config = response.json()
                jwks_uri = config.get('jwks_uri')
                if jwks_uri:
                    return jwks_uri
        except (requests.RequestException, ValueError) as e:
            logger.debug(f"OIDC config not found at {oidc_config_url}: {e}")
        
        # Try .well-known/smart-configuration (SMART on FHIR specific)
        smart_config_url = f"{self._issuer_base}/.well-known/smart-configuration"
        
        try:
            response = requests.get(smart_config_url, timeout=10)
            if response.status_code == 200:
                config = response.json()
                jwks_uri = config.get('jwks_uri')
                if jwks_uri:
                    return jwks_uri
        except (requests.RequestException, ValueError) as e:
            logger.debug(f"SMART config not found at {smart_config_url}: {e}")
        
        # Fall back to common JWKS endpoint pattern
        default_jwks_uri = f"{self._issuer_base}/.well-known/jwks.json"
        logger.info(f"Using default JWKS URI: {default_jwks_uri}")
        return default_jwks_uri
    
    def _get_jwks_client(self) -> PyJWKClient:
        """
        Get or create JWKS client with caching.
        
        Returns:
            PyJWKClient instance
        """
        current_time = time.time()
        
        # Refresh cache if expired or not initialized
        if (self._jwks_client is None or 
            current_time - self._jwks_cache_time > JWKS_CACHE_TTL):
            
            jwks_uri = self._get_jwks_uri()
            self._jwks_client = PyJWKClient(jwks_uri, cache_keys=True)
            self._jwks_cache_time = current_time
            logger.info(f"Initialized JWKS client for {jwks_uri}")
        
        return self._jwks_client
    
    def validate_id_token(self, id_token: str) -> dict[str, Any]:
        """
        Validate an OIDC id_token and return its claims.
        
        Security checks performed:
        1. Verify signature using asymmetric algorithm (RS256/ES256)
        2. Reject 'none' and symmetric (HS256) algorithms
        3. Validate issuer matches expected value
        4. Validate audience contains client_id
        5. Check token is not expired (with clock skew tolerance)
        6. Check token was issued in the past
        
        Args:
            id_token: The JWT id_token to validate
        
        Returns:
            Dictionary of validated claims
        
        Raises:
            OIDCValidationError: If validation fails
        """
        if not id_token:
            raise OIDCValidationError("id_token is required", "missing_token")
        
        # Step 1: Decode header without verification to check algorithm
        try:
            unverified_header = jwt.get_unverified_header(id_token)
        except jwt.exceptions.DecodeError as e:
            raise OIDCValidationError(f"Invalid token format: {e}", "invalid_format")
        
        algorithm = unverified_header.get('alg')
        
        # Step 2: Reject insecure algorithms
        if algorithm == 'none':
            logger.warning("SECURITY: Rejected token with 'none' algorithm")
            raise OIDCValidationError(
                "Algorithm 'none' is not allowed", 
                "insecure_algorithm"
            )
        
        if algorithm and algorithm.startswith('HS'):
            logger.warning(f"SECURITY: Rejected token with symmetric algorithm: {algorithm}")
            raise OIDCValidationError(
                f"Symmetric algorithm '{algorithm}' is not allowed for public clients",
                "insecure_algorithm"
            )
        
        if algorithm not in ALLOWED_ALGORITHMS:
            logger.warning(f"SECURITY: Rejected token with unsupported algorithm: {algorithm}")
            raise OIDCValidationError(
                f"Unsupported algorithm: {algorithm}. Allowed: {ALLOWED_ALGORITHMS}",
                "unsupported_algorithm"
            )
        
        # Step 3: Get signing key from JWKS
        try:
            jwks_client = self._get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        except PyJWKClientError as e:
            logger.error(f"Failed to get signing key: {e}")
            raise OIDCValidationError(
                f"Could not retrieve signing key: {e}",
                "jwks_error"
            )
        
        # Step 4: Verify signature and decode claims
        try:
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=ALLOWED_ALGORITHMS,
                audience=self.client_id,
                issuer=self.issuer,
                leeway=self.clock_skew_seconds,
                options={
                    "require": ["exp", "iat", "iss", "aud"],
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                }
            )
        except jwt.ExpiredSignatureError:
            raise OIDCValidationError("Token has expired", "token_expired")
        except jwt.InvalidAudienceError:
            raise OIDCValidationError(
                f"Invalid audience. Expected: {self.client_id}",
                "invalid_audience"
            )
        except jwt.InvalidIssuerError:
            raise OIDCValidationError(
                f"Invalid issuer. Expected: {self.issuer}",
                "invalid_issuer"
            )
        except jwt.InvalidSignatureError:
            logger.warning("SECURITY: Token signature verification failed")
            raise OIDCValidationError(
                "Token signature verification failed",
                "invalid_signature"
            )
        except jwt.DecodeError as e:
            raise OIDCValidationError(f"Token decode error: {e}", "decode_error")
        
        logger.info(f"Successfully validated id_token for issuer: {self.issuer}")
        return claims
    
    def extract_fhir_user(self, claims: dict[str, Any]) -> Optional[str]:
        """
        Extract fhirUser claim from validated token claims.
        
        The fhirUser claim contains a reference to a FHIR resource
        representing the authenticated user (e.g., "Practitioner/123").
        
        Args:
            claims: Validated token claims dictionary
        
        Returns:
            fhirUser claim value or None if not present
        """
        fhir_user = claims.get('fhirUser')
        
        if fhir_user:
            logger.debug(f"Extracted fhirUser: {fhir_user}")
        else:
            logger.debug("No fhirUser claim in token")
        
        return fhir_user
    
    def get_user_identity(self, claims: dict[str, Any]) -> dict[str, Any]:
        """
        Extract user identity information from validated claims.
        
        Args:
            claims: Validated token claims dictionary
        
        Returns:
            Dictionary with user identity fields
        """
        return {
            'subject': claims.get('sub'),
            'fhir_user': claims.get('fhirUser'),
            'name': claims.get('name'),
            'email': claims.get('email'),
            'profile': claims.get('profile'),
            'auth_methods': claims.get('amr', []),  # Authentication methods reference
        }


def validate_id_token_safe(
    id_token: str, 
    issuer: str, 
    client_id: str
) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """
    Safely validate an id_token, returning (claims, None) on success
    or (None, error_message) on failure.
    
    This is a convenience function for use cases where exceptions
    are not desired.
    
    Args:
        id_token: The JWT id_token to validate
        issuer: Expected token issuer
        client_id: OAuth client ID
    
    Returns:
        Tuple of (claims_dict, None) on success or (None, error_message) on failure
    """
    if not id_token:
        return None, None  # No id_token is not an error (may not be present)
    
    try:
        validator = OIDCValidator(issuer, client_id)
        claims = validator.validate_id_token(id_token)
        return claims, None
    except OIDCValidationError as e:
        logger.warning(f"id_token validation failed: {e.message}")
        return None, e.message
    except Exception as e:
        logger.error(f"Unexpected error validating id_token: {e}")
        return None, f"Validation error: {str(e)}"
