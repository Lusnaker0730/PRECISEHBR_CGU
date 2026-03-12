#!/usr/bin/env python3
"""
批次建立 PRECISE-HBR 法規追溯 GitHub Issues
=============================================
依據 IEC 62304 / ISO 14971 標準，自動建立：
- SRS (軟體需求規格) Issues
- SDS (軟體設計規格) Issues
- RISK (風險分析) Issues
- TC (測試案例) Issues

用法: python scripts/create_regulatory_issues.py [--dry-run]
"""

import json
import os
import sys
import time
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("Github_token") or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
REPO_OWNER = "Lusnaker0730"
REPO_NAME = "smart_fhir_app"
API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# ============================================================
# Labels 定義
# ============================================================
LABELS = [
    {"name": "requirement",  "color": "0075ca", "description": "軟體需求規格 (SRS) - IEC 62304 §5.2"},
    {"name": "design",       "color": "a2eeef", "description": "軟體設計規格 (SDS) - IEC 62304 §5.3"},
    {"name": "risk",         "color": "d73a4a", "description": "風險分析 (ISO 14971)"},
    {"name": "test",         "color": "0e8a16", "description": "測試案例 (V&V) - IEC 62304 §5.5"},
    {"name": "verification", "color": "5319e7", "description": "驗證項目 - IEC 62304 §5.5"},
    {"name": "IEC-62304",    "color": "fbca04", "description": "IEC 62304 醫療器材軟體生命週期"},
    {"name": "ISO-14971",    "color": "f9d0c4", "description": "ISO 14971 風險管理"},
    {"name": "class-A",      "color": "c5def5", "description": "IEC 62304 Class A - 無傷害可能"},
    {"name": "class-B",      "color": "fef2c0", "description": "IEC 62304 Class B - 非嚴重傷害可能"},
    {"name": "class-C",      "color": "e99695", "description": "IEC 62304 Class C - 死亡或嚴重傷害可能"},
]

# ============================================================
# SRS (軟體需求規格) 定義
# ============================================================
SRS_ITEMS = [
    {
        "id": "SRS-001",
        "title": "[SRS-001] 系統應根據病人臨床資料計算 PRECISE-HBR 出血風險分數",
        "labels": ["requirement", "IEC-62304", "class-C"],
        "body": """## Requirement ID
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
- SRS-002（風險分類）、SRS-003（單位轉換）"""
    },
    {
        "id": "SRS-002",
        "title": "[SRS-002] 系統應依據 PRECISE-HBR 分數將病人分類為風險等級",
        "labels": ["requirement", "IEC-62304", "class-C"],
        "body": """## Requirement ID
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
- [x] 單元測試：`tests/test_risk_classifier.py`"""
    },
    {
        "id": "SRS-003",
        "title": "[SRS-003] 系統應支援實驗室值單位自動轉換",
        "labels": ["requirement", "IEC-62304", "class-B"],
        "body": """## Requirement ID
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
- [x] 單元測試：`tests/test_unit_conversion_service.py`"""
    },
    {
        "id": "SRS-004",
        "title": "[SRS-004] 系統應透過 FHIR R4 API 擷取病人臨床資料",
        "labels": ["requirement", "IEC-62304", "class-B"],
        "body": """## Requirement ID
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
- [x] 整合測試"""
    },
    {
        "id": "SRS-005",
        "title": "[SRS-005] 系統應實作 SMART on FHIR OAuth2 + PKCE 認證授權",
        "labels": ["requirement", "IEC-62304", "class-B"],
        "body": """## Requirement ID
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
- [x] 單元測試：`tests/test_auth_security.py`, `tests/test_oidc_validator.py`, `tests/test_smart_security.py`"""
    },
    {
        "id": "SRS-006",
        "title": "[SRS-006] 系統應實作輸入驗證與安全防護機制",
        "labels": ["requirement", "IEC-62304", "class-B"],
        "body": """## Requirement ID
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
- [x] 安全測試：`tests/test_security_comprehensive.py`, `tests/test_patient_context.py`"""
    },
    {
        "id": "SRS-007",
        "title": "[SRS-007] 系統應提供出血-血栓事件權衡分析",
        "labels": ["requirement", "IEC-62304", "class-B"],
        "body": """## Requirement ID
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
- [x] 單元測試：`tests/verify_tradeoff.py`"""
    },
    {
        "id": "SRS-008",
        "title": "[SRS-008] 系統應實作 CDS Hooks v1.2 整合介面",
        "labels": ["requirement", "IEC-62304", "class-B"],
        "body": """## Requirement ID
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
- [x] 單元測試：`tests/test_hooks.py`"""
    },
    {
        "id": "SRS-009",
        "title": "[SRS-009] 系統應支援台灣核心實作指引 (TW Core IG)",
        "labels": ["requirement", "IEC-62304", "class-A"],
        "body": """## Requirement ID
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
- [x] 單元測試：`tests/test_twcore_adapter.py`"""
    },
    {
        "id": "SRS-010",
        "title": "[SRS-010] 系統應實作 ePHI 存取稽核日誌",
        "labels": ["requirement", "IEC-62304", "class-B"],
        "body": """## Requirement ID
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
- [x] 單元測試：`tests/test_audit_logger_extended.py`, `tests/test_ephi_protection.py`"""
    },
    {
        "id": "SRS-011",
        "title": "[SRS-011] 系統應實作 FHIR Consent 同意管理",
        "labels": ["requirement", "IEC-62304", "class-B"],
        "body": """## Requirement ID
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
- [x] 單元測試：`tests/test_consent_service.py`"""
    },
    {
        "id": "SRS-012",
        "title": "[SRS-012] 系統應自動偵測臨床狀態與用藥以計算 HBR 因子",
        "labels": ["requirement", "IEC-62304", "class-C"],
        "body": """## Requirement ID
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
- [x] 單元測試：`tests/test_condition_checker_config.py`, `tests/test_fhir_service.py`"""
    },
]

# ============================================================
# SDS (軟體設計規格) 定義
# ============================================================
SDS_ITEMS = [
    {
        "id": "SDS-001",
        "title": "[SDS-001] PRECISE-HBR 分數計算模組設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-001
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

## 驗證: TC-001, TC-002"""
    },
    {
        "id": "SDS-002",
        "title": "[SDS-002] 風險分類模組設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-002
## 追溯需求: SRS-002

## 軟體模組
**模組**: `services/risk_classifier.py`
**類別**: `RiskClassifierService`

## 設計描述
- 閾值驅動分類：Non-HBR (≤22) / HBR (23-26) / Very-HBR (≥27)
- 出血風險百分比校準曲線（PRECISE-HBR 驗證研究）
- 回傳結構化字典：score, risk_category, bleeding_risk_percent, color_class, recommendation

## 驗證: TC-003"""
    },
    {
        "id": "SDS-003",
        "title": "[SDS-003] 實驗室值單位轉換服務設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-003
## 追溯需求: SRS-003

## 軟體模組
**模組**: `services/unit_conversion_service.py`
**類別**: `UnitConversionService`

## 設計描述
- Config-driven 轉換因子（從 cdss_config.json 載入）
- 支援 UCUM 單位變體（大小寫不敏感）
- CKD-EPI 2021 無種族 eGFR 公式（性別特異性 κ/α 係數）
- 未知單位回傳 None（不猜測）

## 驗證: TC-004"""
    },
    {
        "id": "SDS-004",
        "title": "[SDS-004] FHIR 客戶端服務設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-004
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

## 驗證: TC-005"""
    },
    {
        "id": "SDS-005",
        "title": "[SDS-005] OAuth2/PKCE 認證流程設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-005
## 追溯需求: SRS-005

## 軟體模組
**模組**: `routes/auth_routes.py`, `utils/oidc_validator.py`

## 設計描述
- SMART on FHIR v2.0 OAuth2 authorization code flow
- PKCE: cryptographic code_verifier (≥43 chars) + SHA-256 challenge
- State parameter: 一次性消費，防 CSRF
- OIDC id_token 驗證：RS256/ES256 only，JWKS 快取 1 小時
- Token refresh: 最小間隔 30 秒

## 驗證: TC-006"""
    },
    {
        "id": "SDS-006",
        "title": "[SDS-006] 輸入驗證模組設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-006
## 追溯需求: SRS-006

## 軟體模組
**模組**: `utils/input_validator.py`, `utils/patient_context.py`

## 設計描述
- URL 驗證：DNS 解析 + 私有 IP 封鎖 + cloud metadata 封鎖
- Patient ID：正則驗證 + 長度限制
- FHIR 搜尋參數：白名單 + 注入模式偵測
- BOLA 防護：session patient_id vs request patient_id 比對

## 驗證: TC-007"""
    },
    {
        "id": "SDS-007",
        "title": "[SDS-007] 權衡分析模組設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-007
## 追溯需求: SRS-007

## 軟體模組
**模組**: `services/tradeoff_model_calculator.py`
**類別**: `TradeoffModelCalculator`

## 設計描述
- ARC-HBR 模型資料從 `fhir_resources/valuesets/arc-hbr-model.json` 載入
- Cox proportional hazards 轉換
- 基線風險率：出血 2.5%、血栓 2.5%
- 支援互動式因子切換重新計算

## 驗證: TC-008 (verify_tradeoff.py)"""
    },
    {
        "id": "SDS-008",
        "title": "[SDS-008] CDS Hooks 端點設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-008
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

## 驗證: TC-009"""
    },
    {
        "id": "SDS-009",
        "title": "[SDS-009] TW Core 適配器設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-009
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

## 驗證: TC-010"""
    },
    {
        "id": "SDS-010",
        "title": "[SDS-010] 稽核日誌模組設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-010
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

## 驗證: TC-011"""
    },
    {
        "id": "SDS-011",
        "title": "[SDS-011] 同意服務設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-011
## 追溯需求: SRS-011

## 軟體模組
**模組**: `services/consent_service.py`
**類別**: `ConsentService`

## 設計描述
- FHIR Consent 資源查詢
- Permit/Deny provision 處理
- 優雅降級：FHIR 伺服器不支援時繼續運作

## 驗證: TC-012"""
    },
    {
        "id": "SDS-012",
        "title": "[SDS-012] 臨床狀態檢測模組設計",
        "labels": ["design", "IEC-62304"],
        "body": """## Design ID: SDS-012
## 追溯需求: SRS-012

## 軟體模組
**模組**: `services/condition_checker.py`
**類別**: `ConditionChecker`

## 設計描述
- 多層代碼匹配：SNOMED-CT → ICD-10-CM → 文字關鍵字
- Config-driven 代碼清單（cdss_config.json）
- 惡性腫瘤排除規則：排除皮膚癌，限 12 個月內
- 用藥匹配：RxNorm + NHI 代碼 + 藥名關鍵字

## 驗證: TC-013"""
    },
]

# ============================================================
# RISK (風險分析) 定義
# ============================================================
RISK_ITEMS = [
    {
        "id": "RISK-001",
        "title": "[RISK-001] 分數計算錯誤導致不當 DAPT 療程決策",
        "labels": ["risk", "ISO-14971", "class-C"],
        "body": """## Risk ID: RISK-001

## 危害描述
PRECISE-HBR 分數計算錯誤（係數/截斷/四捨五入），導致：
- **低估** → 高出血風險病人被分類為 non-HBR → 較長 DAPT → 增加出血風險
- **高估** → 低風險病人被分類為 HBR → 較短 DAPT → 增加血栓風險

## 傷害
- BARC 3/5 等級出血事件、支架內血栓、嚴重可致死

## 風險估計（控制前）
- 嚴重度: 5 (災難性) | 機率: 3 (偶爾) | 風險等級: 15 — **不可接受**

## 風險控制措施
1. Golden dataset 驗證（verify_precise_hbr.py）
2. 邊界值分析測試
3. Config-driven 係數（可由臨床團隊獨立審查）
4. 單元測試覆蓋每個分數組成
5. PR code review

## 風險估計（控制後）
- 殘餘嚴重度: 5 | 殘餘機率: 1 (極罕見) | 殘餘風險: 5 — **可接受（附理由）**

## 追溯
- 需求: SRS-001, SRS-002, SRS-012
- 設計: SDS-001
- 驗證: TC-001, TC-002, TC-003"""
    },
    {
        "id": "RISK-002",
        "title": "[RISK-002] 風險分類閾值錯誤導致分類不正確",
        "labels": ["risk", "ISO-14971", "class-C"],
        "body": """## Risk ID: RISK-002

## 危害描述
風險分類閾值設定錯誤（22/23/27 邊界），導致邊界分數的病人被錯誤分類。

## 傷害
- 同 RISK-001：不當 DAPT 療程決策

## 風險估計（控制前）
- 嚴重度: 5 | 機率: 2 (罕見) | 風險等級: 10

## 風險控制措施
1. 閾值從 cdss_config.json 載入（可審查）
2. 邊界值測試（22/23/26/27）
3. 單元測試覆蓋所有分類結果

## 風險估計（控制後）
- 殘餘風險: 5 × 1 = 5 — **可接受**

## 追溯
- 需求: SRS-002 | 設計: SDS-002 | 驗證: TC-003"""
    },
    {
        "id": "RISK-003",
        "title": "[RISK-003] 單位轉換錯誤導致計算輸入不正確",
        "labels": ["risk", "ISO-14971", "class-B"],
        "body": """## Risk ID: RISK-003

## 危害描述
實驗室值單位轉換錯誤（例如 g/L → g/dL 轉換因子錯誤），導致 Hb/eGFR/WBC 輸入值不正確。

## 傷害
- 分數偏差，影響風險分類

## 風險估計（控制前）
- 嚴重度: 4 (嚴重) | 機率: 2 (罕見) | 風險等級: 8

## 風險控制措施
1. Config-driven 轉換因子
2. 已知轉換值的單元測試
3. 未知單位回傳 None（不猜測）

## 風險估計（控制後）
- 殘餘風險: 4 × 1 = 4 — **可接受**

## 追溯
- 需求: SRS-003 | 設計: SDS-003 | 驗證: TC-004"""
    },
    {
        "id": "RISK-004",
        "title": "[RISK-004] FHIR 資料擷取失敗或不完整",
        "labels": ["risk", "ISO-14971", "class-B"],
        "body": """## Risk ID: RISK-004

## 危害描述
FHIR 伺服器逾時、連線失敗、或回傳不完整資料，導致計算使用預設值而非實際值。

## 傷害
- 分數可能低估（缺失資料不加分）

## 風險估計（控制前）
- 嚴重度: 3 (中等) | 機率: 3 (偶爾) | 風險等級: 9

## 風險控制措施
1. 缺失欄位追蹤與警告
2. 15 秒超時設定
3. UI 顯示資料完整性警告
4. 實驗室值時效性檢查（>90天警告）

## 風險估計（控制後）
- 殘餘風險: 3 × 2 = 6 — **可接受（附理由）**

> 理由：系統為輔助工具，臨床醫師可見資料完整性警告

## 追溯
- 需求: SRS-004 | 設計: SDS-004 | 驗證: TC-005"""
    },
    {
        "id": "RISK-005",
        "title": "[RISK-005] 認證繞過或 Token 洩露導致未授權存取",
        "labels": ["risk", "ISO-14971", "class-B"],
        "body": """## Risk ID: RISK-005

## 危害描述
OAuth2 認證流程被繞過、Token 被竊取或重播，導致未授權人員存取病人資料。

## 傷害
- ePHI 資料洩露、違反 HIPAA/個資法

## 風險估計（控制前）
- 嚴重度: 4 | 機率: 2 | 風險等級: 8

## 風險控制措施
1. PKCE（防 authorization code 攔截）
2. State 參數（防 CSRF）
3. OIDC id_token 簽章驗證（拒絕 HS256/none）
4. Session 安全（httponly, secure, samesite）

## 風險估計（控制後）
- 殘餘風險: 4 × 1 = 4 — **可接受**

## 追溯
- 需求: SRS-005 | 設計: SDS-005 | 驗證: TC-006"""
    },
    {
        "id": "RISK-006",
        "title": "[RISK-006] 注入攻擊（XSS/SQLi/SSRF/命令注入）",
        "labels": ["risk", "ISO-14971", "class-B"],
        "body": """## Risk ID: RISK-006

## 危害描述
攻擊者透過惡意輸入進行 XSS、SQL 注入、SSRF 或命令注入攻擊。

## 傷害
- 資料洩露、系統被入侵、ePHI 外洩

## 風險估計（控制前）
- 嚴重度: 4 | 機率: 3 | 風險等級: 12

## 風險控制措施
1. SSRF 防護（DNS 解析 + 私有 IP 封鎖）
2. 輸入驗證（白名單 + 注入模式偵測）
3. CSP nonce + HSTS
4. CSRF 保護
5. 速率限制

## 風險估計（控制後）
- 殘餘風險: 4 × 1 = 4 — **可接受**

## 追溯
- 需求: SRS-006 | 設計: SDS-006 | 驗證: TC-007, TC-014"""
    },
    {
        "id": "RISK-007",
        "title": "[RISK-007] 權衡分析計算錯誤",
        "labels": ["risk", "ISO-14971", "class-B"],
        "body": """## Risk ID: RISK-007

## 危害描述
出血-血栓權衡分析的 hazard ratio 或基線風險率錯誤，導致風險比較不準確。

## 傷害
- 治療決策參考資訊不準確

## 風險估計（控制前）
- 嚴重度: 3 | 機率: 2 | 風險等級: 6

## 風險控制措施
1. 模型資料從驗證過的 JSON 檔載入
2. 驗證測試（verify_tradeoff.py）

## 風險估計（控制後）
- 殘餘風險: 3 × 1 = 3 — **可接受**

## 追溯
- 需求: SRS-007 | 設計: SDS-007"""
    },
    {
        "id": "RISK-008",
        "title": "[RISK-008] ePHI 資料意外洩露至日誌或錯誤訊息",
        "labels": ["risk", "ISO-14971", "class-B"],
        "body": """## Risk ID: RISK-008

## 危害描述
病人健康資料（ePHI）意外出現在應用程式日誌、錯誤頁面或 HTTP 回應中。

## 傷害
- 違反 HIPAA/個資法、病人隱私受損

## 風險估計（控制前）
- 嚴重度: 4 | 機率: 3 | 風險等級: 12

## 風險控制措施
1. ePHI 日誌過濾器（正則遮罩）
2. 錯誤頁面不洩露堆疊追蹤
3. 稽核日誌獨立於應用程式日誌
4. Patient ID 遮罩

## 風險估計（控制後）
- 殘餘風險: 4 × 1 = 4 — **可接受**

## 追溯
- 需求: SRS-010 | 設計: SDS-010 | 驗證: TC-011, TC-013"""
    },
    {
        "id": "RISK-009",
        "title": "[RISK-009] 病人資料混淆 (BOLA/IDOR)",
        "labels": ["risk", "ISO-14971", "class-C"],
        "body": """## Risk ID: RISK-009

## 危害描述
攻擊者或系統錯誤導致存取非授權病人的資料（Broken Object Level Authorization）。

## 傷害
- 錯誤病人的分數被使用、隱私侵害、錯誤治療決策

## 風險估計（控制前）
- 嚴重度: 5 | 機率: 2 | 風險等級: 10

## 風險控制措施
1. `@require_patient_context` 裝飾器
2. Session patient_id vs request patient_id 比對
3. 稽核日誌記錄所有 patient context 違規

## 風險估計（控制後）
- 殘餘風險: 5 × 1 = 5 — **可接受（附理由）**

## 追溯
- 需求: SRS-006 | 設計: SDS-006 | 驗證: TC-007"""
    },
]

# ============================================================
# TC (測試案例) 定義
# ============================================================
TC_ITEMS = [
    {
        "id": "TC-001",
        "title": "[TEST] TC-001: Golden Dataset 驗證 PRECISE-HBR 計算正確性",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-001
## 追溯: SRS-001 → SDS-001 → RISK-001

## 測試檔案
`tests/verify_precise_hbr.py::test_golden_dataset_verification`

## 測試步驟
1. 使用獨立參考實作計算 20 組隨機病人預期分數
2. 使用 `PreciseHBRCalculator.calculate_pure_score()` 計算同組資料
3. 比較差異

## 通過條件
每組差異 < 1 分（四捨五入誤差範圍）"""
    },
    {
        "id": "TC-002",
        "title": "[TEST] TC-002: 邊界值測試 PRECISE-HBR 計算截斷邏輯",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-002
## 追溯: SRS-001 → SDS-001 → RISK-001

## 測試檔案
`tests/verify_precise_hbr.py::test_boundary_values`

## 測試步驟
測試所有截斷邊界：Age 30/80、Hb 5.0/15.0、eGFR 5/100、WBC 3.0/15.0

## 通過條件
所有邊界值的分數與手算結果一致"""
    },
    {
        "id": "TC-003",
        "title": "[TEST] TC-003: 風險分類閾值驗證",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-003
## 追溯: SRS-002 → SDS-002 → RISK-001, RISK-002

## 測試檔案
`tests/test_risk_classifier.py`

## 測試步驟
驗證分數 0/22/23/26/27/50 的風險分類結果

## 通過條件
- ≤22 → Non-HBR
- 23-26 → HBR
- ≥27 → Very HBR"""
    },
    {
        "id": "TC-004",
        "title": "[TEST] TC-004: 實驗室值單位轉換驗證",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-004
## 追溯: SRS-003 → SDS-003 → RISK-003

## 測試檔案
`tests/test_unit_conversion_service.py`

## 通過條件
- Hb g/L → g/dL 轉換正確
- Hb mmol/L → g/dL 轉換正確
- Creatinine µmol/L → mg/dL 轉換正確
- 未知單位回傳 None"""
    },
    {
        "id": "TC-005",
        "title": "[TEST] TC-005: FHIR 資料擷取功能驗證",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-005
## 追溯: SRS-004 → SDS-004 → RISK-004

## 測試檔案
`tests/test_fhir_service.py`

## 通過條件
- Patient demographics 正確擷取
- Observation 值正確解析
- 錯誤處理正確（超時、無效回應）"""
    },
    {
        "id": "TC-006",
        "title": "[TEST] TC-006: OAuth2/PKCE 認證安全驗證",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-006
## 追溯: SRS-005 → SDS-005 → RISK-005

## 測試檔案
`tests/test_auth_security.py`, `tests/test_oidc_validator.py`, `tests/test_smart_security.py`, `tests/test_mfa_validator.py`

## 通過條件
- PKCE 參數正確生成與驗證
- State 參數一次性消費
- OIDC token 驗證拒絕 HS256/none
- Session 不含明文敏感資料"""
    },
    {
        "id": "TC-007",
        "title": "[TEST] TC-007: 輸入驗證與 BOLA 防護測試",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-007
## 追溯: SRS-006 → SDS-006 → RISK-006, RISK-009

## 測試檔案
`tests/test_input_validation.py`, `tests/test_input_validator_module.py`, `tests/test_patient_context.py`

## 通過條件
- SSRF 攻擊被阻擋
- XSS/SQLi/命令注入被防護
- BOLA 攻擊被阻擋
- Patient ID 格式驗證正確"""
    },
    {
        "id": "TC-008",
        "title": "[TEST] TC-008: 權衡分析模型驗證",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-008
## 追溯: SRS-007 → SDS-007 → RISK-007

## 測試檔案
`tests/verify_tradeoff.py`

## 通過條件
- 缺失資料行為正確
- 高風險病人分數合理"""
    },
    {
        "id": "TC-009",
        "title": "[TEST] TC-009: CDS Hooks 整合驗證",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-009
## 追溯: SRS-008 → SDS-008

## 測試檔案
`tests/test_hooks.py`

## 通過條件
- 服務發現回傳正確 JSON
- medication-prescribe Hook 正確偵測用藥
- Warning Card 包含必要欄位
- CORS headers 正確"""
    },
    {
        "id": "TC-010",
        "title": "[TEST] TC-010: TW Core 適配器驗證",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-010
## 追溯: SRS-009 → SDS-009

## 測試檔案
`tests/test_twcore_adapter.py`

## 通過條件
- 中文姓名正確擷取
- 身分證號正確擷取
- NHI 藥品代碼正確擷取
- ICD-10 診斷代碼正確擷取"""
    },
    {
        "id": "TC-011",
        "title": "[TEST] TC-011: ePHI 稽核日誌驗證",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-011
## 追溯: SRS-010 → SDS-010 → RISK-008

## 測試檔案
`tests/test_audit_logger_extended.py`, `tests/test_ephi_protection.py`

## 通過條件
- 雜湊鏈完整性驗證通過
- 竄改偵測正確
- 必要欄位（timestamp, user_id, action）存在
- ePHI 不出現在一般日誌中"""
    },
    {
        "id": "TC-012",
        "title": "[TEST] TC-012: 同意服務驗證",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-012
## 追溯: SRS-011 → SDS-011

## 測試檔案
`tests/test_consent_service.py`

## 通過條件
- ConsentStatus/ConsentProvision 列舉正確
- ConsentResult 正確建立
- ConsentService 初始化正確"""
    },
    {
        "id": "TC-013",
        "title": "[TEST] TC-013: 臨床狀態檢測驗證",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-013
## 追溯: SRS-012 → SDS-012 → RISK-001

## 測試檔案
`tests/test_condition_checker_config.py`, `tests/test_fhir_service.py`

## 通過條件
- ICD-10 出血診斷碼偵測正確
- ICD-10 惡性腫瘤碼偵測正確
- NHI 抗凝藥代碼偵測正確
- NHI NSAID 代碼偵測正確"""
    },
    {
        "id": "TC-014",
        "title": "[TEST] TC-014: OWASP Top 10 安全測試",
        "labels": ["test", "verification", "IEC-62304"],
        "body": """## Test ID: TC-014
## 追溯: SRS-006 → RISK-006

## 測試檔案
`tests/test_security_comprehensive.py`

## 通過條件
- OWASP A01-A10 全部測試通過
- 包含：注入、認證失敗、敏感資料暴露、XXE、存取控制、安全配置、XSS、不安全反序列化、已知漏洞、日誌監控不足"""
    },
]

# ============================================================
# 主程式
# ============================================================
def ensure_labels(session):
    """建立所有法規標籤（如果不存在）"""
    print("=== 建立法規標籤 ===")
    existing = session.get(f"{API_BASE}/labels", params={"per_page": 100})
    existing_names = {l["name"] for l in existing.json()} if existing.ok else set()

    for label in LABELS:
        if label["name"] in existing_names:
            print(f"  [跳過] {label['name']} (已存在)")
            continue
        resp = session.post(f"{API_BASE}/labels", json=label)
        if resp.ok:
            print(f"  [建立] {label['name']}")
        else:
            print(f"  [錯誤] {label['name']}: {resp.status_code} {resp.text[:100]}")
        time.sleep(0.3)


def create_issues(session, items, category, dry_run=False):
    """批次建立 issues"""
    print(f"\n=== 建立 {category} Issues ({len(items)} 個) ===")
    created = []

    for item in items:
        title = item["title"]
        # Check if issue already exists
        search_resp = session.get(
            "https://api.github.com/search/issues",
            params={
                "q": f'repo:{REPO_OWNER}/{REPO_NAME} is:issue in:title "{item["id"]}"',
                "per_page": 1,
            },
        )
        if search_resp.ok and search_resp.json().get("total_count", 0) > 0:
            existing = search_resp.json()["items"][0]
            print(f"  [跳過] {item['id']}: #{existing['number']} (已存在)")
            created.append({"id": item["id"], "number": existing["number"]})
            time.sleep(0.5)
            continue

        if dry_run:
            print(f"  [模擬] {item['id']}: {title}")
            continue

        payload = {
            "title": title,
            "body": item["body"],
            "labels": item["labels"],
        }
        resp = session.post(f"{API_BASE}/issues", json=payload)
        if resp.ok:
            number = resp.json()["number"]
            print(f"  [建立] {item['id']}: #{number}")
            created.append({"id": item["id"], "number": number})
        else:
            print(f"  [錯誤] {item['id']}: {resp.status_code} {resp.text[:200]}")

        time.sleep(1)  # Rate limit

    return created


def main():
    parser = argparse.ArgumentParser(description="批次建立 PRECISE-HBR 法規 GitHub Issues")
    parser.add_argument("--dry-run", action="store_true", help="模擬執行，不實際建立")
    args = parser.parse_args()

    if not GITHUB_TOKEN:
        print("錯誤: 找不到 GitHub Token。請在 .env 設定 Github_token")
        sys.exit(1)

    session = requests.Session()
    session.headers.update(HEADERS)

    # 驗證 token
    user_resp = session.get("https://api.github.com/user")
    if not user_resp.ok:
        print(f"錯誤: GitHub Token 無效 ({user_resp.status_code})")
        sys.exit(1)
    print(f"已認證為: {user_resp.json().get('login')}\n")

    if args.dry_run:
        print("*** 模擬模式 - 不會實際建立 ***\n")

    # Step 1: Labels
    if not args.dry_run:
        ensure_labels(session)

    # Step 2: Issues
    srs_created = create_issues(session, SRS_ITEMS, "SRS (軟體需求規格)", args.dry_run)
    sds_created = create_issues(session, SDS_ITEMS, "SDS (軟體設計規格)", args.dry_run)
    risk_created = create_issues(session, RISK_ITEMS, "RISK (風險分析)", args.dry_run)
    tc_created = create_issues(session, TC_ITEMS, "TC (測試案例)", args.dry_run)

    # Summary
    total = len(srs_created) + len(sds_created) + len(risk_created) + len(tc_created)
    print(f"\n=== 完成 ===")
    print(f"SRS: {len(srs_created)} | SDS: {len(sds_created)} | RISK: {len(risk_created)} | TC: {len(tc_created)}")
    print(f"總計: {total} 個 issues")

    if not args.dry_run:
        # Save issue number mapping
        mapping = {}
        for item in srs_created + sds_created + risk_created + tc_created:
            mapping[item["id"]] = item.get("number")
        with open("reports/regulatory-issue-mapping.json", "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
        print(f"\nIssue 編號對應已儲存至 reports/regulatory-issue-mapping.json")


if __name__ == "__main__":
    main()
