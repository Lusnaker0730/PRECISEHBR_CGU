"""
Circuit Breaker and CDS Hooks Deadline Tests

Verifies:
1. CircuitBreaker state machine (CLOSED → OPEN → HALF_OPEN → CLOSED)
2. CircuitBreakerRegistry per-server isolation
3. FHIR client integration (fast-fail when circuit is open)
4. CDS Hooks deadline enforcement and fallback cards

IEC 62304 §5.5 — Software Unit Verification
ISO 14971 — Risk Control: RISK-002 (System Availability)
"""

import time
import threading
import pytest

from services.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry


# =========================================================================
# CircuitBreaker State Machine
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-002")
@pytest.mark.design("SDS-001")
class TestCircuitBreakerStateMachine:
    """Verify circuit breaker transitions: CLOSED → OPEN → HALF_OPEN → CLOSED."""

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(failure_threshold=3, name='test')
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.allow_request() is True

    def test_stays_closed_under_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, name='test')
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.allow_request() is True

    def test_opens_at_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, name='test')
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        assert cb.allow_request() is False

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3, name='test')
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        # Only 1 failure after reset, not 3
        assert cb.state == CircuitBreaker.CLOSED

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, name='test')
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitBreaker.HALF_OPEN
        assert cb.allow_request() is True

    def test_half_open_success_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, name='test')
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitBreaker.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitBreaker.CLOSED

    def test_half_open_failure_reopens_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, name='test')
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitBreaker.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN

    def test_manual_reset(self):
        cb = CircuitBreaker(failure_threshold=1, name='test')
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        cb.reset()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.allow_request() is True


# =========================================================================
# Metrics
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-002")
@pytest.mark.design("SDS-001")
class TestCircuitBreakerMetrics:
    """Verify metrics tracking."""

    def test_metrics_track_successes(self):
        cb = CircuitBreaker(failure_threshold=5, name='test')
        cb.record_success()
        cb.record_success()
        metrics = cb.get_metrics()
        assert metrics['total_successes'] == 2
        assert metrics['total_failures'] == 0

    def test_metrics_track_failures(self):
        cb = CircuitBreaker(failure_threshold=5, name='test')
        cb.record_failure()
        cb.record_failure()
        metrics = cb.get_metrics()
        assert metrics['total_failures'] == 2

    def test_metrics_track_rejected(self):
        cb = CircuitBreaker(failure_threshold=1, name='test')
        cb.record_failure()
        cb.record_rejected()
        cb.record_rejected()
        metrics = cb.get_metrics()
        assert metrics['total_rejected'] == 2
        assert metrics['state'] == CircuitBreaker.OPEN


# =========================================================================
# Registry
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-002")
@pytest.mark.design("SDS-001")
class TestCircuitBreakerRegistry:
    """Verify per-server circuit breaker isolation."""

    def test_returns_same_instance_for_same_name(self):
        registry = CircuitBreakerRegistry()
        cb1 = registry.get_or_create('server-a')
        cb2 = registry.get_or_create('server-a')
        assert cb1 is cb2

    def test_returns_different_instances_for_different_names(self):
        registry = CircuitBreakerRegistry()
        cb1 = registry.get_or_create('server-a')
        cb2 = registry.get_or_create('server-b')
        assert cb1 is not cb2

    def test_server_a_open_does_not_affect_server_b(self):
        registry = CircuitBreakerRegistry()
        cb_a = registry.get_or_create('server-a', failure_threshold=1)
        cb_b = registry.get_or_create('server-b', failure_threshold=1)
        cb_a.record_failure()
        assert cb_a.state == CircuitBreaker.OPEN
        assert cb_b.state == CircuitBreaker.CLOSED

    def test_get_all_metrics(self):
        registry = CircuitBreakerRegistry()
        registry.get_or_create('server-x')
        registry.get_or_create('server-y')
        metrics = registry.get_all_metrics()
        names = {m['name'] for m in metrics}
        assert 'server-x' in names
        assert 'server-y' in names


# =========================================================================
# Thread Safety
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-002")
@pytest.mark.design("SDS-001")
class TestCircuitBreakerThreadSafety:
    """Verify thread safety under concurrent access."""

    def test_concurrent_failures_trip_circuit(self):
        cb = CircuitBreaker(failure_threshold=10, name='thread-test')
        errors = []

        def fail_n_times(n):
            try:
                for _ in range(n):
                    cb.record_failure()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=fail_n_times, args=(5,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # 4 threads × 5 failures = 20 failures >= threshold of 10
        assert cb.state == CircuitBreaker.OPEN
        metrics = cb.get_metrics()
        assert metrics['total_failures'] == 20

    def test_concurrent_registry_access(self):
        registry = CircuitBreakerRegistry()
        instances = []

        def get_breaker():
            cb = registry.get_or_create('concurrent-test')
            instances.append(id(cb))

        threads = [threading.Thread(target=get_breaker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same instance
        assert len(set(instances)) == 1


# =========================================================================
# CDS Hooks Fallback Cards
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-002")
@pytest.mark.design("SDS-001")
class TestCDSHooksFallbackCards:
    """Verify fallback card generation for CDS Hooks."""

    def test_timeout_fallback_card(self):
        from routes.hooks import _build_fallback_card
        card = _build_fallback_card('timeout')
        assert card['indicator'] == 'warning'
        assert 'delayed' in card['summary'].lower() or 'deadline' in card['summary'].lower()
        assert 'source' in card

    def test_circuit_open_fallback_card(self):
        from routes.hooks import _build_fallback_card
        card = _build_fallback_card('circuit_open')
        assert card['indicator'] == 'warning'
        assert 'unreachable' in card['detail'].lower()

    def test_error_fallback_card(self):
        from routes.hooks import _build_fallback_card
        card = _build_fallback_card('error')
        assert card['indicator'] == 'warning'
        assert 'source' in card

    def test_fallback_card_has_valid_structure(self):
        """All fallback cards must have required CDS Hooks fields."""
        from routes.hooks import _build_fallback_card
        for reason in ('timeout', 'circuit_open', 'error'):
            card = _build_fallback_card(reason)
            assert 'summary' in card
            assert 'indicator' in card
            assert 'detail' in card
            assert 'source' in card
            assert isinstance(card['source'], dict)
            assert 'label' in card['source']


# =========================================================================
# CDS Hooks Deadline Enforcement
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-002")
@pytest.mark.design("SDS-001")
class TestCDSDeadlineEnforcement:
    """Verify _check_deadline raises on expiry."""

    def test_check_deadline_passes_when_within_limit(self):
        from routes.hooks import _check_deadline, CDS_DEADLINE_SECONDS
        start = time.monotonic()
        # Should not raise
        _check_deadline(start, 'test')

    def test_check_deadline_raises_when_exceeded(self):
        from routes.hooks import _check_deadline, _DeadlineExceeded
        # Use a start time far in the past
        start = time.monotonic() - 10.0
        with pytest.raises(_DeadlineExceeded):
            _check_deadline(start, 'test_stage')

    def test_deadline_constant_is_reasonable(self):
        """CDS deadline should be between 1s and 10s."""
        from routes.hooks import CDS_DEADLINE_SECONDS
        assert 1.0 <= CDS_DEADLINE_SECONDS <= 10.0


# =========================================================================
# Integration: CDS Hook endpoint returns fallback on error
# =========================================================================

@pytest.mark.requirement("SRS-001")
@pytest.mark.risk("RISK-002")
@pytest.mark.design("SDS-001")
class TestCDSHookEndpointFallback:
    """Verify CDS Hook endpoints return fallback cards on errors."""

    def test_medication_hook_returns_fallback_on_error(self, client):
        """Sending malformed data should return fallback card, not crash."""
        response = client.post(
            '/cds-services/precise_hbr_bleeding_risk_alert',
            json={'context': {'patientId': 'test'}, 'prefetch': {
                'patient': {'resourceType': 'Patient', 'id': 'test', 'name': [{'given': ['Test'], 'family': 'User'}]},
                'medications': {'entry': [{'resource': {'medicationCodeableConcept': {
                    'coding': [{'system': 'http://www.nlm.nih.gov/research/umls/rxnorm', 'code': '1191'}],
                    'text': 'aspirin'
                }}}]},
                'hemoglobin': {},
                'creatinine': {},
                'egfr': {},
                'wbc': {},
                'conditions': {},
            }},
            content_type='application/json',
        )
        # Should return 200 with cards (empty or warning), not 500
        assert response.status_code == 200
        data = response.get_json()
        assert 'cards' in data

    def test_patient_view_returns_fallback_on_error(self, client):
        """Patient-view hook errors should return fallback card, not empty."""
        response = client.post(
            '/cds-services/precise_hbr_patient_view',
            json={'hook': 'patient-view', 'context': {'patientId': 'test'}, 'prefetch': {
                'patient': {
                    'resourceType': 'Patient', 'id': 'test',
                    'name': [{'given': ['Test'], 'family': 'User'}],
                    'birthDate': '1960-01-01', 'gender': 'male',
                },
                'medications': {},
                'hemoglobin': {},
                'creatinine': {},
                'egfr': {},
                'wbc': {},
                'conditions': {},
            }},
            content_type='application/json',
        )
        # Should return cards (warning card for missing data or fallback)
        data = response.get_json()
        assert 'cards' in data

    def test_patient_view_no_patient_returns_empty(self, client):
        """Patient-view with no patientId returns empty cards."""
        response = client.post(
            '/cds-services/precise_hbr_patient_view',
            json={'hook': 'patient-view', 'context': {}, 'prefetch': {}},
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['cards'] == []
