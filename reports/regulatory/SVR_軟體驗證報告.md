# 軟體驗證報告 (SVR)

## PRECISE-HBR SMART on FHIR 臨床決策支援系統

| 項目 | 內容 |
|------|------|
| **文件編號** | SVR-PRECISE-HBR-v1.0 |
| **版本** | 1.0 |
| **產生日期** | 2026-03-12 |
| **適用標準** | IEC 62304 §5.5 軟體單元驗證、§5.6 軟體整合測試 |
| **軟體安全分類** | IEC 62304 Class C（可能導致嚴重傷害或死亡） |
| **預期用途** | 輔助心臟科/介入醫學臨床醫師評估 PCI 術後病人出血風險 |

---

## 1. 驗證摘要

| 項目 | 數值 |
|------|------|
| 追溯測試總數 | 654 |
| 通過 | 654 |
| 失敗 | 0 |
| 通過率 | 100.0% |
| 報告產生時間 | 2026-03-12T15:03:27Z |

## 2. 測試分類統計

| 測試類別 | 對應需求 | 數量 | 通過 |
|---------|---------|------|------|
| 系統應根據病人臨床資料計算 PRECISE-HBR 出血風險 | SRS-001 | 36 | 36 |
| 系統應依據 PRECISE-HBR 分數將病人分類為風險等級 | SRS-002 | 35 | 35 |
| 系統應支援實驗室值單位自動轉換 | SRS-003 | 41 | 41 |
| 系統應透過 FHIR R4 API 擷取病人臨床資料 | SRS-004 | 5 | 5 |
| 系統應實作 SMART on FHIR OAuth2 + P | SRS-005 | 143 | 143 |
| 系統應實作輸入驗證與安全防護機制 | SRS-006 | 219 | 219 |
| 系統應提供出血-血栓事件權衡分析 | SRS-007 | 5 | 5 |
| 系統應實作 CDS Hooks v1.2 整合介面 | SRS-008 | 31 | 31 |
| 系統應支援台灣核心實作指引 (TW Core IG) | SRS-009 | 18 | 18 |
| 系統應實作 ePHI 存取稽核日誌 | SRS-010 | 47 | 47 |
| 系統應實作 FHIR Consent 同意管理 | SRS-011 | 23 | 23 |
| 系統應自動偵測臨床狀態與用藥以計算 HBR 因子 | SRS-012 | 33 | 33 |

## 3. 測試案例執行結果

### TC-001: TC-001: Golden Dataset 驗證 PRECISE-HBR 計算正確性

## Test ID: TC-001
## 追溯: SRS-001 → SDS-001 → RISK-001

## 測試檔案
`tests/verify_precise_hbr.py::test_golden_dataset_verification`

## 測試步驟
1. 使用獨立參考實作計算 20 組隨機病人預期分數
2. 使用 `PreciseHBRCalculator.calculate_pure_score()` 計算同組資料
3. 比較差異

## 通過條件
每組差異 < 1 分（四捨五入誤差範圍）

**測試檔案**: ## 測試檔案

**相關測試**: 36 個（通過: 36）

---

### TC-002: TC-002: 邊界值測試 PRECISE-HBR 計算截斷邏輯

## Test ID: TC-002
## 追溯: SRS-001 → SDS-001 → RISK-001

## 測試檔案
`tests/verify_precise_hbr.py::test_boundary_values`

## 測試步驟
測試所有截斷邊界：Age 30/80、Hb 5.0/15.0、eGFR 5/100、WBC 3.0/15.0

## 通過條件
所有邊界值的分數與手算結果一致

**測試檔案**: ## 測試檔案

**相關測試**: 36 個（通過: 36）

---

### TC-003: TC-003: 風險分類閾值驗證

## Test ID: TC-003
## 追溯: SRS-002 → SDS-002 → RISK-001, RISK-002

## 測試檔案
`tests/test_risk_classifier.py`

## 測試步驟
驗證分數 0/22/23/26/27/50 的風險分類結果

## 通過條件
- ≤22 → Non-HBR
- 23-26 → HBR
- ≥27 → Very HBR

**測試檔案**: ## 測試檔案

**相關測試**: 35 個（通過: 35）

---

### TC-004: TC-004: 實驗室值單位轉換驗證

## Test ID: TC-004
## 追溯: SRS-003 → SDS-003 → RISK-003

## 測試檔案
`tests/test_unit_conversion_service.py`

## 通過條件
- Hb g/L → g/dL 轉換正確
- Hb mmol/L → g/dL 轉換正確
- Creatinine µmol/L → mg/dL 轉換正確
- 未知單位回傳 None

**測試檔案**: ## 測試檔案

**相關測試**: 41 個（通過: 41）

---

### TC-005: TC-005: FHIR 資料擷取功能驗證

## Test ID: TC-005
## 追溯: SRS-004 → SDS-004 → RISK-004

## 測試檔案
`tests/test_fhir_service.py`

## 通過條件
- Patient demographics 正確擷取
- Observation 值正確解析
- 錯誤處理正確（超時、無效回應）

**測試檔案**: ## 測試檔案

**相關測試**: 5 個（通過: 5）

---

### TC-006: TC-006: OAuth2/PKCE 認證安全驗證

## Test ID: TC-006
## 追溯: SRS-005 → SDS-005 → RISK-005

## 測試檔案
`tests/test_auth_security.py`, `tests/test_oidc_validator.py`, `tests/test_smart_security.py`, `tests/test_mfa_validator.py`

## 通過條件
- PKCE 參數正確生成與驗證
- State 參數一次性消費
- OIDC token 驗證拒絕 HS256/none
- Session 不含明文敏感資料

**測試檔案**: ## 測試檔案

**相關測試**: 143 個（通過: 143）

---

### TC-007: TC-007: 輸入驗證與 BOLA 防護測試

## Test ID: TC-007
## 追溯: SRS-006 → SDS-006 → RISK-006, RISK-009

## 測試檔案
`tests/test_input_validation.py`, `tests/test_input_validator_module.py`, `tests/test_patient_context.py`

## 通過條件
- SSRF 攻擊被阻擋
- XSS/SQLi/命令注入被防護
- BOLA 攻擊被阻擋
- Patient ID 格式驗證正確

**測試檔案**: ## 測試檔案

**相關測試**: 219 個（通過: 219）

---

### TC-008: TC-008: 權衡分析模型驗證

## Test ID: TC-008
## 追溯: SRS-007 → SDS-007 → RISK-007

## 測試檔案
`tests/verify_tradeoff.py`

## 通過條件
- 缺失資料行為正確
- 高風險病人分數合理

**測試檔案**: ## 測試檔案

**相關測試**: 5 個（通過: 5）

---

### TC-009: TC-009: CDS Hooks 整合驗證

## Test ID: TC-009
## 追溯: SRS-008 → SDS-008

## 測試檔案
`tests/test_hooks.py`

## 通過條件
- 服務發現回傳正確 JSON
- medication-prescribe Hook 正確偵測用藥
- Warning Card 包含必要欄位
- CORS headers 正確

**測試檔案**: ## 測試檔案

**相關測試**: 31 個（通過: 31）

---

### TC-010: TC-010: TW Core 適配器驗證

## Test ID: TC-010
## 追溯: SRS-009 → SDS-009

## 測試檔案
`tests/test_twcore_adapter.py`

## 通過條件
- 中文姓名正確擷取
- 身分證號正確擷取
- NHI 藥品代碼正確擷取
- ICD-10 診斷代碼正確擷取

**測試檔案**: ## 測試檔案

**相關測試**: 18 個（通過: 18）

---

### TC-011: TC-011: ePHI 稽核日誌驗證

## Test ID: TC-011
## 追溯: SRS-010 → SDS-010 → RISK-008

## 測試檔案
`tests/test_audit_logger_extended.py`, `tests/test_ephi_protection.py`

## 通過條件
- 雜湊鏈完整性驗證通過
- 竄改偵測正確
- 必要欄位（timestamp, user_id, action）存在
- ePHI 不出現在一般日誌中

**測試檔案**: ## 測試檔案

**相關測試**: 47 個（通過: 47）

---

### TC-012: TC-012: 同意服務驗證

## Test ID: TC-012
## 追溯: SRS-011 → SDS-011

## 測試檔案
`tests/test_consent_service.py`

## 通過條件
- ConsentStatus/ConsentProvision 列舉正確
- ConsentResult 正確建立
- ConsentService 初始化正確

**測試檔案**: ## 測試檔案

**相關測試**: 23 個（通過: 23）

---

### TC-013: TC-013: 臨床狀態檢測驗證

## Test ID: TC-013
## 追溯: SRS-012 → SDS-012 → RISK-001

## 測試檔案
`tests/test_condition_checker_config.py`, `tests/test_fhir_service.py`

## 通過條件
- ICD-10 出血診斷碼偵測正確
- ICD-10 惡性腫瘤碼偵測正確
- NHI 抗凝藥代碼偵測正確
- NHI NSAID 代碼偵測正確

**測試檔案**: ## 測試檔案

**相關測試**: 33 個（通過: 33）

---

### TC-014: TC-014: OWASP Top 10 安全測試

## Test ID: TC-014
## 追溯: SRS-006 → RISK-006

## 測試檔案
`tests/test_security_comprehensive.py`

## 通過條件
- OWASP A01-A10 全部測試通過
- 包含：注入、認證失敗、敏感資料暴露、XXE、存取控制、安全配置、XSS、不安全反序列化、已知漏洞、日誌監控不足

**測試檔案**: ## 測試檔案

**相關測試**: 219 個（通過: 219）

---

## 4. 驗證結論

**結論：所有追溯測試均通過，軟體驗證結果符合 IEC 62304 §5.5 要求。**

所有軟體需求（SRS-001 ~ SRS-012）均有對應的測試案例覆蓋，且所有測試案例均執行通過。風險控制措施（RISK-001 ~ RISK-009）的驗證測試均確認控制措施有效。
