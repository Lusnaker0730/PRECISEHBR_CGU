"""
Logging Filter for ePHI Protection
This module provides logging filters to prevent ePHI from being logged.
"""

import logging
import re
from typing import Pattern, List


class EPhiLoggingFilter(logging.Filter):
    """
    Filter to redact potential ePHI from log messages.
    
    This filter identifies and redacts patterns that may contain:
    - Patient identifiers (MRN, Patient ID)
    - Social Security Numbers
    - Email addresses
    - Phone numbers
    - Dates of birth
    - Full names in common formats
    - FHIR resource IDs that might contain PHI
    """
    
    def __init__(self, name: str = ''):
        super().__init__(name)
        self.patterns: List[tuple[Pattern, str]] = self._compile_patterns()
    
    def _compile_patterns(self) -> List[tuple[Pattern, str]]:
        """
        Compile regex patterns for ePHI detection.
        Returns a list of (pattern, replacement) tuples.
        """
        return [
            # Social Security Numbers (XXX-XX-XXXX)
            (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN_REDACTED]'),
            
            # Phone numbers (various formats)
            (re.compile(r'\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b'), '[PHONE_REDACTED]'),
            
            # Email addresses
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_REDACTED]'),
            
            # Dates (MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD)
            (re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'), '[DATE_REDACTED]'),
            (re.compile(r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'), '[DATE_REDACTED]'),
            
            # Patient ID / MRN patterns
            (re.compile(r'\b(?:patient[_-]?id|mrn|medical[_-]?record)[:\s]*[A-Za-z0-9-]+\b', re.IGNORECASE), '[PATIENT_ID_REDACTED]'),
            
            # FHIR resource IDs with Patient prefix
            (re.compile(r'\bPatient/[A-Za-z0-9-]+\b'), 'Patient/[REDACTED]'),
            
            # Common name patterns (First Last format - be cautious with this)
            # Only redact if it appears in sensitive contexts
            (re.compile(r'\bname[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b', re.IGNORECASE), 'name: [NAME_REDACTED]'),
            
            # API Keys and Secrets (catch any that might slip through)
            (re.compile(r'\b(?:api[_-]?key|secret|token|password)[:\s]*[A-Za-z0-9_\-+/=]{16,}\b', re.IGNORECASE), '[SECRET_REDACTED]'),
            
            # Access tokens
            (re.compile(r'\b(?:Bearer\s+)[A-Za-z0-9_\-+/=.]+\b'), 'Bearer [TOKEN_REDACTED]'),
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and redact ePHI from log record.
        
        Args:
            record: The log record to filter
            
        Returns:
            True to allow the record to be logged (after redaction)
        """
        if hasattr(record, 'msg') and record.msg:
            message = str(record.msg)
            
            # Apply all redaction patterns
            for pattern, replacement in self.patterns:
                message = pattern.sub(replacement, message)
            
            record.msg = message
        
        # Also filter args if present
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = self._redact_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = self._redact_sequence(record.args)
        
        return True
    
    def _redact_dict(self, data: dict) -> dict:
        """Redact sensitive values in dictionary."""
        redacted = {}
        sensitive_keys = {
            'ssn', 'social_security', 'patient_id', 'mrn', 'email', 
            'phone', 'dob', 'date_of_birth', 'name', 'address',
            'api_key', 'secret', 'token', 'password', 'client_secret'
        }
        
        for key, value in data.items():
            key_lower = str(key).lower().replace('_', '').replace('-', '')
            
            # Check if key is sensitive
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                redacted[key] = '[REDACTED]'
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, (list, tuple)):
                redacted[key] = self._redact_sequence(value)
            else:
                # Apply pattern matching to string values
                if isinstance(value, str):
                    redacted_value = value
                    for pattern, replacement in self.patterns:
                        redacted_value = pattern.sub(replacement, redacted_value)
                    redacted[key] = redacted_value
                else:
                    redacted[key] = value
        
        return redacted
    
    def _redact_sequence(self, data: tuple | list) -> tuple | list:
        """Redact sensitive values in sequence."""
        redacted = []
        for item in data:
            if isinstance(item, dict):
                redacted.append(self._redact_dict(item))
            elif isinstance(item, (list, tuple)):
                redacted.append(self._redact_sequence(item))
            elif isinstance(item, str):
                redacted_item = item
                for pattern, replacement in self.patterns:
                    redacted_item = pattern.sub(replacement, redacted_item)
                redacted.append(redacted_item)
            else:
                redacted.append(item)
        
        return type(data)(redacted)


def setup_ephi_logging_filter(app):
    """
    Set up ePHI logging filter for Flask application.
    
    Args:
        app: Flask application instance
    """
    ephi_filter = EPhiLoggingFilter()
    
    # Add filter to app logger
    app.logger.addFilter(ephi_filter)
    
    # Add filter to root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(ephi_filter)
    
    # Add filter to werkzeug logger (Flask's request logger)
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(ephi_filter)
    
    app.logger.info("ePHI logging filter enabled - sensitive data will be redacted from logs")


def test_filter():
    """Test the ePHI filter with sample data."""
    import logging
    
    # Setup test logger
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('test')
    
    # Add filter
    ephi_filter = EPhiLoggingFilter()
    logger.addFilter(ephi_filter)
    
    # Test cases - using obviously fake/placeholder values to avoid Gitleaks false positives
    test_messages = [
        "Patient SSN: XXX-XX-XXXX",
        "Contact phone: (555) 000-0000",
        "Email: test@example.com",
        "DOB: 01/01/2000",
        "Patient ID: TEST123",
        "Bearer [token-placeholder]",
        "API Key: [key-placeholder]",
    ]
    
    print("\n=== Testing ePHI Filter ===")
    for msg in test_messages:
        print(f"\nOriginal: {msg}")
        logger.info(msg)
    

if __name__ == '__main__':
    test_filter()

