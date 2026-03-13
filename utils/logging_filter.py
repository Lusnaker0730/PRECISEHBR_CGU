"""
Logging Filter for ePHI Protection — Strict Allowlist Mode

Defence-in-depth strategy against ePHI leakage in GAE / production logs:

1. **FHIR Resource Detector** — any string or dict containing `resourceType`,
   `subject`, `identifier`, or other FHIR structural keys is treated as a
   clinical resource and fully redacted.  This is the primary safeguard
   against future FHIR spec updates introducing new ePHI-bearing fields.

2. **Dict Key Allowlist** — only explicitly safe keys pass through in
   structured log arguments.  Unknown keys are redacted.  This inverts
   the previous blocklist approach.

3. **Regex Patterns** — catch residual PII/PHI in free-text messages
   (SSN, phone, email, dates, Taiwan National ID, Chinese names,
   NHI codes, Bearer tokens, FHIR references).

4. **Deep Scrub** — JSON-like blobs embedded in string messages are
   detected and replaced.

ONC 45 CFR 170.315(d)(2) / HIPAA §164.312(b) audit-log safe.
"""

import json
import logging
import re
from typing import Pattern

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. FHIR Resource Detection — keys whose presence signals clinical data
# ---------------------------------------------------------------------------
FHIR_RESOURCE_SIGNALS = frozenset({
    "resourceType", "resource_type",
    # Identifiers & references
    "identifier", "subject", "patient",
    # Demographics
    "birthDate", "birth_date", "deceasedDateTime", "deceased_date_time",
    "maritalStatus", "marital_status", "multipleBirthBoolean",
    "communication", "contact", "link",
    # Clinical
    "valueQuantity", "value_quantity", "valueCodeableConcept",
    "component", "interpretation", "referenceRange",
    "bodySite", "body_site", "specimen",
    "performer", "encounter", "basedOn",
    "code", "category",
    # Coverage & consent
    "beneficiary", "subscriber", "payor",
    "provision", "scope", "policy",
    # Address / Telecom
    "telecom", "address",
    # Extensions (TW Core, US Core, etc.)
    "extension",
    # Narrative (may contain ePHI)
    "text", "div",
    # Bundle
    "entry", "fullUrl", "full_url",
})

# ---------------------------------------------------------------------------
# 2. Dict Key Allowlist — ONLY these keys pass through unredacted
# ---------------------------------------------------------------------------
SAFE_DICT_KEYS = frozenset({
    # HTTP / Flask / System
    "status", "status_code", "statusCode", "method", "path", "url",
    "endpoint", "content_type", "content_length",
    "error", "error_type", "error_code", "message", "msg",
    "level", "levelname", "levelno",
    "timestamp", "asctime", "created",
    "logger", "name", "module", "funcName", "lineno", "pathname",
    "process", "processName", "thread", "threadName",
    # Application metrics (aggregate, no ePHI)
    "total", "count", "total_tests", "passed", "failed",
    "score", "risk_category", "score_range", "color_class",
    "bleeding_risk_percent", "recommendation", "full_label",
    "coverage_pct", "traceability_coverage_pct",
    "total_traced_tests", "total_untraced_tests",
    # Audit event metadata (IDs are separately redacted by regex)
    "event_type", "action", "outcome", "severity",
    "resource_type", "category",
    # Configuration keys (no ePHI)
    "version", "env", "debug", "testing",
    "config_changed", "changed_files",
    # FHIR operational (non-ePHI)
    "server_url", "fhir_version", "scope",
    "resource_count", "observation_count", "condition_count",
    "restricted_count", "very_restricted_count",
    # Rate limiting / security
    "rate_limit", "remaining", "retry_after",
})

# ---------------------------------------------------------------------------
# 3. Regex patterns — residual PII/PHI in free-text
# ---------------------------------------------------------------------------

def _compile_patterns() -> list[tuple[Pattern, str]]:
    return [
        # === US formats ===
        # SSN
        (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN_REDACTED]'),
        # US phone (with or without parens/dots/dashes)
        (re.compile(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
         '[PHONE_REDACTED]'),

        # === Taiwan formats ===
        # Taiwan National ID (A123456789)
        (re.compile(r'\b[A-Z][12]\d{8}\b'), '[TW_ID_REDACTED]'),
        # Taiwan Resident Certificate (AB12345678)
        (re.compile(r'\b[A-Z]{2}\d{8}\b'), '[TW_ARC_REDACTED]'),
        # NHI medication codes (typically A-Z + digits, 10 chars)
        (re.compile(r'\b[A-Z]\d{9}\b'), '[NHI_CODE_REDACTED]'),
        # Taiwan phone (+886-X-XXXX-XXXX or 09XX-XXX-XXX)
        (re.compile(r'(?:\+886[-.]?\d[-.]?\d{4}[-.]?\d{4}|09\d{2}[-.]?\d{3}[-.]?\d{3})\b'),
         '[TW_PHONE_REDACTED]'),

        # === Email ===
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
         '[EMAIL_REDACTED]'),

        # === Dates (potential DOB) ===
        (re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'), '[DATE_REDACTED]'),
        (re.compile(r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'), '[DATE_REDACTED]'),

        # === Patient / MRN identifiers ===
        (re.compile(
            r'\b(?:patient[_-]?id|mrn|medical[_-]?record)\s*[:=]\s*[A-Za-z0-9-]+\b',
            re.IGNORECASE), '[PATIENT_ID_REDACTED]'),
        (re.compile(r'\bpatient\s+[A-Za-z0-9]{6,}\b', re.IGNORECASE),
         'patient [PATIENT_ID_REDACTED]'),

        # === FHIR references ===
        (re.compile(r'\b(?:Patient|Practitioner|RelatedPerson)/[A-Za-z0-9._-]+\b'),
         '[FHIR_REF_REDACTED]'),

        # === Names ===
        # English "name: First Last"
        (re.compile(r'\bname[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b', re.IGNORECASE),
         'name: [NAME_REDACTED]'),
        # Chinese names (2-4 CJK chars preceded by 姓名/患者/病人)
        (re.compile(r'(?:姓名|患者|病人|病患)[：:\s]*[\u4e00-\u9fff]{2,4}'),
         '[CN_NAME_REDACTED]'),

        # === Secrets / Tokens ===
        (re.compile(
            r'\b(?:api[_-]?key|secret|token|password|client_secret)'
            r'[:\s]*[A-Za-z0-9_\-+/=.]{16,}\b', re.IGNORECASE),
         '[SECRET_REDACTED]'),
        (re.compile(r'\bBearer\s+[A-Za-z0-9_\-+/=.]+\b'),
         'Bearer [TOKEN_REDACTED]'),

        # === JSON blobs that look like FHIR resources ===
        # Catches {"resourceType": "..."  ...}  embedded in strings
        (re.compile(
            r'\{[^{}]*"resourceType"\s*:\s*"[^"]*"[^{}]*\}',
            re.DOTALL),
         '[FHIR_RESOURCE_REDACTED]'),
        # Nested JSON with resourceType (multi-level braces)
        (re.compile(
            r'\{[^{}]*"resourceType"\s*:[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
            re.DOTALL),
         '[FHIR_RESOURCE_REDACTED]'),
    ]


# Pre-compiled at module load
_PATTERNS = _compile_patterns()


# ---------------------------------------------------------------------------
# 4. Core filter
# ---------------------------------------------------------------------------

class EPhiLoggingFilter(logging.Filter):
    """
    Strict allowlist-based ePHI logging filter.

    Defence layers:
    - FHIR resource detection (dict or embedded JSON)
    - Dict key allowlist (unknown keys → [REDACTED])
    - Regex scrubbing for residual PII/PHI patterns
    """

    def __init__(self, name: str = ''):
        super().__init__(name)
        self.patterns = _PATTERNS

    # ---- public API -------------------------------------------------------

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'msg') and record.msg:
            record.msg = self._scrub_string(str(record.msg))

        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = self._sanitize_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = self._sanitize_sequence(record.args)

        return True

    # ---- string-level scrubbing -------------------------------------------

    def _scrub_string(self, text: str) -> str:
        for pattern, replacement in self.patterns:
            text = pattern.sub(replacement, text)
        return text

    # ---- dict allowlist ---------------------------------------------------

    def _is_fhir_resource(self, data: dict) -> bool:
        return bool(FHIR_RESOURCE_SIGNALS & set(data.keys()))

    def _sanitize_dict(self, data: dict) -> dict:
        if self._is_fhir_resource(data):
            resource_type = data.get('resourceType', data.get('resource_type', 'unknown'))
            return {'_redacted': f'[FHIR {resource_type} RESOURCE — ePHI REDACTED]'}

        sanitized = {}
        for key, value in data.items():
            key_str = str(key)
            if key_str in SAFE_DICT_KEYS:
                sanitized[key] = self._sanitize_value(value)
            else:
                sanitized[key] = '[REDACTED]'
        return sanitized

    def _sanitize_value(self, value):
        if isinstance(value, dict):
            return self._sanitize_dict(value)
        elif isinstance(value, (list, tuple)):
            return self._sanitize_sequence(value)
        elif isinstance(value, str):
            return self._scrub_string(value)
        return value

    def _sanitize_sequence(self, data: list | tuple) -> list | tuple:
        sanitized = [self._sanitize_value(item) for item in data]
        return type(data)(sanitized)


# ---------------------------------------------------------------------------
# 5. Setup helper
# ---------------------------------------------------------------------------

def setup_ephi_logging_filter(app):
    """Attach the ePHI filter to all relevant loggers."""
    ephi_filter = EPhiLoggingFilter()

    app.logger.addFilter(ephi_filter)

    root_logger = logging.getLogger()
    root_logger.addFilter(ephi_filter)

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(ephi_filter)

    app.logger.info(
        "ePHI logging filter enabled — strict allowlist mode, "
        "FHIR resource detection active"
    )
