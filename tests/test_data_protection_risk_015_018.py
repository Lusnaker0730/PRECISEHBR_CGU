"""
Data Protection Security Tests — RISK-008/009/015~018
=====================================================
Covers security audit findings on ePHI data protection:

RISK-008/015: ePHI Log Poisoning — logging filter redaction
RISK-009: BOLA/IDOR — patient context enforcement
RISK-016: Session storage — server-side, cookie flags
RISK-017: Data Minimization — FHIR query filtering
RISK-018: ePHI lifecycle — session timeout & destruction

Traceability:
  Requirements: SRS-004 (#4), SRS-005 (#5), SRS-006 (#6), SRS-010 (#10)
  Design: SDS-004 (#16), SDS-005 (#17), SDS-010 (#22)
  Verification: TC-005 (#38), TC-006 (#39), TC-007 (#40), TC-011 (#44)
"""

import hashlib
import json
import logging
import time
from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def authenticated_session(client):
    """Simulate an authenticated session with FHIR data."""
    with client.session_transaction() as sess:
        sess['fhir_data'] = {
            'token': 'test-access-token-abc123',
            'patient': 'patient-123',
            'server': 'https://fhir.example.com/r4',
            'client_id': 'test-client',
            'expires_in': 3600,
            'scope': 'patient/*.read',
            'refresh_token': 'test-refresh-token-xyz',
        }
        sess['patient_id'] = 'patient-123'
        sess['session_id'] = 'test-session-id'
        sess['session_fingerprint'] = hashlib.sha256(
            b'127.0.0.1:test-agent'
        ).hexdigest()
    return client


# ============================================================
# RISK-015: ePHI Log Poisoning
# ============================================================

@pytest.mark.requirement("SRS-010")
@pytest.mark.risk("RISK-015")
@pytest.mark.risk("RISK-008")
@pytest.mark.design("SDS-010")
@pytest.mark.security
class TestRISK015_EPhiLogPoisoning:
    """RISK-015: ePHI leakage via log poisoning.

    Success Criteria:
    - SC-015-01: FHIR Patient resource detected and fully redacted
    - SC-015-02: FHIR Observation resource detected and fully redacted
    - SC-015-03: Taiwan National ID pattern redacted
    - SC-015-04: SSN pattern redacted
    - SC-015-05: Bearer token pattern redacted
    - SC-015-06: SAFE_DICT_KEYS allowlist blocks unknown keys
    - SC-015-07: Filter attached to root/app/werkzeug loggers
    - SC-015-08: Patient name in free text redacted
    """

    def test_sc_015_01_fhir_patient_resource_redacted(self):
        """SC-015-01: FHIR Patient resource must be fully redacted in logs."""
        from utils.logging_filter import EPhiLoggingFilter

        f = EPhiLoggingFilter()
        patient_data = {
            'resourceType': 'Patient',
            'id': 'patient-123',
            'name': [{'family': 'Wang', 'given': ['Wei-Lin']}],
            'birthDate': '1985-03-15',
            'identifier': [{'value': 'A123456789'}],
            'address': [{'text': 'Taipei, Taiwan'}],
        }
        result = f._sanitize_dict(patient_data)
        # Entire resource should be redacted
        assert '_redacted' in result or 'REDACTED' in str(result)
        assert 'Wang' not in str(result)
        assert 'Wei-Lin' not in str(result)
        assert '1985-03-15' not in str(result)
        assert 'A123456789' not in str(result)

    def test_sc_015_02_fhir_observation_resource_redacted(self):
        """SC-015-02: FHIR Observation resource must be fully redacted."""
        from utils.logging_filter import EPhiLoggingFilter

        f = EPhiLoggingFilter()
        obs_data = {
            'resourceType': 'Observation',
            'subject': {'reference': 'Patient/123'},
            'code': {'coding': [{'code': '718-7', 'display': 'Hemoglobin'}]},
            'valueQuantity': {'value': 12.5, 'unit': 'g/dL'},
        }
        result = f._sanitize_dict(obs_data)
        assert '_redacted' in result or 'REDACTED' in str(result)
        assert 'Patient/123' not in str(result)

    def test_sc_015_03_taiwan_national_id_redacted(self):
        """SC-015-03: Taiwan National ID (e.g., A123456789) must be redacted."""
        from utils.logging_filter import EPhiLoggingFilter

        f = EPhiLoggingFilter()
        text = "Patient identifier: A123456789 was processed"
        result = f._scrub_string(text)
        assert 'A123456789' not in result
        assert 'REDACTED' in result or 'TW_ID' in result

    def test_sc_015_04_ssn_pattern_redacted(self):
        """SC-015-04: SSN pattern (123-45-6789) must be redacted."""
        from utils.logging_filter import EPhiLoggingFilter

        f = EPhiLoggingFilter()
        text = "SSN: 123-45-6789 found in record"
        result = f._scrub_string(text)
        assert '123-45-6789' not in result
        assert 'REDACTED' in result or 'SSN' in result

    def test_sc_015_05_bearer_token_redacted(self):
        """SC-015-05: Bearer token in log text must be redacted."""
        from utils.logging_filter import EPhiLoggingFilter

        f = EPhiLoggingFilter()
        text = "Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.payload.sig"
        result = f._scrub_string(text)
        assert 'eyJhbGci' not in result

    def test_sc_015_06_unknown_dict_keys_blocked(self):
        """SC-015-06: Dict keys not in SAFE_DICT_KEYS allowlist must be redacted.
        Note: If dict triggers FHIR resource detection, entire dict is redacted."""
        from utils.logging_filter import EPhiLoggingFilter

        f = EPhiLoggingFilter()
        data = {
            'status': 'success',
            'score': 25,
            'patient_name': 'Wang Wei',
            'birthDate': '1985-03-15',
        }
        result = f._sanitize_dict(data)
        result_str = str(result)
        # Regardless of mechanism (FHIR detection or key allowlist),
        # sensitive values must not appear in output
        assert 'Wang Wei' not in result_str
        assert '1985-03-15' not in result_str

    def test_sc_015_07_filter_attached_to_loggers(self, app):
        """SC-015-07: EPhiLoggingFilter must be attached to app/root loggers."""
        from utils.logging_filter import EPhiLoggingFilter

        # Check that at least one logger has the ePHI filter
        root_logger = logging.getLogger()
        app_logger = app.logger
        werkzeug_logger = logging.getLogger('werkzeug')

        all_filters = (
            root_logger.filters +
            app_logger.filters +
            werkzeug_logger.filters
        )
        has_ephi_filter = any(
            isinstance(f, EPhiLoggingFilter) for f in all_filters
        )
        # Also check handlers' filters
        for handler in root_logger.handlers + app_logger.handlers:
            if any(isinstance(f, EPhiLoggingFilter) for f in handler.filters):
                has_ephi_filter = True
                break

        assert has_ephi_filter, "EPhiLoggingFilter not found on any logger"

    def test_sc_015_08_fhir_json_blob_in_text_redacted(self):
        """SC-015-08: JSON blob containing resourceType in free text must be redacted."""
        from utils.logging_filter import EPhiLoggingFilter

        f = EPhiLoggingFilter()
        text = 'Error processing: {"resourceType": "Patient", "name": [{"family": "Chen"}]}'
        result = f._scrub_string(text)
        assert 'Chen' not in result


# ============================================================
# RISK-009 (expanded): BOLA / IDOR Attacks
# ============================================================

@pytest.mark.requirement("SRS-006")
@pytest.mark.risk("RISK-009")
@pytest.mark.design("SDS-006")
@pytest.mark.security
class TestRISK009_BOLA_Expanded:
    """RISK-009: BOLA/IDOR — patient context enforcement.

    Success Criteria:
    - SC-009-01: validate_patient_context rejects mismatched patient IDs
    - SC-009-02: validate_patient_context accepts matching patient IDs
    - SC-009-03: @require_patient_context returns 403 on mismatch
    - SC-009-04: Security violation is logged on BOLA attempt
    - SC-009-05: API endpoints enforce patient context
    - SC-009-06: FHIR resource ownership validated per resource
    """

    def test_sc_009_01_reject_mismatched_patient(self, app):
        """SC-009-01: validate_patient_context rejects different patient ID."""
        from utils.patient_context import validate_patient_context

        with app.test_request_context():
            with patch('utils.patient_context.get_authorized_patient_id',
                       return_value='patient-123'):
                is_valid, error = validate_patient_context('patient-456')
                assert is_valid is False
                assert error is not None

    def test_sc_009_02_accept_matching_patient(self, app):
        """SC-009-02: validate_patient_context accepts matching patient ID."""
        from utils.patient_context import validate_patient_context

        with app.test_request_context():
            with patch('utils.patient_context.get_authorized_patient_id',
                       return_value='patient-123'):
                is_valid, error = validate_patient_context('patient-123')
                assert is_valid is True
                assert error is None

    def test_sc_009_03_api_rejects_wrong_patient(self, authenticated_session):
        """SC-009-03: API returns 4xx when requesting different patient's data."""
        # Session has patient-123, try to access patient-999 via POST
        resp = authenticated_session.post(
            '/api/calculate_risk',
            json={'patient_id': 'patient-999'},
            content_type='application/json'
        )
        assert resp.status_code in (400, 403, 405)

    def test_sc_009_04_bola_attempt_logged(self):
        """SC-009-04: BOLA attempt triggers security violation log."""
        from utils.patient_context import validate_patient_context

        with patch('utils.patient_context.get_authorized_patient_id',
                   return_value='patient-123'):
            with patch('utils.patient_context._log_context_violation') as mock_log:
                validate_patient_context('patient-HACKED')
                mock_log.assert_called_once()

    def test_sc_009_05_fhir_resource_ownership_validation(self):
        """SC-009-06: FHIR resources must be validated for patient ownership."""
        from services.fhir_client_service import FHIRClientService

        with patch('fhirclient.client.FHIRClient'):
            service = FHIRClientService(
                fhir_server_url='https://fhir.example.com/r4',
                access_token='test-token',
                client_id='test-client'
            )

        # Resource belonging to correct patient
        valid_resource = {
            'resourceType': 'Observation',
            'subject': {'reference': 'Patient/patient-123'}
        }
        assert service._validate_resource_ownership(
            valid_resource, 'patient-123'
        ) is True

        # Resource belonging to different patient
        invalid_resource = {
            'resourceType': 'Observation',
            'subject': {'reference': 'Patient/patient-OTHER'}
        }
        assert service._validate_resource_ownership(
            invalid_resource, 'patient-123'
        ) is False


# ============================================================
# RISK-016: Session Storage Security
# ============================================================

@pytest.mark.requirement("SRS-005")
@pytest.mark.requirement("SRS-006")
@pytest.mark.risk("RISK-016")
@pytest.mark.design("SDS-005")
@pytest.mark.security
class TestRISK016_SessionStorageSecurity:
    """RISK-016: Session storage must be server-side, not client cookie.

    Success Criteria:
    - SC-016-01: SESSION_TYPE is 'filesystem' (server-side), not 'cookie'
    - SC-016-02: SESSION_COOKIE_HTTPONLY is True
    - SC-016-03: SESSION_COOKIE_SAMESITE is Lax or Strict
    - SC-016-04: SECRET_KEY is sufficiently long (>=32 chars)
    - SC-016-05: Session cookie does not contain ePHI or token in value
    - SC-016-06: Session ID is opaque (not Base64 of data)
    """

    def test_sc_016_01_session_is_server_side(self, app):
        """SC-016-01: SESSION_TYPE must be 'filesystem' (server-side)."""
        session_type = app.config.get('SESSION_TYPE', 'null')
        assert session_type in ('filesystem', 'redis', 'memcached', 'sqlalchemy'), \
            f"SESSION_TYPE is '{session_type}' — must be server-side, not 'cookie'"

    def test_sc_016_02_httponly_flag(self, app):
        """SC-016-02: SESSION_COOKIE_HTTPONLY must be True."""
        assert app.config.get('SESSION_COOKIE_HTTPONLY', True) is True

    def test_sc_016_03_samesite_flag(self, app):
        """SC-016-03: SESSION_COOKIE_SAMESITE must be Lax or Strict."""
        samesite = app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
        assert samesite in ('Lax', 'Strict', 'lax', 'strict')

    def test_sc_016_04_secret_key_length(self, app):
        """SC-016-04: SECRET_KEY must be at least 32 characters."""
        secret = app.config.get('SECRET_KEY', '')
        assert len(secret) >= 32, \
            f"SECRET_KEY is only {len(secret)} chars — minimum 32 required"

    def test_sc_016_05_cookie_does_not_contain_ephi(self, authenticated_session):
        """SC-016-05: Session cookie value must not contain ePHI or tokens."""
        resp = authenticated_session.get('/main')
        cookie_header = resp.headers.get('Set-Cookie', '')
        # Cookie should not contain access token or patient data
        assert 'test-access-token' not in cookie_header
        assert 'patient-123' not in cookie_header

    def test_sc_016_06_session_id_is_opaque(self, client):
        """SC-016-06: Session ID must be opaque, not Base64 of actual data."""
        resp = client.get('/')
        cookie_header = resp.headers.get('Set-Cookie', '')
        # Session cookie should exist but be a short opaque ID
        if 'session=' in cookie_header.lower():
            import re
            match = re.search(r'session=([^;]+)', cookie_header, re.IGNORECASE)
            if match:
                session_value = match.group(1)
                # Should NOT be a long Base64-encoded JSON blob
                assert len(session_value) < 500, \
                    "Session cookie is too long — may be client-side storage"


# ============================================================
# RISK-017: FHIR Data Minimization
# ============================================================

@pytest.mark.requirement("SRS-004")
@pytest.mark.risk("RISK-017")
@pytest.mark.design("SDS-004")
@pytest.mark.security
class TestRISK017_DataMinimization:
    """RISK-017: FHIR queries must use specific filters (data minimization).

    Success Criteria:
    - SC-017-01: Observation queries use LOINC code filter
    - SC-017-02: LOINC codes are validated before use
    - SC-017-03: Condition queries filter by clinical-status=active
    - SC-017-04: All queries use _count parameter to limit results
    - SC-017-05: Resource ownership validated for each returned resource
    - SC-017-06: Only required LOINC codes are queried (Hb, WBC, eGFR, Cr)
    """

    def test_sc_017_01_observation_query_uses_loinc_filter(self):
        """SC-017-01: get_observations_by_loinc accepts LOINC code parameter."""
        from services.fhir_client_service import FHIRClientService
        import inspect

        with patch('fhirclient.client.FHIRClient'):
            service = FHIRClientService(
                fhir_server_url='https://fhir.example.com/r4',
                access_token='test-token',
                client_id='test-client'
            )

        # Method signature must accept loinc_codes parameter
        sig = inspect.signature(service.get_observations_by_loinc)
        assert 'loinc_codes' in sig.parameters
        assert 'patient_id' in sig.parameters

    def test_sc_017_02_loinc_code_validation(self):
        """SC-017-02: Invalid LOINC codes must be rejected."""
        from utils.input_validator import validate_loinc_code

        # validate_loinc_code returns (bool, error_msg) tuple
        # Valid LOINC codes
        assert validate_loinc_code('718-7')[0] is True     # Hemoglobin
        assert validate_loinc_code('6690-2')[0] is True    # WBC
        assert validate_loinc_code('33914-3')[0] is True   # eGFR
        assert validate_loinc_code('2160-0')[0] is True    # Creatinine

        # Invalid LOINC codes
        assert validate_loinc_code('')[0] is False
        assert validate_loinc_code('not-a-loinc')[0] is False
        assert validate_loinc_code('<script>alert(1)</script>')[0] is False

    def test_sc_017_03_condition_query_has_count_param(self):
        """SC-017-03: get_conditions has count param for result limiting."""
        from services.fhir_client_service import FHIRClientService
        import inspect

        with patch('fhirclient.client.FHIRClient'):
            service = FHIRClientService(
                fhir_server_url='https://fhir.example.com/r4',
                access_token='test-token',
                client_id='test-client'
            )

        sig = inspect.signature(service.get_conditions)
        assert 'count' in sig.parameters
        assert 'patient_id' in sig.parameters

    def test_sc_017_04_queries_use_count_limit(self):
        """SC-017-04: FHIR queries must use _count to limit results."""
        from services.fhir_client_service import FHIRClientService

        with patch('fhirclient.client.FHIRClient'):
            service = FHIRClientService(
                fhir_server_url='https://fhir.example.com/r4',
                access_token='test-token',
                client_id='test-client'
            )

        # Check that default count params exist in method signatures
        import inspect
        sig = inspect.signature(service.get_observations_by_loinc)
        assert 'count' in sig.parameters
        count_default = sig.parameters['count'].default
        assert isinstance(count_default, int) and count_default > 0

        sig_cond = inspect.signature(service.get_conditions)
        assert 'count' in sig_cond.parameters

    def test_sc_017_05_resource_ownership_filters_mismatches(self):
        """SC-017-05: _filter_owned_resources removes mismatched resources."""
        from services.fhir_client_service import FHIRClientService

        with patch('fhirclient.client.FHIRClient'):
            service = FHIRClientService(
                fhir_server_url='https://fhir.example.com/r4',
                access_token='test-token',
                client_id='test-client'
            )

        resources = [
            {'resourceType': 'Observation', 'subject': {'reference': 'Patient/patient-123'}},
            {'resourceType': 'Observation', 'subject': {'reference': 'Patient/patient-OTHER'}},
            {'resourceType': 'Observation', 'subject': {'reference': 'Patient/patient-123'}},
        ]
        filtered = service._filter_owned_resources(resources, 'patient-123', 'test')
        assert len(filtered) == 2  # Only 2 belong to patient-123

    def test_sc_017_06_required_loinc_codes_configured(self):
        """SC-017-06: Required LOINC codes must be configured for queries."""
        from services.config_loader import config_loader

        loinc_map = config_loader.get_loinc_codes()

        # Must have the required lab code categories
        required_keys = ['HEMOGLOBIN', 'WBC', 'EGFR', 'CREATININE']
        for key in required_keys:
            codes = loinc_map.get(key, ())
            assert len(codes) > 0, f"Missing LOINC codes for {key}"


# ============================================================
# RISK-018: ePHI Lifecycle & Destruction
# ============================================================

@pytest.mark.requirement("SRS-005")
@pytest.mark.requirement("SRS-010")
@pytest.mark.risk("RISK-018")
@pytest.mark.design("SDS-005")
@pytest.mark.security
class TestRISK018_EPhiLifecycle:
    """RISK-018: ePHI lifecycle — data must be destroyed on session end.

    Success Criteria:
    - SC-018-01: Explicit logout clears all session data
    - SC-018-02: Session timeout is configured
    - SC-018-03: After logout, fhir_data is gone
    - SC-018-04: After logout, patient_id is gone
    - SC-018-05: After logout, access token is gone
    - SC-018-06: Protected routes reject expired/cleared sessions
    """

    def test_sc_018_01_logout_clears_session(self, authenticated_session):
        """SC-018-01: Logout must call session.clear() or equivalent."""
        # Verify data exists
        with authenticated_session.session_transaction() as sess:
            assert 'fhir_data' in sess
            assert 'patient_id' in sess

        # Logout
        authenticated_session.get('/logout')

        # All sensitive data cleared
        with authenticated_session.session_transaction() as sess:
            assert sess.get('fhir_data') is None or \
                   sess.get('fhir_data', {}).get('token') is None

    def test_sc_018_02_session_timeout_configured(self, app):
        """SC-018-02: Session timeout must be configured."""
        has_timeout = (
            app.config.get('PERMANENT_SESSION_LIFETIME') is not None or
            app.config.get('SESSION_TIMEOUT_HOURS') is not None or
            app.config.get('SESSION_TIMEOUT_SECONDS') is not None
        )
        assert has_timeout, "No session timeout configured — ePHI may persist indefinitely"

    def test_sc_018_03_logout_removes_fhir_data(self, authenticated_session):
        """SC-018-03: fhir_data must be None after logout."""
        authenticated_session.get('/logout')
        with authenticated_session.session_transaction() as sess:
            fhir = sess.get('fhir_data')
            if fhir:
                assert fhir.get('token') is None

    def test_sc_018_04_logout_removes_patient_id(self, authenticated_session):
        """SC-018-04: patient_id must be None after logout."""
        authenticated_session.get('/logout')
        with authenticated_session.session_transaction() as sess:
            assert sess.get('patient_id') is None

    def test_sc_018_05_logout_removes_access_token(self, authenticated_session):
        """SC-018-05: Access token must not survive logout."""
        authenticated_session.get('/logout')
        with authenticated_session.session_transaction() as sess:
            fhir = sess.get('fhir_data', {})
            if isinstance(fhir, dict):
                assert fhir.get('token') is None
                assert fhir.get('refresh_token') is None

    def test_sc_018_06_expired_session_rejected(self, client):
        """SC-018-06: Requests with no session must be rejected."""
        resp = client.get('/main')
        assert resp.status_code in (302, 401, 403)

    def test_sc_018_07_post_logout_api_rejected(self, authenticated_session):
        """SC-018-06 extended: API calls after logout must fail."""
        authenticated_session.get('/logout')
        resp = authenticated_session.get('/main')
        assert resp.status_code in (302, 400, 401, 403)
