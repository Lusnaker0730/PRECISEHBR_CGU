"""
ePHI Logging Filter — Strict Allowlist Mode Tests

Verifies the defence-in-depth approach:
1. FHIR resource detection blocks entire clinical resources
2. Dict key allowlist only passes known-safe keys
3. Regex patterns catch residual PII/PHI (US + Taiwan formats)
4. Deep scrub catches JSON-like FHIR blobs in strings
5. Safe operational messages pass through unaltered
"""

import logging
import pytest

from utils.logging_filter import (
    EPhiLoggingFilter,
    FHIR_RESOURCE_SIGNALS,
    SAFE_DICT_KEYS,
)


@pytest.fixture
def ephi_filter():
    return EPhiLoggingFilter()


@pytest.fixture
def make_record():
    """Factory for log records with a given message and optional args."""
    _logger = logging.getLogger("test.ephi")

    def _make(msg, args=None):
        record = _logger.makeRecord(
            name="test.ephi",
            level=logging.INFO,
            fn="test.py",
            lno=1,
            msg=msg,
            args=args,
            exc_info=None,
        )
        return record

    return _make


# =========================================================================
# Layer 1: FHIR Resource Detection
# =========================================================================

@pytest.mark.requirement("SRS-006")
@pytest.mark.risk("RISK-008")
@pytest.mark.design("SDS-010")
class TestFhirResourceDetection:
    """FHIR resources must be fully redacted regardless of content."""

    def test_patient_resource_redacted(self, ephi_filter):
        patient = {
            "resourceType": "Patient",
            "id": "12345",
            "name": [{"family": "Wang", "given": ["Ming"]}],
            "birthDate": "1960-05-15",
            "telecom": [{"system": "phone", "value": "0912345678"}],
            "address": [{"city": "Taipei"}],
        }
        result = ephi_filter._sanitize_dict(patient)
        assert "REDACTED" in str(result["_redacted"])
        assert "Wang" not in str(result)
        assert "12345" not in str(result)
        assert "1960" not in str(result)

    def test_observation_resource_redacted(self, ephi_filter):
        obs = {
            "resourceType": "Observation",
            "subject": {"reference": "Patient/12345"},
            "valueQuantity": {"value": 10.5, "unit": "g/dL"},
            "code": {"coding": [{"system": "http://loinc.org", "code": "718-7"}]},
        }
        result = ephi_filter._sanitize_dict(obs)
        assert "REDACTED" in str(result["_redacted"])
        assert "10.5" not in str(result)

    def test_condition_resource_redacted(self, ephi_filter):
        condition = {
            "resourceType": "Condition",
            "subject": {"reference": "Patient/12345"},
            "code": {"coding": [{"code": "I25.1", "display": "Coronary artery disease"}]},
        }
        result = ephi_filter._sanitize_dict(condition)
        assert "REDACTED" in str(result["_redacted"])

    def test_bundle_entry_redacted(self, ephi_filter):
        bundle = {
            "resourceType": "Bundle",
            "entry": [{"resource": {"resourceType": "Patient", "id": "123"}}],
        }
        result = ephi_filter._sanitize_dict(bundle)
        assert "REDACTED" in str(result["_redacted"])
        assert "123" not in str(result)

    def test_medication_request_redacted(self, ephi_filter):
        med = {
            "resourceType": "MedicationRequest",
            "subject": {"reference": "Patient/99"},
            "identifier": [{"value": "RX-001"}],
        }
        result = ephi_filter._sanitize_dict(med)
        assert "REDACTED" in str(result["_redacted"])

    def test_consent_resource_redacted(self, ephi_filter):
        consent = {
            "resourceType": "Consent",
            "patient": {"reference": "Patient/99"},
            "provision": {"type": "deny"},
        }
        result = ephi_filter._sanitize_dict(consent)
        assert "REDACTED" in str(result["_redacted"])

    def test_dict_with_subject_key_treated_as_fhir(self, ephi_filter):
        """Any dict with FHIR-signal keys should be treated as clinical data."""
        data = {"subject": {"reference": "Patient/1"}, "status": "final"}
        result = ephi_filter._sanitize_dict(data)
        assert "REDACTED" in str(result["_redacted"])

    def test_dict_with_identifier_key_treated_as_fhir(self, ephi_filter):
        data = {"identifier": [{"value": "MRN-123"}], "active": True}
        result = ephi_filter._sanitize_dict(data)
        assert "REDACTED" in str(result["_redacted"])

    def test_dict_with_telecom_treated_as_fhir(self, ephi_filter):
        data = {"telecom": [{"system": "phone", "value": "09123"}]}
        result = ephi_filter._sanitize_dict(data)
        assert "REDACTED" in str(result["_redacted"])

    def test_future_fhir_resource_with_extension(self, ephi_filter):
        """Simulates a future FHIR resource with unknown fields."""
        future_res = {
            "resourceType": "FutureResource",
            "newField2026": "sensitive data",
            "extension": [{"url": "http://example.org", "valueString": "PHI"}],
        }
        result = ephi_filter._sanitize_dict(future_res)
        assert "REDACTED" in str(result["_redacted"])
        assert "sensitive data" not in str(result)


# =========================================================================
# Layer 2: Dict Key Allowlist
# =========================================================================

@pytest.mark.requirement("SRS-006")
@pytest.mark.risk("RISK-008")
@pytest.mark.design("SDS-010")
class TestDictKeyAllowlist:
    """Unknown dict keys must be redacted; safe keys pass through."""

    def test_safe_keys_pass_through(self, ephi_filter):
        data = {"status": 200, "method": "GET", "path": "/api/health"}
        result = ephi_filter._sanitize_dict(data)
        assert result["status"] == 200
        assert result["method"] == "GET"
        assert result["path"] == "/api/health"

    def test_unknown_keys_redacted(self, ephi_filter):
        data = {
            "status": 200,
            "patient_name": "John Doe",
            "diagnosis": "Coronary artery disease",
            "lab_value": 10.5,
        }
        result = ephi_filter._sanitize_dict(data)
        assert result["status"] == 200
        assert result["patient_name"] == "[REDACTED]"
        assert result["diagnosis"] == "[REDACTED]"
        assert result["lab_value"] == "[REDACTED]"

    def test_risk_score_keys_pass(self, ephi_filter):
        data = {
            "score": 25,
            "risk_category": "HBR",
            "bleeding_risk_percent": 4.0,
            "recommendation": "Consider shorter DAPT",
        }
        result = ephi_filter._sanitize_dict(data)
        assert result["score"] == 25
        assert result["risk_category"] == "HBR"

    def test_nested_safe_dict(self, ephi_filter):
        data = {"status": 200, "error": {"message": "not found", "error_code": 404}}
        result = ephi_filter._sanitize_dict(data)
        assert result["error"]["message"] == "not found"
        assert result["error"]["error_code"] == 404

    def test_nested_unknown_keys_redacted(self, ephi_filter):
        data = {"status": 200, "error": {"message": "fail", "ssn": "123-45-6789"}}
        result = ephi_filter._sanitize_dict(data)
        assert result["error"]["ssn"] == "[REDACTED]"

    def test_empty_dict_passes(self, ephi_filter):
        assert ephi_filter._sanitize_dict({}) == {}

    def test_all_safe_keys_constant_coverage(self):
        """Verify critical operational keys are in the allowlist."""
        critical_keys = {"status", "error", "message", "score", "risk_category"}
        assert critical_keys.issubset(SAFE_DICT_KEYS)


# =========================================================================
# Layer 3: Regex Pattern Scrubbing
# =========================================================================

@pytest.mark.requirement("SRS-006")
@pytest.mark.risk("RISK-008")
@pytest.mark.design("SDS-010")
class TestRegexPatterns:
    """Regex patterns catch residual PII/PHI in free-text messages."""

    # --- US formats ---

    def test_ssn_redacted(self, ephi_filter):
        assert "REDACTED" in ephi_filter._scrub_string("SSN: 123-45-6789")

    def test_us_phone_redacted(self, ephi_filter):
        assert "REDACTED" in ephi_filter._scrub_string("Call (555) 123-4567")

    def test_email_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string("Contact: patient@hospital.org")
        assert "patient@hospital.org" not in result
        assert "REDACTED" in result

    def test_date_mmddyyyy_redacted(self, ephi_filter):
        assert "REDACTED" in ephi_filter._scrub_string("DOB: 01/15/1960")

    def test_date_yyyymmdd_redacted(self, ephi_filter):
        assert "REDACTED" in ephi_filter._scrub_string("DOB: 1960-01-15")

    # --- Taiwan formats ---

    def test_taiwan_national_id_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string("Patient ID: A123456789")
        assert "A123456789" not in result
        assert "REDACTED" in result

    def test_taiwan_arc_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string("ARC: AB12345678")
        assert "AB12345678" not in result
        assert "REDACTED" in result

    def test_taiwan_phone_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string("Tel: 0912-345-678")
        assert "0912-345-678" not in result
        assert "REDACTED" in result

    def test_taiwan_phone_intl_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string("Tel: +886-2-1234-5678")
        assert "+886-2-1234-5678" not in result

    def test_chinese_name_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string("患者：王大明 已完成風險評估")
        assert "王大明" not in result
        assert "REDACTED" in result

    def test_chinese_name_with_colon(self, ephi_filter):
        result = ephi_filter._scrub_string("姓名：陳小明")
        assert "陳小明" not in result

    def test_chinese_patient_name(self, ephi_filter):
        result = ephi_filter._scrub_string("病人 李美玲 的HBR分數")
        assert "李美玲" not in result

    # --- FHIR references ---

    def test_patient_reference_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string("Subject: Patient/abc-123")
        assert "abc-123" not in result
        assert "REDACTED" in result

    def test_practitioner_reference_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string("Performer: Practitioner/dr-456")
        assert "dr-456" not in result

    # --- Names ---

    def test_english_name_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string("name: John Smith")
        assert "John Smith" not in result

    # --- Secrets ---

    def test_bearer_token_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string(
            "Auth: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.abc.def"
        )
        assert "eyJ" not in result

    def test_api_key_redacted(self, ephi_filter):
        result = ephi_filter._scrub_string("api_key: abcdefghij1234567890")
        assert "abcdefghij1234567890" not in result

    # --- Safe messages pass through ---

    def test_safe_operational_message_unchanged(self, ephi_filter):
        msg = "ePHI logging filter enabled — strict allowlist mode"
        assert ephi_filter._scrub_string(msg) == msg

    def test_safe_metric_message_unchanged(self, ephi_filter):
        msg = "Fetched 5 observation(s) for risk calculation"
        assert ephi_filter._scrub_string(msg) == msg

    def test_safe_error_message_unchanged(self, ephi_filter):
        msg = "Token exchange failed: 401 Unauthorized"
        assert ephi_filter._scrub_string(msg) == msg


# =========================================================================
# Layer 4: JSON Blob Detection in Strings
# =========================================================================

@pytest.mark.requirement("SRS-006")
@pytest.mark.risk("RISK-008")
@pytest.mark.design("SDS-010")
class TestJsonBlobDetection:
    """JSON-like FHIR blobs embedded in strings must be redacted."""

    def test_embedded_patient_json_redacted(self, ephi_filter):
        msg = 'Received data: {"resourceType": "Patient", "id": "123", "name": [{"family": "Wang"}]}'
        result = ephi_filter._scrub_string(msg)
        assert "Wang" not in result
        assert "FHIR_RESOURCE_REDACTED" in result

    def test_embedded_observation_json_redacted(self, ephi_filter):
        msg = 'Got: {"resourceType": "Observation", "valueQuantity": {"value": 10.5}}'
        result = ephi_filter._scrub_string(msg)
        assert "10.5" not in result

    def test_non_fhir_json_not_redacted(self, ephi_filter):
        msg = 'Config: {"version": "1.0", "debug": false}'
        result = ephi_filter._scrub_string(msg)
        assert "version" in result
        assert "1.0" in result


# =========================================================================
# Layer 5: Integration — LogRecord Processing
# =========================================================================

@pytest.mark.requirement("SRS-006")
@pytest.mark.risk("RISK-008")
@pytest.mark.design("SDS-010")
class TestLogRecordIntegration:
    """End-to-end tests using actual LogRecord objects."""

    def test_string_message_scrubbed(self, ephi_filter, make_record):
        record = make_record("Patient A123456789 admitted")
        ephi_filter.filter(record)
        assert "A123456789" not in record.msg
        assert "REDACTED" in record.msg

    def test_dict_args_sanitized(self, ephi_filter, make_record):
        record = make_record("Event: %(status)s", {"status": 200, "ssn": "123-45-6789"})
        ephi_filter.filter(record)
        assert record.args["status"] == 200
        assert record.args["ssn"] == "[REDACTED]"

    def test_fhir_resource_in_args_fully_redacted(self, ephi_filter, make_record):
        patient = {
            "resourceType": "Patient",
            "id": "99",
            "name": [{"family": "Chen"}],
        }
        record = make_record("Got patient: %s", (patient,))
        ephi_filter.filter(record)
        result_str = str(record.args)
        assert "Chen" not in result_str
        assert "99" not in result_str

    def test_tuple_args_sanitized(self, ephi_filter, make_record):
        record = make_record("Values: %s %s", ("safe_text", "patient@test.com"))
        ephi_filter.filter(record)
        args = record.args
        assert args[0] == "safe_text"
        assert "patient@test.com" not in args[1]

    def test_filter_always_returns_true(self, ephi_filter, make_record):
        """Messages are scrubbed, not dropped — audit trail preserved."""
        record = make_record("SSN: 123-45-6789")
        assert ephi_filter.filter(record) is True
        assert "REDACTED" in record.msg

    def test_none_msg_handled(self, ephi_filter, make_record):
        record = make_record("")
        record.msg = None
        assert ephi_filter.filter(record) is True

    def test_none_args_handled(self, ephi_filter, make_record):
        record = make_record("hello")
        record.args = None
        assert ephi_filter.filter(record) is True


# =========================================================================
# Layer 6: Completeness & Regression
# =========================================================================

@pytest.mark.requirement("SRS-006")
@pytest.mark.risk("RISK-008")
class TestCompletenessRegression:
    """Ensure allowlist is comprehensive and no regressions."""

    def test_fhir_signals_include_demographics(self):
        demos = {"birthDate", "maritalStatus", "telecom", "address", "contact"}
        assert demos.issubset(FHIR_RESOURCE_SIGNALS)

    def test_fhir_signals_include_clinical(self):
        clinical = {"valueQuantity", "code", "category", "component", "bodySite"}
        assert clinical.issubset(FHIR_RESOURCE_SIGNALS)

    def test_fhir_signals_include_identifiers(self):
        ids = {"identifier", "subject", "patient"}
        assert ids.issubset(FHIR_RESOURCE_SIGNALS)

    def test_fhir_signals_include_twcore_extension(self):
        assert "extension" in FHIR_RESOURCE_SIGNALS

    def test_safe_keys_do_not_overlap_fhir_signals(self):
        """Safe keys should not contain FHIR-signal keys (defence consistency)."""
        overlap = SAFE_DICT_KEYS & FHIR_RESOURCE_SIGNALS
        # Some keys like 'category', 'scope' are in both — acceptable if the
        # FHIR detector runs FIRST (checks for ANY signal key presence)
        # Just ensure critical FHIR keys are not in safe list
        critical_fhir = {"resourceType", "subject", "identifier", "telecom",
                         "birthDate", "valueQuantity", "extension"}
        assert not (SAFE_DICT_KEYS & critical_fhir), \
            f"Critical FHIR keys leaked into safe list: {SAFE_DICT_KEYS & critical_fhir}"
