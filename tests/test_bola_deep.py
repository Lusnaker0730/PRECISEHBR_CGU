"""
Deep BOLA (Broken Object Level Authorization) Tests

Tests for:
1. Tradeoff endpoint BOLA protection (previously missing)
2. FHIR response ownership validation (defense-in-depth)

PT-062 ~ PT-075: Deep object-level authorization tests
"""

import hashlib
import json
from unittest.mock import MagicMock, patch, Mock

import pytest

from services.fhir_client_service import FHIRClientService


pytestmark = [
    pytest.mark.requirement("SRS-006"),
    pytest.mark.risk("RISK-009"),
    pytest.mark.design("SDS-006"),
    pytest.mark.security,
]


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_session(client):
    """Simulate an authenticated session for patient-123."""
    with client.session_transaction() as sess:
        sess['fhir_data'] = {
            'token': 'test-access-token',
            'patient': 'patient-123',
            'server': 'https://fhir.example.com/r4',
            'client_id': 'test-client',
        }
        sess['patient_id'] = 'patient-123'
        sess['session_id'] = 'test-session-id'
        sess['session_fingerprint'] = hashlib.sha256(
            b'127.0.0.1:test-agent'
        ).hexdigest()
    return client


@pytest.fixture
def fhir_service():
    """Create a FHIRClientService with mocked FHIR client."""
    with patch('services.fhir_client_service.client.FHIRClient') as mock_client_cls:
        mock_smart = MagicMock()
        mock_client_cls.return_value = mock_smart
        mock_smart.server = MagicMock()
        mock_smart.server.session = MagicMock()

        service = FHIRClientService(
            fhir_server_url='https://fhir.example.com/r4',
            access_token='test-token',
            client_id='test-client',
        )
        yield service


# ============================================================
# 1. Tradeoff Endpoint BOLA Tests
# ============================================================

class TestTradeoffBOLA:
    """Test BOLA protection on /api/calculate_tradeoff."""

    def test_tradeoff_rejects_different_patient_id(self, authenticated_session):
        """PT-062: Tradeoff endpoint rejects patientId != session patient."""
        resp = authenticated_session.post(
            '/api/calculate_tradeoff',
            json={'patientId': 'patient-EVIL'},
            content_type='application/json',
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data.get('error_type') == 'authorization_error'

    def test_tradeoff_accepts_authorized_patient_id(self, authenticated_session):
        """PT-063: Tradeoff endpoint accepts patientId == session patient."""
        with patch('routes.tradeoff_routes.fhir_data_service') as mock_svc:
            mock_svc.get_tradeoff_model_predictors.return_value = {
                'bleedingEvents': {'predictors': [], 'intercept': 0},
                'thromboticEvents': {'predictors': [], 'intercept': 0},
            }
            mock_svc.get_fhir_data.return_value = (
                {'patient': {'resourceType': 'Patient', 'id': 'patient-123',
                             'birthDate': '1960-01-01', 'gender': 'male'}},
                None,
            )
            mock_svc.get_patient_demographics.return_value = {
                'name': 'Test', 'age': 64, 'gender': 'male',
            }
            mock_svc.get_tradeoff_model_data.return_value = {}
            mock_svc.detect_tradeoff_factors.return_value = []
            mock_svc.calculate_tradeoff_scores_interactive.return_value = {
                'bleeding': 0.05, 'thrombotic': 0.03,
            }

            resp = authenticated_session.post(
                '/api/calculate_tradeoff',
                json={'patientId': 'patient-123'},
                content_type='application/json',
            )
            # Should not be 403
            assert resp.status_code != 403

    def test_tradeoff_missing_patient_id_returns_400(self, authenticated_session):
        """PT-064: Tradeoff endpoint returns 400 for missing patientId."""
        with patch('routes.tradeoff_routes.fhir_data_service') as mock_svc:
            mock_svc.get_tradeoff_model_predictors.return_value = {
                'bleedingEvents': {'predictors': []},
                'thromboticEvents': {'predictors': []},
            }
            resp = authenticated_session.post(
                '/api/calculate_tradeoff',
                json={'someField': 'value'},
                content_type='application/json',
            )
            assert resp.status_code == 400

    def test_tradeoff_no_session_returns_403(self, authenticated_session):
        """PT-065: Tradeoff endpoint returns 403 when session has no patient context."""
        # Clear patient_id from session
        with authenticated_session.session_transaction() as sess:
            del sess['patient_id']
            sess['fhir_data'] = {
                'token': 'test-token',
                'server': 'https://fhir.example.com/r4',
                'client_id': 'test-client',
                # No 'patient' key
            }

        with patch('routes.tradeoff_routes.fhir_data_service') as mock_svc:
            mock_svc.get_tradeoff_model_predictors.return_value = {
                'bleedingEvents': {'predictors': []},
                'thromboticEvents': {'predictors': []},
            }
            resp = authenticated_session.post(
                '/api/calculate_tradeoff',
                json={'patientId': 'patient-123'},
                content_type='application/json',
            )
            assert resp.status_code == 403

    def test_tradeoff_active_factors_bypasses_bola(self, authenticated_session):
        """PT-066: Recalculation with active_factors does not require patientId (no FHIR fetch)."""
        with patch('routes.tradeoff_routes.fhir_data_service') as mock_svc:
            mock_svc.get_tradeoff_model_predictors.return_value = {
                'bleedingEvents': {'predictors': [], 'intercept': 0},
                'thromboticEvents': {'predictors': [], 'intercept': 0},
            }
            mock_svc.calculate_tradeoff_scores_interactive.return_value = {
                'bleeding': 0.05, 'thrombotic': 0.03,
            }
            resp = authenticated_session.post(
                '/api/calculate_tradeoff',
                json={'active_factors': {'age_gte_75': True}},
                content_type='application/json',
            )
            # active_factors path should work without BOLA check
            assert resp.status_code == 200


# ============================================================
# 2. FHIR Response Ownership Validation Tests
# ============================================================

class TestResourceOwnershipValidation:
    """Test _validate_resource_ownership on FHIRClientService."""

    def test_patient_resource_matching_id(self, fhir_service):
        """PT-067: Patient resource with matching id passes validation."""
        resource = {'resourceType': 'Patient', 'id': 'patient-123'}
        assert fhir_service._validate_resource_ownership(resource, 'patient-123') is True

    def test_patient_resource_mismatched_id(self, fhir_service):
        """PT-068: Patient resource with mismatched id fails validation."""
        resource = {'resourceType': 'Patient', 'id': 'patient-EVIL'}
        assert fhir_service._validate_resource_ownership(resource, 'patient-123') is False

    def test_observation_with_correct_subject(self, fhir_service):
        """PT-069: Observation referencing correct patient passes."""
        resource = {
            'resourceType': 'Observation',
            'id': 'obs-1',
            'subject': {'reference': 'Patient/patient-123'},
        }
        assert fhir_service._validate_resource_ownership(resource, 'patient-123') is True

    def test_observation_with_wrong_subject(self, fhir_service):
        """PT-070: Observation referencing wrong patient fails."""
        resource = {
            'resourceType': 'Observation',
            'id': 'obs-1',
            'subject': {'reference': 'Patient/patient-EVIL'},
        }
        assert fhir_service._validate_resource_ownership(resource, 'patient-123') is False

    def test_condition_with_full_url_reference(self, fhir_service):
        """PT-071: Condition with full URL reference matching patient passes."""
        resource = {
            'resourceType': 'Condition',
            'id': 'cond-1',
            'subject': {'reference': 'https://fhir.example.com/Patient/patient-123'},
        }
        assert fhir_service._validate_resource_ownership(resource, 'patient-123') is True

    def test_condition_with_full_url_wrong_patient(self, fhir_service):
        """PT-072: Condition with full URL reference to wrong patient fails."""
        resource = {
            'resourceType': 'Condition',
            'id': 'cond-1',
            'subject': {'reference': 'https://fhir.example.com/Patient/patient-EVIL'},
        }
        assert fhir_service._validate_resource_ownership(resource, 'patient-123') is False

    def test_resource_without_subject_passes(self, fhir_service):
        """PT-073: Resource without subject/patient field passes (cannot validate)."""
        resource = {'resourceType': 'ValueSet', 'id': 'vs-1'}
        assert fhir_service._validate_resource_ownership(resource, 'patient-123') is True

    def test_none_resource_passes(self, fhir_service):
        """Edge case: None or empty resource passes."""
        assert fhir_service._validate_resource_ownership(None, 'patient-123') is True
        assert fhir_service._validate_resource_ownership({}, 'patient-123') is True


class TestFilterOwnedResources:
    """Test _filter_owned_resources bulk filtering."""

    def test_filters_out_mismatched_resources(self, fhir_service):
        """PT-074: Mixed ownership list — only owned resources are kept."""
        resources = [
            {'resourceType': 'Observation', 'id': 'obs-1',
             'subject': {'reference': 'Patient/patient-123'}},
            {'resourceType': 'Observation', 'id': 'obs-evil',
             'subject': {'reference': 'Patient/patient-EVIL'}},
            {'resourceType': 'Observation', 'id': 'obs-2',
             'subject': {'reference': 'Patient/patient-123'}},
        ]
        result = fhir_service._filter_owned_resources(resources, 'patient-123', 'Observation')
        assert len(result) == 2
        assert all(r['id'] != 'obs-evil' for r in result)

    def test_empty_list_returns_empty(self, fhir_service):
        """Edge case: empty list returns empty."""
        assert fhir_service._filter_owned_resources([], 'patient-123') == []


class TestGetAllPatientDataOwnership:
    """Test ownership validation integrated into get_all_patient_data."""

    def test_rejects_patient_resource_ownership_mismatch(self, fhir_service):
        """PT-075: get_all_patient_data rejects mismatched Patient resource."""
        # Mock get_patient to return a resource for a different patient
        fhir_service.get_patient = Mock(return_value=(
            {'resourceType': 'Patient', 'id': 'patient-EVIL', 'birthDate': '1960-01-01'},
            None,
        ))

        raw_data, error = fhir_service.get_all_patient_data('patient-123')

        assert raw_data is None
        assert 'ownership mismatch' in error.lower()

    def test_filters_mismatched_observations(self, fhir_service):
        """Observations belonging to wrong patient are filtered out."""
        fhir_service.get_patient = Mock(return_value=(
            {'resourceType': 'Patient', 'id': 'patient-123', 'birthDate': '1960-01-01'},
            None,
        ))
        fhir_service.get_conditions = Mock(return_value=[])

        # Return observations with mixed ownership
        def fake_fetch(patient_id, resource_type, loinc_codes, text_terms):
            return [
                {'resourceType': 'Observation', 'id': 'obs-ok',
                 'subject': {'reference': 'Patient/patient-123'},
                 'valueQuantity': {'value': 12.0}},
                {'resourceType': 'Observation', 'id': 'obs-evil',
                 'subject': {'reference': 'Patient/patient-EVIL'},
                 'valueQuantity': {'value': 99.0}},
            ]

        fhir_service._fetch_observation_with_fallback = fake_fetch

        with patch('services.fhir_client_service.config_loader') as mock_cfg:
            mock_cfg.get_loinc_codes.return_value = {'HEMOGLOBIN': ['718-7']}
            mock_cfg.get_text_search_terms.return_value = {}

            with patch('services.fhir_client_service.get_security_summary') as mock_sec:
                mock_sec.return_value = {
                    'warnings': [],
                    'requires_elevated_access': False,
                    'restricted_count': 0,
                    'very_restricted_count': 0,
                }

                raw_data, error = fhir_service.get_all_patient_data('patient-123')

        assert error is None
        # Only the owned observation should remain
        assert len(raw_data['HEMOGLOBIN']) == 1
        assert raw_data['HEMOGLOBIN'][0]['id'] == 'obs-ok'
