# 軟體需求規格書 (SRS)

## PRECISE-HBR SMART on FHIR 臨床決策支援系統

| 項目 | 內容 |
|------|------|
| **文件編號** | SRS-PRECISE-HBR-v1.0 |
| **版本** | 1.0 |
| **產生日期** | 2026-03-12 |
| **適用標準** | IEC 62304 §5.2 軟體需求分析 |
| **軟體安全分類** | IEC 62304 Class C（可能導致嚴重傷害或死亡） |
| **預期用途** | 輔助心臟科/介入醫學臨床醫師評估 PCI 術後病人出血風險 |

---

## 需求摘要

| ID | 標題 | 安全分類 | 相關風險 | 驗證方式 |
|----|------|---------|---------|--------|
| SRS-001 | 系統應根據病人臨床資料計算 PRECISE-HBR 出血風險分數 | Class C | RISK-001 | 單元/整合測試 |
| SRS-002 | 系統應依據 PRECISE-HBR 分數將病人分類為風險等級 | Class C | RISK-001, RISK-002 | 單元/整合測試 |
| SRS-003 | 系統應支援實驗室值單位自動轉換 | Class B | RISK-003 | 單元/整合測試 |
| SRS-004 | 系統應透過 FHIR R4 API 擷取病人臨床資料 | Class B | RISK-004 | 單元/整合測試 |
| SRS-005 | 系統應實作 SMART on FHIR OAuth2 + PKCE 認證授權 | Class B | RISK-005 | 單元/整合測試 |
| SRS-006 | 系統應實作輸入驗證與安全防護機制 | Class B | RISK-006, RISK-009 | 單元/整合測試 |
| SRS-007 | 系統應提供出血-血栓事件權衡分析 | Class B | RISK-007 | 單元/整合測試 |
| SRS-008 | 系統應實作 CDS Hooks v1.2 整合介面 | Class B | - | 單元/整合測試 |
| SRS-009 | 系統應支援台灣核心實作指引 (TW Core IG) | Class A | - | 單元/整合測試 |
| SRS-010 | 系統應實作 ePHI 存取稽核日誌 | Class B | RISK-008 | 單元/整合測試 |
| SRS-011 | 系統應實作 FHIR Consent 同意管理 | Class B | - | 單元/整合測試 |
| SRS-012 | 系統應自動偵測臨床狀態與用藥以計算 HBR 因子 | Class C | RISK-001 | 單元/整合測試 |

---

## SRS-001: 系統應根據病人臨床資料計算 PRECISE-HBR 出血風險分數

**標籤**: requirement, IEC-62304, class-C

## Requirement ID
**ID**: SRS-001

## 需求類型
- [x] 功能性需求 (Functional Requirement)

## 安全分類 (IEC 62304)
- [x] Class C - 死亡或嚴重傷害可能

> **理由**: 分數計算錯誤可能導致臨床醫師做出錯誤的抗血栓治療決策。

## 描述

系統應根據以下病人參數計算 PRECISE-HBR 出血風險分數：

1. **年齡 (Age)**: 貢獻分 = 0.25 × (Age - 30)，Age 截斷至 [30, 80]
2. **血紅素 (Hb)**: 貢獻分 = 2.5 × (15 - Hb)，Hb 截斷至 [5.0, 15.0] g/dL
3. **腎絲球過濾率 (eGFR)**: 貢獻分 = 0.05 × (100 - eGFR)，eGFR 截斷至 [5, 100]
4. **白血球 (WBC)**: 貢獻分 = 0.8 × (WBC - 3)，WBC 截斷至 [3.0, 15.0]
5. **既往出血史**: +7 分（二元）
6. **口服抗凝藥使用**: +5 分（二元）
7. **ARC-HBR 因子 >= 1**: +3 分（二元）
8. **基礎分數**: 2 分

系統應回傳四捨五入後的整數總分。

## 驗收條件

1. 65 歲、Hb=11、eGFR=45、WBC=8、無出血史、無抗凝藥、無 ARC-HBR → 預期分數 28 → Very HBR
2. 25 歲健康人（Hb=14、eGFR=120、WBC=6、無旗標）→ 預期分數 7 → Not HBR
3. 超出截斷範圍的輸入值應被截斷（不拒絕）
4. 計算應在 100ms 內完成

## 風險參考
相關風險: RISK-001

## 法規追溯
- [x] TFDA 指引: 醫療器材軟體確效指引 - 4.2 軟體需求分析
- [x] IEC 62304 §5.2 Software Requirements Analysis
- [x] ISO 14971 §4.4 Risk Analysis

## 驗證方式
- [x] 單元測試 (Unit Test)
- [x] 整合測試 (Integration Test)

## 子需求
- SRS-002（風險分類）、SRS-003（單位轉換）

---

## SRS-002: 系統應依據 PRECISE-HBR 分數將病人分類為風險等級

**標籤**: requirement, IEC-62304, class-C

## Requirement ID
**ID**: SRS-002

## 安全分類 (IEC 62304)
- [x] Class C - 死亡或嚴重傷害可能

## 描述

系統應根據 PRECISE-HBR 總分將病人分類為以下風險等級：

| 分數範圍 | 風險等級 | 1年出血風險 |
|----------|---------|------------|
| ≤ 22 | Non-HBR（非高出血風險）| < 4% |
| 23-26 | HBR（高出血風險）| ~4% |
| ≥ 27 | Very HBR（極高出血風險）| ~6% |

## 驗收條件
1. 分數 22 → Non-HBR
2. 分數 23 → HBR
3. 分數 27 → Very HBR
4. 應回傳：風險等級、出血風險百分比、顏色標示、建議

## 風險參考
相關風險: RISK-001, RISK-002

## 驗證方式
- [x] 單元測試：`tests/test_risk_classifier.py`

---

## SRS-003: 系統應支援實驗室值單位自動轉換

**標籤**: requirement, IEC-62304, class-B

## Requirement ID
**ID**: SRS-003

## 安全分類 (IEC 62304)
- [x] Class B - 非嚴重傷害可能

## 描述

系統應自動偵測並轉換以下實驗室值的單位：

| 檢驗項目 | 支援的輸入單位 | 目標單位 |
|----------|-------------|---------|
| 血紅素 (Hb) | g/L, mmol/L | g/dL |
| 肌酐 (Creatinine) | µmol/L | mg/dL |
| 白血球 (WBC) | K/µL, cells/µL | 10^9/L |
| eGFR | — | 使用 CKD-EPI 2021 無種族公式計算 |

## 驗收條件
1. Hb 110 g/L → 11.0 g/dL
2. Hb 6.8 mmol/L → 11.0 g/dL (±0.5)
3. Creatinine 88.4 µmol/L → 1.0 mg/dL (±0.1)
4. eGFR 應使用性別特異性係數

## 風險參考
相關風險: RISK-003

## 驗證方式
- [x] 單元測試：`tests/test_unit_conversion_service.py`

---

## SRS-004: 系統應透過 FHIR R4 API 擷取病人臨床資料

**標籤**: requirement, IEC-62304, class-B

## Requirement ID
**ID**: SRS-004

## 安全分類 (IEC 62304)
- [x] Class B - 非嚴重傷害可能

## 描述

系統應透過 FHIR R4 API 擷取以下病人資料：
1. **Patient**: 人口統計資料（姓名、性別、出生日期）
2. **Observation**: 實驗室值（Hb, Creatinine, WBC, Platelets, eGFR）透過 LOINC 代碼查詢
3. **Condition**: 診斷（出血史、惡性腫瘤、肝硬化等）
4. **MedicationRequest**: 用藥（抗凝藥、NSAID 等）

## 驗收條件
1. 每個 FHIR 請求超時設為 15 秒
2. 擷取失敗時應優雅降級（繼續使用可用資料）
3. 應檢查 FHIR 安全標籤（restricted/very-restricted）
4. 應追蹤缺失欄位並警告臨床醫師

## 風險參考
相關風險: RISK-004

## 驗證方式
- [x] 單元測試：`tests/test_fhir_service.py`
- [x] 整合測試

---

## SRS-005: 系統應實作 SMART on FHIR OAuth2 + PKCE 認證授權

**標籤**: requirement, IEC-62304, class-B

## Requirement ID
**ID**: SRS-005

## 安全分類 (IEC 62304)
- [x] Class B - 非嚴重傷害可能

## 描述

系統應實作 SMART on FHIR v2.0 OAuth2 認證授權流程：

1. **SMART 配置發現**: 自動取得 `.well-known/smart-configuration` 端點
2. **PKCE 參數生成**: 使用密碼學安全隨機數產生 `code_verifier` / `code_challenge`
3. **State 參數**: 防止 CSRF 攻擊
4. **Token 交換**: Authorization code → Access token + Refresh token
5. **OIDC 驗證**: 驗證 `id_token` 簽章（僅允許 RS256/ES256，拒絕 HS256/none）
6. **Token 刷新**: 支援 refresh token，最小間隔 30 秒

## 驗收條件
1. PKCE challenge 使用 SHA-256
2. State 參數在使用後消費（一次性）
3. Session 中不儲存明文敏感資料
4. 支援 Epic 和 Cerner EHR 系統

## 風險參考
相關風險: RISK-005

## 驗證方式
- [x] 單元測試：`tests/test_auth_security.py`, `tests/test_oidc_validator.py`, `tests/test_smart_security.py`

---

## SRS-006: 系統應實作輸入驗證與安全防護機制

**標籤**: requirement, IEC-62304, class-B

## Requirement ID
**ID**: SRS-006

## 安全分類 (IEC 62304)
- [x] Class B - 非嚴重傷害可能

## 描述

系統應對所有使用者輸入實施驗證與安全防護：

1. **URL 驗證 / SSRF 防護**: DNS 解析檢查、封鎖私有 IP 與雲端 metadata 端點
2. **Patient ID 驗證**: 英數字 + 連字符/底線，最長 255 字元
3. **LOINC/FHIR 搜尋參數驗證**: 防止注入攻擊
4. **BOLA 防護**: 驗證請求的 patient_id 與 OAuth 授權的 patient 一致
5. **CSP nonce**: 基於 nonce 的腳本安全策略
6. **CSRF 保護**: 所有非冪等路由（CDS Hooks 除外）
7. **速率限制**: API 端點限制 10 次/分鐘

## 驗收條件
1. SSRF 攻擊（私有 IP、cloud metadata）應被阻擋
2. XSS / SQL 注入 / 命令注入應被防護
3. 不同 patient 的 BOLA 攻擊應被阻擋

## 風險參考
相關風險: RISK-006, RISK-009

## 驗證方式
- [x] 單元測試：`tests/test_input_validation.py`, `tests/test_input_validator_module.py`
- [x] 安全測試：`tests/test_security_comprehensive.py`, `tests/test_patient_context.py`

---

## SRS-007: 系統應提供出血-血栓事件權衡分析

**標籤**: requirement, IEC-62304, class-B

## Requirement ID
**ID**: SRS-007

## 安全分類 (IEC 62304)
- [x] Class B - 非嚴重傷害可能

## 描述

系統應基於 ARC-HBR 模型提供出血與血栓事件的權衡分析：

1. 使用 Cox proportional hazards 模型計算出血/血栓風險
2. 基線風險率：出血 2.5%、血栓 2.5%
3. 偵測風險因子：糖尿病、既往心肌梗塞、吸菸、NSTEMI/STEMI、複雜 PCI、BMS、COPD、出院抗凝藥
4. 支援互動式重新計算

## 風險參考
相關風險: RISK-007

## 驗證方式
- [x] 單元測試：`tests/verify_tradeoff.py`

---

## SRS-008: 系統應實作 CDS Hooks v1.2 整合介面

**標籤**: requirement, IEC-62304, class-B

## Requirement ID
**ID**: SRS-008

## 安全分類 (IEC 62304)
- [x] Class B - 非嚴重傷害可能

## 描述

系統應實作 CDS Hooks v1.2 標準介面，支援 EHR 系統整合：

1. **服務發現** (`/cds-services`): 公布可用的 Hook 服務
2. **medication-prescribe Hook**: 偵測高出血風險用藥（DAPT、抗凝藥），建議 HBR 評估
3. **patient-view Hook**: 開啟病歷時顯示 HBR 分數與出血風險
4. **Warning Card 生成**: 包含分數、建議、建議動作
5. **CORS**: 允許所有來源（CDS Hooks 規範要求）

## 驗證方式
- [x] 單元測試：`tests/test_hooks.py`

---

## SRS-009: 系統應支援台灣核心實作指引 (TW Core IG)

**標籤**: requirement, IEC-62304, class-A

## Requirement ID
**ID**: SRS-009

## 安全分類 (IEC 62304)
- [x] Class A - 無傷害可能

## 描述

系統應支援台灣衛福部核心實作指引 (TW Core IG)：

1. **中文姓名擷取**: 支援 HumanName 中的中文字元
2. **台灣身分證號**: 擷取身分證字號 / 居留證號 / 病歷號
3. **健保藥品代碼 (NHI)**: 支援台灣 NHI 藥品代碼系統
4. **ICD-10-CM 診斷代碼**: 當 SNOMED 不可用時回退到 ICD-10-CM
5. **TW Core 相容性**: 產生符合 TW Core Profile 的 Patient 資源

## 驗證方式
- [x] 單元測試：`tests/test_twcore_adapter.py`

---

## SRS-010: 系統應實作 ePHI 存取稽核日誌

**標籤**: requirement, IEC-62304, class-B

## Requirement ID
**ID**: SRS-010

## 安全分類 (IEC 62304)
- [x] Class B - 非嚴重傷害可能

## 描述

系統應實作符合 ONC 45 CFR 170.315(d)(2) 的稽核日誌功能：

1. **防竄改雜湊鏈**: SHA-256 雜湊鏈確保日誌完整性
2. **日誌內容**: 時間戳、user_id、patient_id、動作、結果、IP、User-Agent
3. **執行緒安全**: Append-only JSON Lines 格式
4. **ePHI 過濾**: 防止病人健康資料出現在應用程式日誌中
5. **完整性驗證**: 提供雜湊鏈驗證功能
6. **裝飾器**: `@audit_ephi_access` 自動記錄 ePHI 存取

## 風險參考
相關風險: RISK-008

## 驗證方式
- [x] 單元測試：`tests/test_audit_logger_extended.py`, `tests/test_ephi_protection.py`

---

## SRS-011: 系統應實作 FHIR Consent 同意管理

**標籤**: requirement, IEC-62304, class-B

## Requirement ID
**ID**: SRS-011

## 安全分類 (IEC 62304)
- [x] Class B - 非嚴重傷害可能

## 描述

系統應支援 FHIR Consent 資源管理：

1. **同意查詢**: 查詢病人的 active Consent 資源
2. **同意檢查**: 在存取敏感資源前驗證病人同意
3. **資源過濾**: 根據 permit/deny 條款過濾病人資料
4. **優雅降級**: 當 FHIR 伺服器不支援 Consent 時不中斷服務

## 驗證方式
- [x] 單元測試：`tests/test_consent_service.py`

---

## SRS-012: 系統應自動偵測臨床狀態與用藥以計算 HBR 因子

**標籤**: requirement, IEC-62304, class-C

## Requirement ID
**ID**: SRS-012

## 安全分類 (IEC 62304)
- [x] Class C - 死亡或嚴重傷害可能

> **理由**: 錯誤偵測臨床狀態會直接影響 HBR 分數（+3/+5/+7 分），影響治療決策。

## 描述

系統應自動偵測以下臨床狀態與用藥：

1. **既往出血史** (+7分): SNOMED/ICD-10-CM 出血代碼 + 文字關鍵字匹配
2. **口服抗凝藥** (+5分): Warfarin, DOAC (apixaban, rivaroxaban) via RxNorm/NHI 代碼
3. **ARC-HBR 因子** (+3分):
   - 血小板減少症 (< 100×10^9/L)
   - 出血傾向
   - 肝硬化合併門脈高壓
   - 活動性惡性腫瘤（排除皮膚癌，限過去 12 個月）
   - 慢性 NSAID/類固醇使用
4. 支援 SNOMED-CT、ICD-10-CM、NHI 代碼系統

## 風險參考
相關風險: RISK-001

## 驗證方式
- [x] 單元測試：`tests/test_condition_checker_config.py`, `tests/test_fhir_service.py`

---

## 附錄 A：PRECISE-HBR 計算公式

```
總分 = 基礎分(2)
     + 0.25 × (Age - 30)        [Age 截斷至 30~80]
     + 2.5 × (15 - Hb)          [Hb 截斷至 5.0~15.0 g/dL]
     + 0.05 × (100 - eGFR)      [eGFR 截斷至 5~100]
     + 0.8 × (WBC - 3)          [WBC 截斷至 3.0~15.0]
     + 7 (既往出血史)
     + 5 (口服抗凝藥)
     + 3 (ARC-HBR 因子 ≥ 1)
```

| 風險等級 | 分數範圍 | 1 年出血風險 |
|---------|---------|------------|
| Non-HBR | ≤ 22 | < 4% |
| HBR | 23–26 | ~4% |
| Very HBR | ≥ 27 | ~6% |
