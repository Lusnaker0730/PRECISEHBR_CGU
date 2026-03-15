"""
Circuit Breaker for External Service Calls

Prevents cascading failures when an external service (FHIR server) is
unresponsive. Instead of every request waiting for a full timeout,
the circuit breaker short-circuits after detecting repeated failures.

States:
    CLOSED  — normal operation, requests pass through
    OPEN    — service is down, requests fail immediately (fast-fail)
    HALF_OPEN — recovery probe: one request is allowed through to test

IEC 62304 §5.3 — Software Architecture Design
ISO 14971 — Risk Control: RISK-002 (System Availability)
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Lightweight in-process circuit breaker."""

    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'

    def __init__(self, failure_threshold=5, recovery_timeout=30.0, name='default'):
        """
        Args:
            failure_threshold: consecutive failures before opening the circuit
            recovery_timeout: seconds to wait before probing recovery (half-open)
            name: identifier for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._lock = threading.Lock()
        # Metrics
        self._total_rejected = 0
        self._total_successes = 0
        self._total_failures = 0

    @property
    def state(self):
        with self._lock:
            if self._state == self.OPEN:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    logger.info(
                        f"CircuitBreaker[{self.name}]: OPEN → HALF_OPEN "
                        f"after {elapsed:.1f}s recovery wait"
                    )
                    self._state = self.HALF_OPEN
            return self._state

    def allow_request(self):
        """Check if a request should be allowed through."""
        return self.state != self.OPEN

    def record_success(self):
        """Record a successful call — resets failure count, closes circuit."""
        with self._lock:
            prev = self._state
            self._failure_count = 0
            self._state = self.CLOSED
            self._total_successes += 1
            if prev != self.CLOSED:
                logger.info(
                    f"CircuitBreaker[{self.name}]: {prev} → CLOSED "
                    f"(service recovered)"
                )

    def record_failure(self):
        """Record a failed call — may trip the circuit to OPEN."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            self._total_failures += 1
            if self._failure_count >= self.failure_threshold:
                if self._state != self.OPEN:
                    logger.warning(
                        f"CircuitBreaker[{self.name}]: → OPEN "
                        f"after {self._failure_count} consecutive failures. "
                        f"Fast-failing for {self.recovery_timeout}s."
                    )
                self._state = self.OPEN

    def record_rejected(self):
        """Record a request that was rejected (circuit open)."""
        with self._lock:
            self._total_rejected += 1

    def get_metrics(self):
        """Return current metrics for monitoring."""
        with self._lock:
            return {
                'name': self.name,
                'state': self._state,
                'failure_count': self._failure_count,
                'total_successes': self._total_successes,
                'total_failures': self._total_failures,
                'total_rejected': self._total_rejected,
            }

    def reset(self):
        """Manually reset the circuit breaker (for testing or admin)."""
        with self._lock:
            self._state = self.CLOSED
            self._failure_count = 0
            self._last_failure_time = 0.0


class CircuitBreakerRegistry:
    """
    Thread-safe registry of circuit breakers keyed by service name.

    FHIRClientService is instantiated per-request, but circuit breaker
    state must persist across requests for the same FHIR server.
    """

    def __init__(self):
        self._breakers = {}
        self._lock = threading.Lock()

    def get_or_create(self, name, failure_threshold=5, recovery_timeout=30.0):
        """Get existing breaker or create a new one."""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    name=name,
                )
            return self._breakers[name]

    def get_all_metrics(self):
        """Get metrics for all registered breakers."""
        with self._lock:
            return [b.get_metrics() for b in self._breakers.values()]


# Global singleton registry — shared across all requests
circuit_breaker_registry = CircuitBreakerRegistry()
