"""
ONC Compliance: 45 CFR 170.315 (d)(2) - Auditable Events and Tamper-resistance

This module provides comprehensive audit logging functionality for tracking all
access to electronic Protected Health Information (ePHI).

Features:
- Records all ePHI access events with required metadata
- Implements tamper-resistance through cryptographic hashing
- Stores logs in append-only JSON Lines format
- Provides query and analysis capabilities
"""

import os
import json
import hashlib
import datetime
from typing import Optional, Dict, Any
from functools import wraps
from flask import session, request
import logging

# Configure module logger
logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Secure audit logging system for ePHI access tracking.
    
    Implements tamper-resistance through cryptographic chain:
    Each log entry includes a hash of the previous entry, creating
    an immutable audit trail.
    """
    
    def __init__(self, audit_file_path=None):
        """
        Initialize the audit logger.
        
        Args:
            audit_file_path: Path to the audit log file (auto-detected if None)
        """
        # Auto-detect appropriate path based on environment
        if audit_file_path is None:
            if os.environ.get('GAE_ENV', '').startswith('standard'):
                # Running on Google App Engine - use secure temp directory
                import tempfile
                audit_file_path = os.path.join(tempfile.gettempdir(), 'audit', 'audit_log.jsonl')
            else:
                # Running locally - use instance directory
                audit_file_path = 'instance/audit/audit_log.jsonl'
        
        self.audit_file_path = audit_file_path
        self.audit_dir = os.path.dirname(audit_file_path)
        
        # Create audit directory if it doesn't exist
        try:
            os.makedirs(self.audit_dir, exist_ok=True)
        except OSError as e:
            logger.warning(f"Could not create audit directory {self.audit_dir}: {e}. Audit logging may be limited.")
        
        # Initialize audit log file with header if it doesn't exist
        if not os.path.exists(self.audit_file_path):
            self._initialize_audit_log()
        
        # Load the last hash for chain verification
        self.last_hash = self._get_last_hash()
    
    def _initialize_audit_log(self):
        """Initialize audit log file with metadata header"""
        try:
            metadata = {
                'log_type': 'AUDIT_LOG_HEADER',
                'application': 'SMART on FHIR PRECISE-HBR Calculator',
                'compliance_standard': '45 CFR 170.315 (d)(2)',
                'initialized_at': datetime.datetime.utcnow().isoformat() + 'Z',
                'version': '1.0',
                'hash_algorithm': 'SHA-256',
                'previous_hash': None,
                'entry_hash': None
            }
            # Calculate hash of metadata
            metadata['entry_hash'] = self._calculate_hash(metadata)
            
            with open(self.audit_file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(metadata, ensure_ascii=False) + '\n')
            
            logger.info(f"Audit log initialized: {self.audit_file_path}")
        except OSError as e:
            logger.warning(f"Could not initialize audit log file {self.audit_file_path}: {e}. Continuing without file-based audit logging.")
    
    def _get_last_hash(self) -> Optional[str]:
        """
        Retrieve the hash of the last log entry for chain verification.
        
        Returns:
            The last entry hash, or None if log is empty
        """
        if not os.path.exists(self.audit_file_path):
            return None
        
        try:
            with open(self.audit_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    return last_entry.get('entry_hash')
        except (OSError, IOError) as e:
            logger.warning(f"Could not read audit log (possibly read-only filesystem): {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading last hash: {e}")
        
        return None
    
    def _calculate_hash(self, entry_data: Dict[str, Any]) -> str:
        """
        Calculate SHA-256 hash of an audit entry.
        
        Creates a deterministic hash by:
        1. Excluding the 'entry_hash' field itself
        2. Sorting keys for consistency
        3. Using compact JSON representation
        
        Args:
            entry_data: The audit entry dictionary
            
        Returns:
            Hexadecimal hash string
        """
        # Create a copy without the entry_hash field
        data_to_hash = {k: v for k, v in entry_data.items() if k != 'entry_hash'}
        
        # Convert to JSON string with sorted keys for consistency
        json_str = json.dumps(data_to_hash, sort_keys=True, ensure_ascii=False)
        
        # Calculate SHA-256 hash
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    def log_event(self,
                  event_type: str,
                  action: str,
                  patient_id: Optional[str] = None,
                  user_id: Optional[str] = None,
                  resource_type: Optional[str] = None,
                  resource_ids: Optional[list] = None,
                  outcome: str = 'success',
                  details: Optional[Dict[str, Any]] = None,
                  ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None) -> Dict[str, Any]:
        """
        Log an auditable event.
        
        Args:
            event_type: Type of event (e.g., 'ePHI_ACCESS', 'DATA_EXPORT', 'LOGIN')
            action: Specific action performed (e.g., 'view_patient_data', 'calculate_risk')
            patient_id: Patient identifier (if applicable)
            user_id: User/session identifier
            resource_type: FHIR resource type accessed (e.g., 'Patient', 'Observation')
            resource_ids: List of specific resource IDs accessed
            outcome: 'success' or 'failure'
            details: Additional context information
            ip_address: Client IP address
            user_agent: Client user agent string
            
        Returns:
            The logged audit entry
        """
        # Create audit entry
        audit_entry = {
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'event_type': event_type,
            'action': action,
            'user_id': user_id,
            'patient_id': patient_id,
            'resource_type': resource_type,
            'resource_ids': resource_ids or [],
            'outcome': outcome,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'details': details or {},
            'previous_hash': self.last_hash
        }
        
        # Calculate hash for this entry (creates tamper-evident chain)
        audit_entry['entry_hash'] = self._calculate_hash(audit_entry)
        
        # Write to audit log
        try:
            with open(self.audit_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + '\n')
            
            # Update last hash
            self.last_hash = audit_entry['entry_hash']
            
            # Also log to application logger (but without sensitive details)
            logger.info(f"AUDIT: {event_type} - {action} - User:{user_id} - Patient:{patient_id} - Outcome:{outcome}")
            
            return audit_entry
            
        except (OSError, IOError) as e:
            # In App Engine or read-only filesystem, log to console/monitoring instead
            logger.warning(f"Could not write to audit log file (read-only filesystem): {e}")
            logger.info(f"AUDIT_ENTRY: {json.dumps(audit_entry)}")  # Log to console for Cloud Logging
            return audit_entry  # Continue operation
        except Exception as e:
            logger.error(f"CRITICAL: Failed to write audit log: {e}")
            # In production, this should trigger an alert
            raise
    
    def verify_log_integrity(self) -> tuple[bool, Optional[str]]:
        """
        Verify the integrity of the entire audit log chain.
        
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if the entire chain is valid
            - error_message: Description of tampering if detected, None otherwise
        """
        if not os.path.exists(self.audit_file_path):
            return False, "Audit log file does not exist"
        
        try:
            with open(self.audit_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                return False, "Audit log is empty"
            
            previous_hash = None
            
            for line_num, line in enumerate(lines, 1):
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    return False, f"Invalid JSON at line {line_num}"
                
                # Verify the hash chain
                if entry.get('previous_hash') != previous_hash:
                    return False, f"Hash chain broken at line {line_num}: expected previous_hash={previous_hash}, got {entry.get('previous_hash')}"
                
                # Verify the entry's own hash
                stored_hash = entry.get('entry_hash')
                calculated_hash = self._calculate_hash(entry)
                
                if stored_hash != calculated_hash:
                    return False, f"Entry hash mismatch at line {line_num}: stored={stored_hash}, calculated={calculated_hash}"
                
                previous_hash = stored_hash
            
            return True, None
            
        except Exception as e:
            return False, f"Error during verification: {str(e)}"


# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance (singleton pattern)"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def audit_ephi_access(action: str, 
                     resource_type: Optional[str] = None,
                     details: Optional[Dict[str, Any]] = None):
    """
    Decorator to automatically audit ePHI access in Flask routes.
    
    Usage:
        @app.route('/patient/<patient_id>')
        @audit_ephi_access(action='view_patient_data', resource_type='Patient')
        def view_patient(patient_id):
            # Your code here
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
            
            # Extract context from Flask request and session
            patient_id = session.get('patient_id') or kwargs.get('patient_id')
            user_id = session.get('user_id') or session.get('session_id', 'unknown')
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', 'unknown')
            
            # Prepare details
            audit_details = details or {}
            audit_details['endpoint'] = request.endpoint
            audit_details['method'] = request.method
            
            try:
                # Execute the wrapped function
                result = f(*args, **kwargs)
                
                # Log successful access
                audit_logger.log_event(
                    event_type='ePHI_ACCESS',
                    action=action,
                    patient_id=patient_id,
                    user_id=user_id,
                    resource_type=resource_type,
                    outcome='success',
                    details=audit_details,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                return result
                
            except Exception as e:
                # Log failed access
                audit_logger.log_event(
                    event_type='ePHI_ACCESS',
                    action=action,
                    patient_id=patient_id,
                    user_id=user_id,
                    resource_type=resource_type,
                    outcome='failure',
                    details={**audit_details, 'error': str(e)},
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Re-raise the exception
                raise
        
        return wrapped
    return decorator


def log_user_authentication(user_id: str, outcome: str, details: Optional[Dict[str, Any]] = None):
    """
    Log user authentication events.
    
    Args:
        user_id: User identifier
        outcome: 'success' or 'failure'
        details: Additional context (e.g., authentication method)
    """
    audit_logger = get_audit_logger()
    
    audit_logger.log_event(
        event_type='AUTHENTICATION',
        action='user_login',
        user_id=user_id,
        outcome=outcome,
        details=details or {},
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None
    )


def log_privilege_change(user_id: str, action: str, details: Dict[str, Any]):
    """
    Log changes to user privileges.
    
    Args:
        user_id: User identifier
        action: Description of privilege change
        details: Details of the change
    """
    audit_logger = get_audit_logger()
    
    audit_logger.log_event(
        event_type='PRIVILEGE_CHANGE',
        action=action,
        user_id=user_id,
        outcome='success',
        details=details,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None
    )


def log_audit_status_change(action: str, details: Dict[str, Any]):
    """
    Log changes to audit log status (e.g., manual review, backup).
    
    Args:
        action: Description of the audit status change
        details: Details of the change
    """
    audit_logger = get_audit_logger()
    
    audit_logger.log_event(
        event_type='AUDIT_STATUS_CHANGE',
        action=action,
        outcome='success',
        details=details,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None
    )

