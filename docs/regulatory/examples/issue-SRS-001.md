# [SRS-001] 系統應根據病人臨床資料計算 PRECISE-HBR 出血風險分數

> **這是一個範例 GitHub Issue，使用 `software_requirement.md` template 建立**
> **在 GitHub 上建立時，選擇 "Software Requirement (SRS)" template**

---

## Requirement ID
**ID**: SRS-001

## Requirement Type
- [x] Functional Requirement

## Safety Classification (IEC 62304)
- [ ] Class A - No injury possible
- [ ] Class B - Non-serious injury possible
- [x] Class C - Death or serious injury possible

> **理由**: 分數計算錯誤可能導致臨床醫師做出錯誤的抗血栓治療決策，
> 進而導致病人出血或血栓事件。

## Description

The system shall calculate a PRECISE-HBR bleeding risk score based on the following patient parameters:

1. **Age**: Contribution = 0.25 x (Age - 30) when Age > 30, clamped to [30, 80]
2. **Hemoglobin (Hb)**: Contribution = 2.5 x (15 - Hb) when Hb < 15 g/dL, clamped to [5.0, 15.0]
3. **eGFR**: Contribution = 0.05 x (100 - eGFR) when eGFR < 100, clamped to [5, 100]
4. **WBC**: Contribution = 0.8 x (WBC - 3) when WBC > 3, clamped to [3.0, 15.0]
5. **Prior bleeding history**: +7 points (binary)
6. **Oral anticoagulation use**: +5 points (binary)
7. **ARC-HBR factors >= 1**: +3 points (binary)
8. **Base score**: 2 points

The system shall return a total score as a rounded integer.

## Rationale

PRECISE-HBR is a validated bleeding risk prediction model for PCI patients
(Costa et al., European Heart Journal, 2021). Accurate calculation is essential
for clinical decision-making regarding dual antiplatelet therapy duration.

## Acceptance Criteria

1. Given a 65-year-old patient with Hb=11 g/dL, eGFR=45, WBC=8, no bleeding history,
   no anticoagulation, no ARC-HBR factors:
   - Age contribution = 0.25 x (65-30) = 8.75
   - Hb contribution = 2.5 x (15-11) = 10.0
   - eGFR contribution = 0.05 x (100-45) = 2.75
   - WBC contribution = 0.8 x (8-3) = 4.0
   - Total = 2 + 8.75 + 10.0 + 2.75 + 4.0 = 27.5 → rounded to 28
   - Expected risk category: "Very HBR"

2. Given a 25-year-old healthy patient (Hb=14, eGFR=120, WBC=6, no flags):
   - Age contribution = 0 (below threshold)
   - Hb contribution = 2.5 x (15-14) = 2.5
   - eGFR contribution = 0 (above threshold)
   - WBC contribution = 0.8 x (6-3) = 2.4
   - Total = 2 + 0 + 2.5 + 0 + 2.4 = 6.9 → rounded to 7
   - Expected risk category: "Not high bleeding risk"

3. All input values outside truncation range shall be clamped (not rejected).

4. Score calculation shall complete within 100ms.

## Risk Reference
Related risks: #RISK-001, #RISK-002

## Regulatory Traceability
- [x] Maps to TFDA guidance: 醫療器材軟體確效指引 - 4.2 軟體需求分析
- [x] Maps to IEC 62304 clause: 5.2 Software Requirements Analysis
- [x] Maps to ISO 14971 clause: 4.4 Risk Analysis

## Verification Method
- [x] Unit Test
- [x] Integration Test
- [ ] System Test
- [ ] Manual Review
- [ ] Code Inspection

## Parent/Child Requirements
- Parent: N/A (top-level requirement)
- Children: #SRS-002 (Risk Classification), #SRS-003 (Unit Conversion)

---

**Labels**: `requirement`, `IEC-62304`, `class-C`
