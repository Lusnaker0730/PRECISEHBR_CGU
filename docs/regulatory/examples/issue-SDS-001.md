# [SDS-001] PRECISE-HBR 分數計算模組設計

> **這是一個範例 GitHub Issue，使用 `software_design.md` template 建立**

---

## Design ID
**ID**: SDS-001

## Traces to Requirements
Implements: #SRS-001

## Software Unit / Module
**Module**: `services/precise_hbr_calculator.py`
**Class/Function**: `PreciseHBRCalculator.calculate_pure_score()`

## Design Description

### Architecture Decision
採用 **Config-Driven Calculation** 設計模式：
- 所有計算係數、截斷值、閾值從 `config/cdss_config.json` 載入
- 計算邏輯與臨床參數分離，允許臨床團隊調整參數而不修改程式碼
- 使用 Singleton pattern 避免重複載入 config

### Calculation Pipeline
```
extract_inputs(fhir_data) → normalize/clamp → calculate_pure_score(inputs) → round → classify_risk
```

### Key Design Decisions
1. **Clamping strategy**: 超出範圍的值被截斷到最近的有效值，而非拒絕輸入
   - **Rationale**: 臨床上極端值（如 95 歲）仍需要分數，截斷到上限（80歲）是臨床上可接受的近似
   - **Alternatives considered**: 拒絕超出範圍的輸入 → rejected，因為會阻止臨床使用

2. **Rounding**: 最終分數四捨五入為整數
   - **Rationale**: 臨床溝通中使用整數分數更直觀

3. **Missing data handling**: 缺失的實驗室值使用「正常值」替代（不加分）
   - **Rationale**: 避免因資料缺失而誇大風險

## Interface Specification

### Inputs
| Parameter | Type | Constraints |
|-----------|------|-------------|
| age | float | Will be clamped to [30, 80] |
| hemoglobin | float | g/dL, clamped to [5.0, 15.0] |
| egfr | float | mL/min/1.73m², clamped to [5, 100] |
| wbc | float | 10^9/L, clamped to [3.0, 15.0] |
| has_prior_bleeding | bool | Binary flag |
| has_oral_anticoagulation | bool | Binary flag |
| has_arc_hbr_factors | bool | Binary flag |

### Outputs
| Parameter | Type | Description |
|-----------|------|-------------|
| score | int | Rounded PRECISE-HBR total score |
| components | dict | Breakdown of each component's contribution |

## Safety Considerations
- **Overflow protection**: All inputs clamped before calculation → score cannot exceed theoretical max (~40)
- **Type safety**: All numeric inputs cast to float before calculation
- **Config validation**: If config is missing, falls back to hardcoded defaults (tested in test_config_loader.py)

## Verification Approach
Test cases: #TC-001, #TC-002, #TC-003

---

**Labels**: `design`, `IEC-62304`
