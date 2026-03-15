"""
ONC Compliance: 45 CFR 170.315 (d)(2) - Auditable Events and Tamper-resistance

This module provides comprehensive audit logging functionality for tracking all
access to electronic Protected Health Information (ePHI).

Features:
- Records all ePHI access events with required metadata (5W: Who/What/Whom/When/Where)
- Implements tamper-resistance through cryptographic hashing
- Stores logs in append-only JSON Lines format
- GCP Cloud Logging structured output on GAE for WORM-grade durability
- Provides query and analysis capabilities
"""

import datetime
import hashlib
import json
import logging
import os
import sys
import tempfile
import threading
from functools import wraps
from typing import Any, Optional

from flask import request, session, has_request_context

# Configure module logger
logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Secure audit logging system for ePHI access tracking.

    Implements tamper-resistance through cryptographic chain:
    Each log entry includes a hash of the previous entry, creating
    an immutable audit trail.

    Thread-safe: Uses a lock to ensure atomic write operations.
    """

    def __init__(self, audit_file_path=None):
        """
        Initialize the audit logger.

        Args:
            audit_file_path: Path to the audit log file (auto-detected if None)
        """
        # Thread lock for atomic operations
        self._lock = threading.Lock()

        # Auto-detect appropriate path based on environment
        if audit_file_path is None:
            if os.environ.get('GAE_ENV', '').startswith('standard'):
                # Running on Google App Engine - use secure temp directory
                audit_file_path = os.path.join(tempfile.gettempdir(), 'audit', 'audit_log.jsonl')
            else:
                # Running locally - use instance directory
                audit_file_path = 'instance/audit/audit_log.jsonl'

        self.audit_file_path = audit_file_path
        self.audit_dir = os.path.dirname(audit_file_path)

        # Create audit directory if it doesn't exist
        try:
            os.makedirs(self.audit_dir, mode=0o700, exist_ok=True)  # M-04
        except OSError as e:
            logger.error(f"AUDIT COMPLIANCE WARNING: Could not create audit directory {self.audit_dir}: {e}")  # C-06

        # Initialize audit log file with header if it doesn't exist
        if not os.path.exists(self.audit_file_path):
            self._initialize_audit_log()

        # Load the last hash for chain verification
        self._last_hash = self._get_last_hash()
    
    def _initialize_audit_log(self):
        """Initialize audit log file with metadata header"""
        try:
            metadata = {
                'log_type': 'AUDIT_LOG_HEADER',
                'application': 'SMART on FHIR PRECISE-HBR Calculator',
                'compliance_standard': '45 CFR 170.315 (d)(2)',
                'initialized_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                'version': '1.0',
                'hash_algorithm': 'SHA-256',
                'previous_hash': None,
                'entry_hash': None
            }
            # Calculate hash of metadata
            metadata['entry_hash'] = self._calculate_hash(metadata)
            
            with open(self.audit_file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(metadata, ensure_ascii=False) + '\n')
            try:
                os.chmod(self.audit_file_path, 0o600)  # M-04
            except OSError:
                pass
            logger.info(f"Audit log initialized: {self.audit_file_path}")
        except OSError as e:
            logger.error(f"AUDIT COMPLIANCE WARNING: Could not initialize audit log {self.audit_file_path}: {e}")  # C-06
    
    def _get_last_hash(self) -> Optional[str]:
        """
        Retrieve the hash of the last log entry for chain verification.

        Uses efficient file seeking to read only the last line,
        avoiding loading the entire file into memory.

        Returns:
            The last entry hash, or None if log is empty or unreadable
        """
        if not os.path.exists(self.audit_file_path):
            return None

        try:
            with open(self.audit_file_path, 'rb') as f:
                # Seek to end of file
                f.seek(0, 2)
                file_size = f.tell()
                if file_size == 0:
                    return None

                # Read backwards to find the last newline
                buffer_size = min(4096, file_size)
                f.seek(-buffer_size, 2)
                lines = f.read().decode('utf-8').splitlines()

                if not lines:
                    return None

                # Get the last non-empty line
                last_line = lines[-1] if lines[-1] else (lines[-2] if len(lines) > 1 else None)
                if not last_line:
                    return None

                last_entry = json.loads(last_line)
                return last_entry.get('entry_hash')

        except (OSError, IOError) as e:
            logger.warning(f"Could not read audit log (possibly read-only filesystem): {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing last hash entry: {e}")
        except (UnicodeDecodeError, ValueError) as e:
            logger.error(f"Error decoding audit log: {e}")
        return None
    
    def _calculate_hash(self, entry_data: dict[str, Any]) -> str:
        """
        Calculate SHA-256 hash of an audit entry.

        Creates a deterministic hash by excluding the 'entry_hash' field,
        sorting keys for consistency, and using compact JSON representation.

        Args:
            entry_data: The audit entry dictionary

        Returns:
            Hexadecimal hash string
        """
        data_to_hash = {k: v for k, v in entry_data.items() if k != 'entry_hash'}
        json_str = json.dumps(data_to_hash, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    def log_event(
        self,
        event_type: str,
        action: str,
        patient_id: Optional[str] = None,
        user_id: Optional[str] = None,
        fhir_user: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_ids: Optional[list] = None,
        outcome: str = 'success',
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Log an auditable event with full 5W context.

        Args:
            event_type: Type of event (e.g., 'ePHI_ACCESS', 'DATA_EXPORT', 'LOGIN')
            action: Specific action performed (e.g., 'view_patient_data', 'calculate_risk')
            patient_id: Patient identifier — Whom (if applicable)
            user_id: User/session identifier — Who (session-level)
            fhir_user: FHIR Practitioner reference — Who (e.g., 'Practitioner/12345')
            resource_type: FHIR resource type accessed (e.g., 'Patient', 'Observation')
            resource_ids: List of specific resource IDs accessed
            outcome: 'success' or 'failure'
            details: Additional context information
            ip_address: Client IP address — Where
            user_agent: Client user agent string — Where

        Returns:
            The logged audit entry
        """
        # H-04: Lock protects both read and write of hash chain
        with self._lock:
            current_last_hash = self._last_hash

            # Merge GCP trace context into details for cross-service correlation
            merged_details = dict(details) if details else {}
            trace_ctx = _get_trace_context()
            if trace_ctx:
                merged_details.update(trace_ctx)

            audit_entry = {
                'timestamp': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                'event_type': event_type,
                'action': action,
                'user_id': user_id,
                'fhir_user': fhir_user,
                'patient_id': patient_id,
                'resource_type': resource_type,
                'resource_ids': resource_ids or [],
                'outcome': outcome,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'details': merged_details,
                'previous_hash': current_last_hash
            }
            audit_entry['entry_hash'] = self._calculate_hash(audit_entry)

            return self._write_audit_entry(audit_entry)

    def _write_audit_entry(self, audit_entry: dict[str, Any]) -> dict[str, Any]:
        """
        Write an audit entry to the log file and update chain state.

        On GAE, also emits structured JSON to stdout for Cloud Logging
        ingestion (routed to WORM storage via Log Sink).

        Note: This method should be called within the _lock context.
        """
        event_type = audit_entry['event_type']
        action = audit_entry['action']
        user_id = audit_entry['user_id']
        patient_id = audit_entry['patient_id']
        outcome = audit_entry['outcome']

        try:
            with open(self.audit_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + '\n')
            # Update hash chain state (atomic with write due to lock)
            self._last_hash = audit_entry['entry_hash']
            logger.info(f"AUDIT: {event_type} - {action} - User:{user_id} - Patient:{patient_id} - Outcome:{outcome}")
        except (OSError, IOError) as e:
            logger.warning(f"Could not write to audit log file (read-only filesystem): {e}")
            # Still log to application logger for traceability
            logger.info(f"AUDIT_ENTRY: {json.dumps(audit_entry)}")

        # On GAE, emit structured JSON to stdout for Cloud Logging.
        # Cloud Logging auto-parses JSON from stdout on GAE Standard.
        # Route these via a Log Sink to a Locked Cloud Storage bucket for WORM.
        if os.environ.get('GAE_ENV', '').startswith('standard'):
            self._write_structured_log(audit_entry)

        return audit_entry

    def _write_structured_log(self, audit_entry: dict[str, Any]) -> None:
        """
        Emit audit entry as GCP Cloud Logging structured JSON to stdout.

        Cloud Logging on GAE Standard auto-captures JSON lines from stdout.
        Use a Log Sink with filter `jsonPayload.audit_event="true"` to route
        audit entries to a Cloud Storage bucket with Retention Lock (WORM).
        """
        structured = {
            'severity': 'NOTICE',
            'message': f"AUDIT: {audit_entry['event_type']} - {audit_entry['action']}",
            'audit_event': 'true',
            'logging.googleapis.com/labels': {
                'audit_event': 'true',
                'event_type': audit_entry['event_type'],
            },
        }
        # Merge all audit fields at top level for Cloud Logging queryability
        structured.update(audit_entry)

        # Attach GCP trace for correlation in Cloud Trace / Logging
        trace_id = audit_entry.get('details', {}).get('trace_id')
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', '')
        if trace_id and project_id:
            structured['logging.googleapis.com/trace'] = (
                f'projects/{project_id}/traces/{trace_id}'
            )

        print(json.dumps(structured, ensure_ascii=False), file=sys.stdout, flush=True)
    
    def verify_log_integrity(self) -> tuple[bool, Optional[str]]:
        """
        Verify the integrity of the entire audit log chain.

        Returns:
            Tuple of (is_valid, error_message) where error_message is None if valid
        """
        if not os.path.exists(self.audit_file_path):
            return False, "Audit log file does not exist"

        try:
            with open(self.audit_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return False, f"Error reading audit log: {str(e)}"

        if not lines:
            return False, "Audit log is empty"

        previous_hash = None
        for line_num, line in enumerate(lines, 1):
            error = self._verify_entry(line, line_num, previous_hash)
            if error:
                return False, error
            entry = json.loads(line)
            previous_hash = entry.get('entry_hash')

        return True, None

    def _verify_entry(
        self, line: str, line_num: int, expected_previous_hash: Optional[str]
    ) -> Optional[str]:
        """Verify a single audit log entry. Returns error message or None if valid."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return f"Invalid JSON at line {line_num}"

        if entry.get('previous_hash') != expected_previous_hash:
            return (
                f"Hash chain broken at line {line_num}: "
                f"expected previous_hash={expected_previous_hash}, got {entry.get('previous_hash')}"
            )

        stored_hash = entry.get('entry_hash')
        calculated_hash = self._calculate_hash(entry)
        if stored_hash != calculated_hash:
            return (
                f"Entry hash mismatch at line {line_num}: "
                f"stored={stored_hash}, calculated={calculated_hash}"
            )

        return None


# Global audit logger instance (thread-safe singleton)
_audit_logger = None
_audit_logger_lock = threading.Lock()


def get_audit_logger() -> AuditLogger:
    """
    Get the global audit logger instance (thread-safe singleton pattern).

    Uses double-checked locking for efficient thread-safe initialization.
    """
    global _audit_logger
    if _audit_logger is None:
        with _audit_logger_lock:
            # Double-check after acquiring lock
            if _audit_logger is None:
                _audit_logger = AuditLogger()
    return _audit_logger


def audit_ephi_access(
    action: str,
    resource_type: Optional[str] = None,
    details: Optional[dict[str, Any]] = None
):
    """
    Decorator to automatically audit ePHI access in Flask routes.

    Usage:
        @app.route('/patient/<patient_id>')
        @audit_ephi_access(action='view_patient_data', resource_type='Patient')
        def view_patient(patient_id):
            pass

    Args:
        action: Description of the action being performed
        resource_type: Type of FHIR resource being accessed
        details: Additional context to log
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            audit_logger = get_audit_logger()
            patient_id = session.get('patient_id') or kwargs.get('patient_id')
            user_id = session.get('user_id') or session.get('session_id', 'unknown')
            ip_address, user_agent, fhir_user = _get_request_context()

            audit_details = dict(details) if details else {}
            audit_details['endpoint'] = request.endpoint
            audit_details['method'] = request.method

            try:
                result = f(*args, **kwargs)
                audit_logger.log_event(
                    event_type='ePHI_ACCESS',
                    action=action,
                    patient_id=patient_id,
                    user_id=user_id,
                    fhir_user=fhir_user,
                    resource_type=resource_type,
                    outcome='success',
                    details=audit_details,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                return result
            except Exception as e:
                audit_logger.log_event(
                    event_type='ePHI_ACCESS',
                    action=action,
                    patient_id=patient_id,
                    user_id=user_id,
                    fhir_user=fhir_user,
                    resource_type=resource_type,
                    outcome='failure',
                    details={**audit_details, 'error': str(e)},
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise

        return wrapped
    return decorator


def _get_request_context() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract client IP, user agent, and FHIR user from Flask request context.

    - IP: Uses X-Forwarded-For (set by GAE/nginx load balancers) to get the
      real client IP instead of the load balancer's IP.
    - fhir_user: The OIDC fhirUser claim stored in session by OAuth callback,
      e.g. 'Practitioner/12345'. Essential for identifying *who* (NPI/doctor)
      performed the action in medical-legal audit trails.
    """
    if not has_request_context():
        return None, None, None

    # Extract real client IP from X-Forwarded-For (format: "client, proxy1, proxy2")
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        ip_address = forwarded_for.split(',')[0].strip()
    else:
        ip_address = request.remote_addr

    user_agent = request.headers.get('User-Agent')

    # Extract FHIR practitioner identity from session (set in OAuth callback)
    fhir_user = None
    try:
        fhir_user = session.get('fhir_user')
    except RuntimeError:
        # session not available (e.g., CDS Hooks endpoints without session middleware)
        pass

    return ip_address, user_agent, fhir_user


def _get_trace_context() -> dict[str, str]:
    """
    Extract GCP Cloud Trace context from request headers.

    X-Cloud-Trace-Context format: "TRACE_ID/SPAN_ID;o=TRACE_TRUE"
    Used for correlating audit entries with Cloud Trace spans.
    """
    if not has_request_context():
        return {}
    trace_header = request.headers.get('X-Cloud-Trace-Context')
    if not trace_header:
        return {}
    parts = trace_header.split('/')
    trace_id = parts[0] if parts else None
    if not trace_id:
        return {}
    return {'trace_id': trace_id, 'trace_header': trace_header}


def log_user_authentication(
    user_id: str, outcome: str, details: Optional[dict[str, Any]] = None
) -> None:
    """
    Log user authentication events.

    Args:
        user_id: User identifier
        outcome: 'success' or 'failure'
        details: Additional context (e.g., authentication method)
    """
    ip_address, user_agent, fhir_user = _get_request_context()
    get_audit_logger().log_event(
        event_type='AUTHENTICATION',
        action='user_login',
        user_id=user_id,
        fhir_user=fhir_user,
        outcome=outcome,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent
    )


def log_privilege_change(user_id: str, action: str, details: dict[str, Any]) -> None:
    """
    Log changes to user privileges.

    Args:
        user_id: User identifier
        action: Description of privilege change
        details: Details of the change
    """
    ip_address, user_agent, fhir_user = _get_request_context()
    get_audit_logger().log_event(
        event_type='PRIVILEGE_CHANGE',
        action=action,
        user_id=user_id,
        fhir_user=fhir_user,
        outcome='success',
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )


def log_audit_status_change(action: str, details: dict[str, Any]) -> None:
    """
    Log changes to audit log status (e.g., manual review, backup).

    Args:
        action: Description of the audit status change
        details: Details of the change
    """
    ip_address, user_agent, fhir_user = _get_request_context()
    get_audit_logger().log_event(
        event_type='AUDIT_STATUS_CHANGE',
        action=action,
        fhir_user=fhir_user,
        outcome='success',
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )

