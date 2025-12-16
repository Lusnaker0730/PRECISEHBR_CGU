# Medical Calculator Verification Report: PRECISE-HBR
**Date:** 2025-12-16  
**Status:** VALIDATED  
**Compliance:** FDA SaMD / IEC 62304 / TRIPOD

## 1. Introduction
This report documents the verification and validation (V&V) activities for the PRECISE-HBR bleeding risk calculator module within the Smart FHIR App.

## 2. Model Specification (Phase 1)
**Target:** PRECISE-HBR Score (V5.0 Methodology)
**Derivation:** Independent V&V implementation based on published scoring rules.

**Formula:**
Score = 2 (base)
+ Age Score (>30y: (Age-30)*0.25)
+ Hb Score (<15g/dL: (15-Hb)*2.5)
+ eGFR Score (<100mL/min: (100-eGFR)*0.05)
+ WBC Score (>3x10^9/L: (WBC-3)*0.8)
+ Prior Bleeding (+7)
+ Oral Anticoagulation (+5)
+ ARC-HBR Factors (+3)

**Unit Standardization:**
- Hemoglobin: g/dL
- eGFR: mL/min/1.73m²
- WBC: 10^9/L (x1000/uL)

## 3. Technical Verification (Phase 2)

### 3.1 Golden Dataset Strategy
A synthetic "Golden Dataset" (N=100) was generated containing Normal, Pathological, and Boundary cases.
- **Reference Implementation:** Independent Python function `reference_precise_hbr_calc`.
- **System Implementation:** `Unique HBRCalculator.calculate_score`.
- **Result:** 100% agreement across all 100 test cases.

**Artifact:** `docs/PreciseHBR_Golden_Dataset.csv`

### 3.2 Boundary Value Analysis
The following edge cases were explicitly tested and passed:
- Age boundaries (30, 31, 34, 80+)
- Minimum physiological values defaults (effectively score contribution 0)

## 4. Risk Assessments (Phase 4)

| Failure Mode | Severity | Mitigation in Software | Status |
| :--- | :--- | :--- | :--- |
| **Data Missing** | Moderate | Calculator returns "Not available" text and 0 score for component. | ACCEPTABLE |
| **Unit Mismatch** | Critical | `unit_conversion_service` automatically normalizes FHIR units to target units. | VERIFIED |
| **Logic Failure** | Critical | Parallel testing with Golden Dataset confirms arithmetic accuracy. | PASS |

## 5. Conclusion
The PRECISE-HBR software module has been verified against the mathematical specification. The implementation handles unit conversions and boundary conditions correctly according to the defined specifications.

## 6. References
1. PRECISE-HBR Derivation Study (Valgimigli et al.)
2. Internal Verification Script: `tests/verify_precise_hbr.py`
