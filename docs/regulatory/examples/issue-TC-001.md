# [TEST] TC-001: Golden Dataset 驗證 PRECISE-HBR 計算正確性

> **這是一個範例 GitHub Issue，使用 `test_case.md` template 建立**

---

## Test ID
**ID**: TC-001

## Test Level
- [x] Unit Test
- [ ] Integration Test
- [ ] System Test (E2E)
- [ ] Performance Test
- [ ] Security Test

## Traces to
- Requirement: #SRS-001 (PRECISE-HBR 分數計算)
- Design: #SDS-001 (計算模組設計)
- Risk Control: #RISK-001 (風險控制措施 #1: Golden dataset verification)

## Preconditions

1. `cdss_config.json` 已正確載入所有 PRECISE-HBR 計算參數
2. `condition_checker` 的回傳值可被 mock

## Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | 使用獨立參考實作計算 100 組隨機病人資料的預期分數 | 得到 100 組預期分數 |
| 2 | 使用 `PreciseHBRCalculator.calculate_pure_score()` 計算相同 100 組資料 | 得到 100 組實際分數 |
| 3 | 比較實際分數與預期分數 | 每組差異 < 1 分（四捨五入誤差範圍） |

## Test Data

- **Normal case**: Age=50, Hb=14, eGFR=90, WBC=6, no flags → expected score ~9
- **High risk case**: Age=78, Hb=8, eGFR=20, WBC=12, all flags → expected score ~40
- **98 random cases**: 隨機生成的參數組合

## Pass/Fail Criteria

- **Pass**: 所有 100 組測試資料的實際分數與參考實作計算結果差異 < 1 分
- **Fail**: 任一組測試資料差異 >= 1 分

## Automated Test Location
**File**: `tests/verify_precise_hbr.py`
**Function**: `test_golden_dataset_verification`

## Test Execution Record
- **Date**: (由 CI 自動填入)
- **Tester**: GitHub Actions
- **CI Run**: (連結到 GitHub Actions run)
- **Result**: (Pass / Fail)
- **Evidence**: `reports/unit-test-results.xml` 中 `test_golden_dataset_verification` 的結果

---

**Labels**: `test`, `verification`, `IEC-62304`
