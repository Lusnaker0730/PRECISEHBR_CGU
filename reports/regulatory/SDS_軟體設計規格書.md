# 軟體設計規格書 (SDS)

## PRECISE-HBR SMART on FHIR 臨床決策支援系統

| 項目 | 內容 |
|------|------|
| **文件編號** | SDS-PRECISE-HBR-v1.0 |
| **版本** | 1.0 |
| **產生日期** | 2026-03-12 |
| **適用標準** | IEC 62304 §5.3 軟體架構設計、§5.4 詳細設計 |
| **軟體安全分類** | IEC 62304 Class C（可能導致嚴重傷害或死亡） |
| **預期用途** | 輔助心臟科/介入醫學臨床醫師評估 PCI 術後病人出血風險 |

---

## 1. 系統架構概覽

```
┌─────────────────────────────────────────────────────────┐
│                    Flask Application                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ web_     │  │ auth_    │  │ api_     │  │ hooks    │ │
│  │ routes   │  │ routes   │  │ routes   │  │ (CDS)    │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │              │              │              │       │
│  ┌────┴──────────────┴──────────────┴──────────────┴────┐ │
│  │                   Services Layer                      │ │
│  │  precise_hbr_calculator │ risk_classifier             │ │
│  │  condition_checker      │ unit_conversion_service     │ │
│  │  fhir_client_service    │ tradeoff_model_calculator   │ │
│  │  twcore_adapter         │ audit_logger                │ │
│  │  consent_service        │ config_loader               │ │
│  └────┬─────────────────────────────────────────────────┘ │
│       │                                                    │
│  ┌────┴─────────────────────────────────────────────────┐ │
│  │                   Utilities Layer                      │ │
│  │  input_validator │ patient_context │ oidc_validator    │ │
│  │  web_utils       │ security_labels │ logging_filter    │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ FHIR R4 / OAuth2+PKCE
                         ▼
              ┌─────────────────────┐
              │  EHR FHIR Server    │
              │  (Epic / Cerner)    │
              └─────────────────────┘
```

## 模組設計摘要

| ID | 模組 | 追溯需求 | 驗證 |
|----|------|---------|------|
| SDS-001 | PRECISE-HBR 分數計算模組設計 | SRS-001 | TC-001, TC-002 |
| SDS-002 | 風險分類模組設計 | SRS-002 | TC-003 |
| SDS-003 | 實驗室值單位轉換服務設計 | SRS-003 | TC-004 |
| SDS-004 | FHIR 客戶端服務設計 | SRS-004 | TC-005 |
| SDS-005 | OAuth2/PKCE 認證流程設計 | SRS-005 | TC-006 |
| SDS-006 | 輸入驗證模組設計 | SRS-006 | TC-007 |
| SDS-007 | 權衡分析模組設計 | SRS-007 | TC-008 (verify_tradeoff.py) |
| SDS-008 | CDS Hooks 端點設計 | SRS-008 | TC-009 |
| SDS-009 | TW Core 適配器設計 | SRS-009 | TC-010 |
| SDS-010 | 稽核日誌模組設計 | SRS-010 | TC-011 |
| SDS-011 | 同意服務設計 | SRS-011 | TC-012 |
| SDS-012 | 臨床狀態檢測模組設計 | SRS-012 | TC-013 |

---

## SDS-001: PRECISE-HBR 分數計算模組設計

## Design ID: SDS-001
## 追溯需求: SRS-001

## 軟體模組
**模組**: `services/precise_hbr_calculator.py`
**類別**: `PreciseHBRCalculator`

## 設計描述

### 架構決策
採用 **Config-Driven Calculation** 設計模式：
- 所有計算係數從 `config/cdss_config.json` 載入
- 計算邏輯與臨床參數分離
- Singleton pattern 避免重複載入

### 計算管線
```
extract_inputs(fhir_data) → normalize/clamp → calculate_pure_score(inputs) → round → classify_risk
```

### 關鍵決策
1. **截斷策略**: 超出範圍值截斷到最近有效值（非拒絕），因臨床上極端值仍需分數
2. **四捨五入**: 最終分數四捨五入為整數，臨床溝通更直觀
3. **缺失資料處理**: 缺失實驗室值使用正常值替代（不加分）

## 安全考量
- 溢位保護：所有輸入截斷後計算
- 型別安全：數值輸入轉為 float
- Config 驗證：缺失時回退到硬編碼預設值

## 驗證: TC-001, TC-002

---

## SDS-002: 風險分類模組設計

## Design ID: SDS-002
## 追溯需求: SRS-002

## 軟體模組
**模組**: `services/risk_classifier.py`
**類別**: `RiskClassifierService`

## 設計描述
- 閾值驅動分類：Non-HBR (≤22) / HBR (23-26) / Very-HBR (≥27)
- 出血風險百分比校準曲線（PRECISE-HBR 驗證研究）
- 回傳結構化字典：score, risk_category, bleeding_risk_percent, color_class, recommendation

## 驗證: TC-003

---

## SDS-003: 實驗室值單位轉換服務設計

## Design ID: SDS-003
## 追溯需求: SRS-003

## 軟體模組
**模組**: `services/unit_conversion_service.py`
**類別**: `UnitConversionService`

## 設計描述
- Config-driven 轉換因子（從 cdss_config.json 載入）
- 支援 UCUM 單位變體（大小寫不敏感）
- CKD-EPI 2021 無種族 eGFR 公式（性別特異性 κ/α 係數）
- 未知單位回傳 None（不猜測）

## 驗證: TC-004

---

## SDS-004: FHIR 客戶端服務設計

## Design ID: SDS-004
## 追溯需求: SRS-004

## 軟體模組
**模組**: `services/fhir_client_service.py`
**類別**: `FHIRClientService`

## 設計描述
- HTTP client with 15s timeout per request (GAE 60s 限制)
- LOINC code 驗證後才發送搜尋
- 安全標籤檢查（restricted/very-restricted）
- 優雅降級：個別資源擷取失敗不影響整體流程
- 排序：最新觀測值優先

## 驗證: TC-005

---

## SDS-005: OAuth2/PKCE 認證流程設計

## Design ID: SDS-005
## 追溯需求: SRS-005

## 軟體模組
**模組**: `routes/auth_routes.py`, `utils/oidc_validator.py`

## 設計描述
- SMART on FHIR v2.0 OAuth2 authorization code flow
- PKCE: cryptographic code_verifier (≥43 chars) + SHA-256 challenge
- State parameter: 一次性消費，防 CSRF
- OIDC id_token 驗證：RS256/ES256 only，JWKS 快取 1 小時
- Token refresh: 最小間隔 30 秒

## 驗證: TC-006

---

## SDS-006: 輸入驗證模組設計

## Design ID: SDS-006
## 追溯需求: SRS-006

## 軟體模組
**模組**: `utils/input_validator.py`, `utils/patient_context.py`

## 設計描述
- URL 驗證：DNS 解析 + 私有 IP 封鎖 + cloud metadata 封鎖
- Patient ID：正則驗證 + 長度限制
- FHIR 搜尋參數：白名單 + 注入模式偵測
- BOLA 防護：session patient_id vs request patient_id 比對

## 驗證: TC-007

---

## SDS-007: 權衡分析模組設計

## Design ID: SDS-007
## 追溯需求: SRS-007

## 軟體模組
**模組**: `services/tradeoff_model_calculator.py`
**類別**: `TradeoffModelCalculator`

## 設計描述
- ARC-HBR 模型資料從 `fhir_resources/valuesets/arc-hbr-model.json` 載入
- Cox proportional hazards 轉換
- 基線風險率：出血 2.5%、血栓 2.5%
- 支援互動式因子切換重新計算

## 驗證: TC-008 (verify_tradeoff.py)

---

## SDS-008: CDS Hooks 端點設計

## Design ID: SDS-008
## 追溯需求: SRS-008

## 軟體模組
**模組**: `routes/hooks.py`

## 設計描述
- CDS Hooks v1.2 規範實作
- medication-prescribe: 偵測 DAPT/抗凝藥 → 產生 warning card
- patient-view: 計算 HBR 分數 → 產生 info card
- CORS: 所有來源（規範要求）
- CSRF 豁免（CDS Hooks 規範要求）
- Card 結構：summary, indicator, source, suggestions

## 驗證: TC-009

---

## SDS-009: TW Core 適配器設計

## Design ID: SDS-009
## 追溯需求: SRS-009

## 軟體模組
**模組**: `services/twcore_adapter.py`
**類別**: `TWCoreAdapter`

## 設計描述
- 中文字元偵測（`contains_chinese`）
- 身分證號擷取：身分證 / 居留證 / 病歷號
- NHI 藥品代碼擷取：coding system 匹配 + 正則模式
- ICD-10-CM 診斷代碼擷取
- 預設啟用（`use_twcore=True`）

## 驗證: TC-010

---

## SDS-010: 稽核日誌模組設計

## Design ID: SDS-010
## 追溯需求: SRS-010

## 軟體模組
**模組**: `services/audit_logger.py`
**類別**: `AuditLogger`

## 設計描述
- SHA-256 雜湊鏈：每筆日誌包含前一筆的雜湊值
- JSON Lines 格式：append-only，執行緒安全
- 自動路徑偵測：本地 vs GAE 環境
- 唯讀檔案系統回退：降級到應用程式日誌
- ePHI 過濾器：正則遮罩病人資料

## 驗證: TC-011

---

## SDS-011: 同意服務設計

## Design ID: SDS-011
## 追溯需求: SRS-011

## 軟體模組
**模組**: `services/consent_service.py`
**類別**: `ConsentService`

## 設計描述
- FHIR Consent 資源查詢
- Permit/Deny provision 處理
- 優雅降級：FHIR 伺服器不支援時繼續運作

## 驗證: TC-012

---

## SDS-012: 臨床狀態檢測模組設計

## Design ID: SDS-012
## 追溯需求: SRS-012

## 軟體模組
**模組**: `services/condition_checker.py`
**類別**: `ConditionChecker`

## 設計描述
- 多層代碼匹配：SNOMED-CT → ICD-10-CM → 文字關鍵字
- Config-driven 代碼清單（cdss_config.json）
- 惡性腫瘤排除規則：排除皮膚癌，限 12 個月內
- 用藥匹配：RxNorm + NHI 代碼 + 藥名關鍵字

## 驗證: TC-013

---
