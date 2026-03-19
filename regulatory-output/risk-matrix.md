# PRECISE-HBR Risk Analysis Matrix (ISO 14971:2019)

> **Document ID**: RISK-MATRIX-001
> **Product**: PRECISE-HBR SMART on FHIR Clinical Decision Support
> **Classification**: IEC 62304 Class B / Class C (per item)
> **Generated**: 2026-03-19
> **Standard**: ISO 14971:2019 Medical devices — Application of risk management

---

## 1. Risk Acceptability Criteria

| Risk Level | Score Range | Acceptability |
|-----------|------------|---------------|
| **Low** | 1–4 | Acceptable |
| **Medium** | 5–8 | Acceptable with monitoring |
| **High** | 9–12 | Requires risk control, re-evaluate |
| **Very High** | 13–25 | Unacceptable — must reduce |

### Severity Scale (S)

| Score | Level | Description |
|-------|-------|-------------|
| 1 | Negligible | No impact on patient safety or data |
| 2 | Minor | Inconvenience, no clinical impact |
| 3 | Serious | Incorrect clinical recommendation possible |
| 4 | Critical | ePHI breach, wrong treatment decision |
| 5 | Catastrophic | Patient harm or death |

### Probability Scale (P)

| Score | Level | Description |
|-------|-------|-------------|
| 1 | Rare | Requires sophisticated attack + insider access |
| 2 | Unlikely | Requires technical skill + specific conditions |
| 3 | Possible | Known attack vector, tools available |
| 4 | Likely | Common vulnerability, easily exploitable |
| 5 | Frequent | Occurs in normal operation |

---

## 2. Risk Matrix — Pre-Control vs Post-Control

### 2.1 Clinical Risks (Class C)

| Risk ID | Issue | Hazard | S | P(pre) | Risk(pre) | Control Measures | P(post) | Risk(post) | Status |
|---------|-------|--------|---|--------|-----------|-----------------|---------|------------|--------|
| RISK-001 | [#25](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/25) | Score calculation error → wrong DAPT decision | 5 | 2 | **10 High** | Config-driven coefficients, golden dataset validation, truncation logic | 1 | **5 Medium** | ✅ Controlled |
| RISK-002 | [#26](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/26) | Risk classification threshold error | 5 | 2 | **10 High** | Configurable thresholds, boundary value tests | 1 | **5 Medium** | ✅ Controlled |
| RISK-009 | [#33](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/33) | BOLA/IDOR — patient data confusion | 5 | 2 | **10 High** | @require_patient_context, resource ownership validation | 1 | **5 Medium** | ✅ Controlled |

### 2.2 Security Risks — OAuth2/OIDC (Class B)

| Risk ID | Issue | Hazard | S | P(pre) | Risk(pre) | Control Measures | P(post) | Risk(post) | Status |
|---------|-------|--------|---|--------|-----------|-----------------|---------|------------|--------|
| RISK-005 | [#29](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/29) | Auth bypass / token theft | 4 | 2 | **8 Medium** | PKCE + State + OIDC signature | 1 | **4 Low** | ✅ Controlled |
| RISK-010 | [#66](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/66) | SSRF via ISS forgery | 4 | 3 | **12 High** | validate_url() allowlist, private IP block | 1 | **4 Low** | ✅ Controlled |
| RISK-011 | [#67](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/67) | Token endpoint MITM tampering | 4 | 2 | **8 Medium** | HTTPS + domain validation + SSRF block | 1 | **4 Low** | ✅ Controlled |
| RISK-012 | [#68](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/68) | Session fixation / PKCE replay | 4 | 2 | **8 Medium** | One-time state, PKCE timeout 600s | 1 | **4 Low** | ✅ Controlled |
| RISK-013 | [#69](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/69) | OIDC ID Token forgery | 4 | 2 | **8 Medium** | JWKS verify, alg whitelist, Fail-Closed | 1 | **4 Low** | ✅ Controlled |
| RISK-014 | [#70](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/70) | Token exposure / unlimited refresh | 4 | 2 | **8 Medium** | Server-side session, HttpOnly, rate limit | 1 | **4 Low** | ✅ Controlled |

### 2.3 Data Protection Risks (Class B)

| Risk ID | Issue | Hazard | S | P(pre) | Risk(pre) | Control Measures | P(post) | Risk(post) | Status |
|---------|-------|--------|---|--------|-----------|-----------------|---------|------------|--------|
| RISK-003 | [#27](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/27) | Unit conversion error | 4 | 2 | **8 Medium** | UnitConversionService, fail-safe exclusion | 1 | **4 Low** | ✅ Controlled |
| RISK-004 | [#28](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/28) | FHIR data retrieval failure | 3 | 3 | **9 High** | Circuit breaker, fallback queries, missing data warning | 1 | **3 Low** | ✅ Controlled |
| RISK-006 | [#30](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/30) | Injection attacks (XSS/SQLi/SSRF) | 4 | 3 | **12 High** | CSP nonce, input validation, SSRF block | 1 | **4 Low** | ✅ Controlled |
| RISK-007 | [#31](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/31) | Tradeoff analysis error | 3 | 2 | **6 Medium** | Config-driven model, boundary validation | 1 | **3 Low** | ✅ Controlled |
| RISK-008 | [#32](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/32) | ePHI leak to logs | 4 | 3 | **12 High** | EPhiLoggingFilter, allowlist, regex | 1 | **4 Low** | ✅ Controlled |
| RISK-015 | [#72](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/72) | Log poisoning — FHIR resource in logs | 4 | 3 | **12 High** | FHIR resource detection, PII regex, safe dict keys | 1 | **4 Low** | ✅ Controlled |
| RISK-016 | [#73](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/73) | Session cookie ePHI exposure | 4 | 2 | **8 Medium** | SESSION_TYPE=filesystem, HttpOnly, SameSite | 1 | **4 Low** | ✅ Controlled |
| RISK-017 | [#74](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/74) | FHIR data over-fetching | 3 | 2 | **6 Medium** | LOINC filter, _count limit, ownership check | 1 | **3 Low** | ✅ Controlled |
| RISK-018 | [#75](https://github.com/Lusnaker0730/PRECISEHBR_CGU/issues/75) | ePHI not destroyed after session | 3 | 2 | **6 Medium** | Session timeout, logout clear, filesystem cleanup | 1 | **3 Low** | ✅ Controlled |

---

## 3. Risk Heatmap (Post-Control)

```
            Probability →
            1(Rare)  2(Unlikely)  3(Possible)  4(Likely)  5(Frequent)
Severity ↓  ┌────────┬────────────┬────────────┬──────────┬───────────┐
5 Catastrophic│        │            │            │          │           │
              │ R001   │            │            │          │           │
              │ R002   │            │            │          │           │
              ├────────┼────────────┼────────────┼──────────┼───────────┤
4 Critical    │ R003   │            │            │          │           │
              │ R005-6 │            │            │          │           │
              │ R008   │            │            │          │           │
              │ R010-16│            │            │          │           │
              ├────────┼────────────┼────────────┼──────────┼───────────┤
3 Serious     │ R004   │            │            │          │           │
              │ R007   │            │            │          │           │
              │ R017-18│            │            │          │           │
              ├────────┼────────────┼────────────┼──────────┼───────────┤
2 Minor       │        │            │            │          │           │
              ├────────┼────────────┼────────────┼──────────┼───────────┤
1 Negligible  │        │            │            │          │           │
              └────────┴────────────┴────────────┴──────────┴───────────┘

All 18 risks are in the LOW zone (P=1) after control measures.
```

---

## 4. Traceability Matrix (ISO 14971 §7.4 / IEC 62304 §5.1.1)

| Risk ID | Requirement | Design | Test | Test File | Success Criteria |
|---------|------------|--------|------|-----------|-----------------|
| RISK-001 | SRS-001 (#1) | SDS-001 (#13) | TC-001 (#34) | `verify_precise_hbr.py` | Golden dataset 20 cases pass |
| RISK-002 | SRS-002 (#2) | SDS-002 (#14) | TC-003 (#36) | `test_risk_classifier.py` | Threshold boundary tests |
| RISK-003 | SRS-003 (#3) | SDS-003 (#15) | TC-004 (#37) | `test_unit_conversion.py` | Unit conversion accuracy |
| RISK-004 | SRS-004 (#4) | SDS-004 (#16) | TC-005 (#38) | `test_fhir_client.py` | FHIR retrieval + fallback |
| RISK-005 | SRS-005 (#5) | SDS-005 (#17) | TC-006 (#39) | `test_auth_security.py` | PKCE/State/OIDC flow |
| RISK-006 | SRS-006 (#6) | SDS-006 (#18) | TC-007 (#40) | `test_security_comprehensive.py` | OWASP Top 10 |
| RISK-007 | SRS-007 (#7) | SDS-007 (#19) | TC-008 (#41) | `test_tradeoff.py` | Tradeoff model validation |
| RISK-008 | SRS-010 (#10) | SDS-010 (#22) | TC-011 (#44) | `test_audit_logger_extended.py` | ePHI filter + hash chain |
| RISK-009 | SRS-006 (#6) | SDS-006 (#18) | TC-007 (#40) | `test_data_protection_risk_015_018.py` | SC-009-01~06 |
| RISK-010 | SRS-005 (#5) | SDS-005 (#17) | TC-006 (#39) | `test_oauth_risk_010_014.py` | SC-010-01~06 |
| RISK-011 | SRS-005 (#5) | SDS-005 (#17) | TC-006 (#39) | `test_oauth_risk_010_014.py` | SC-011-01~05 |
| RISK-012 | SRS-005 (#5) | SDS-005 (#17) | TC-006 (#39) | `test_oauth_risk_010_014.py` | SC-012-01~06 |
| RISK-013 | SRS-005 (#5) | SDS-005 (#17) | TC-006 (#39) | `test_oauth_risk_010_014.py` | SC-013-01~07 |
| RISK-014 | SRS-005 (#5) | SDS-005 (#17) | TC-006 (#39) | `test_oauth_risk_010_014.py` | SC-014-01~08 |
| RISK-015 | SRS-010 (#10) | SDS-010 (#22) | TC-011 (#44) | `test_data_protection_risk_015_018.py` | SC-015-01~08 |
| RISK-016 | SRS-005 (#5) | SDS-005 (#17) | TC-006 (#39) | `test_data_protection_risk_015_018.py` | SC-016-01~06 |
| RISK-017 | SRS-004 (#4) | SDS-004 (#16) | TC-005 (#38) | `test_data_protection_risk_015_018.py` | SC-017-01~06 |
| RISK-018 | SRS-005 (#5) | SDS-005 (#17) | TC-006 (#39) | `test_data_protection_risk_015_018.py` | SC-018-01~07 |

---

## 5. Residual Risk Assessment

### Overall Residual Risk Summary

| Category | Count | Pre-Control Max | Post-Control Max | Verdict |
|----------|-------|----------------|-----------------|---------|
| Clinical (Class C) | 3 | 10 (High) | 5 (Medium) | Acceptable with monitoring |
| Security — OAuth2 | 6 | 12 (High) | 4 (Low) | Acceptable |
| Data Protection | 9 | 12 (High) | 4 (Low) | Acceptable |
| **Total** | **18** | | | **All risks at acceptable level** |

### Benefit-Risk Determination (ISO 14971 §8)

The PRECISE-HBR calculator provides significant clinical benefit by:
1. Quantifying individualized bleeding risk for PCI patients
2. Enabling evidence-based DAPT duration decisions
3. Reducing both bleeding and ischemic adverse events

**Conclusion**: The residual risks are acceptable in light of the clinical benefits. All identified hazards have control measures in place, verified by automated tests with defined success criteria.

---

## 6. Document History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-03-19 | Claude Code / Development Team | Initial risk matrix — 18 risks identified and controlled |
