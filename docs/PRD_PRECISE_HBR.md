# PRECISE-HBR 智慧 FHIR 應用程式
## 產品需求規格書 (PRD)

**版本**: 1.0.0
**文件狀態**: 正式版
**最後更新**: 2026-01-13
**文件負責人**: 產品團隊

---

## 目錄

1. [產品概述](#1-產品概述)
2. [產品願景與目標](#2-產品願景與目標)
3. [目標用戶](#3-目標用戶)
4. [功能需求](#4-功能需求)
5. [非功能需求](#5-非功能需求)
6. [系統架構](#6-系統架構)
7. [整合規範](#7-整合規範)
8. [安全與合規](#8-安全與合規)
9. [使用者介面設計](#9-使用者介面設計)
10. [資料模型](#10-資料模型)
11. [API 規格](#11-api-規格)
12. [部署與維運](#12-部署與維運)
13. [測試策略](#13-測試策略)
14. [風險評估](#14-風險評估)
15. [附錄](#15-附錄)

---

## 1. 產品概述

### 1.1 產品簡介

PRECISE-HBR SMART on FHIR 是一款臨床決策支援系統 (Clinical Decision Support System, CDSS)，專為評估接受經皮冠狀動脈介入治療 (PCI) 患者的高出血風險而設計。本產品整合 HL7 FHIR R4 標準與 CDS Hooks 規範，可無縫嵌入醫療資訊系統，為臨床醫師提供即時、準確的出血風險評估。

### 1.2 產品定位

| 項目 | 說明 |
|------|------|
| **產品類型** | 醫療決策支援軟體 (SaMD) |
| **目標市場** | 心臟科、介入性心臟科、急診科 |
| **技術標準** | SMART on FHIR、CDS Hooks 1.0、HL7 FHIR R4 |
| **法規分類** | 第二類醫療器材軟體 |

### 1.3 產品背景

經皮冠狀動脈介入治療後的雙重抗血小板治療 (DAPT) 是預防支架血栓的標準療法，但同時增加出血風險。PRECISE-HBR 評分系統是經過臨床驗證的出血風險預測工具，本產品將此評分系統數位化並整合至電子病歷系統，實現自動化風險評估。

---

## 2. 產品願景與目標

### 2.1 產品願景

**「透過智慧化臨床決策支援，協助醫師在出血與血栓風險之間做出最佳治療決策，提升 PCI 患者的治療安全性與預後。」**

### 2.2 業務目標

| 目標 | 關鍵結果 (KR) | 衡量指標 |
|------|--------------|----------|
| 提升風險評估效率 | 將風險評估時間縮短 80% | 從手動 5 分鐘降至自動 1 分鐘內 |
| 提高評估準確性 | 消除人工計算錯誤 | 100% 符合原始演算法 |
| 改善臨床決策品質 | 提供客觀風險數據 | 醫師滿意度 > 85% |
| 符合法規要求 | 通過 ONC 認證要求 | 100% 合規達成率 |

### 2.3 成功指標

- **採用率**: 目標醫院內 70% 的心臟科醫師使用本系統
- **使用頻率**: 每位使用者每週平均使用 10 次以上
- **準確性**: 風險評分與臨床結果相關性 > 0.8 (AUC-ROC)
- **系統可用性**: 99.5% 以上的服務可用時間

---

## 3. 目標用戶

### 3.1 主要用戶 (Primary Users)

#### 3.1.1 介入性心臟科醫師
- **角色描述**: 執行 PCI 手術的專科醫師
- **使用情境**: 術前評估、DAPT 療程規劃
- **核心需求**: 快速獲取出血風險、輔助治療決策
- **痛點**: 手動計算耗時、多系統切換不便

#### 3.1.2 心臟內科醫師
- **角色描述**: 負責冠心病患者長期照護
- **使用情境**: 門診追蹤、藥物調整
- **核心需求**: 監控風險變化、評估治療效果
- **痛點**: 缺乏整合性風險評估工具

### 3.2 次要用戶 (Secondary Users)

#### 3.2.1 臨床藥師
- **使用情境**: 審核 DAPT 處方、藥物交互作用檢查
- **核心需求**: 確認高風險患者的用藥安全

#### 3.2.2 護理師
- **使用情境**: 患者教育、出院準備
- **核心需求**: 了解患者風險等級以進行衛教

### 3.3 利害關係人 (Stakeholders)

| 角色 | 關注重點 |
|------|----------|
| 醫療資訊部門 | 系統整合、資安合規 |
| 品質管理部門 | 臨床決策品質、病安指標 |
| 醫院管理層 | 投資報酬率、法規遵循 |
| 法規主管機關 | 醫療器材安全性、有效性 |

---

## 4. 功能需求

### 4.1 核心功能模組

#### 4.1.1 PRECISE-HBR 出血風險計算

**功能描述**
基於 7 項臨床參數自動計算 PRECISE-HBR 出血風險評分。

**輸入參數**

| 參數 | 資料類型 | 來源 | 係數 |
|------|----------|------|------|
| 年齡 | 連續變數 (歲) | Patient 資源 | +0.26/年 (30-80歲截斷) |
| 血紅素 | 連續變數 (g/dL) | Observation | +2.5/g/dL 下降 (5-15截斷) |
| eGFR | 連續變數 (mL/min) | Observation/計算 | +0.05/mL/min 下降 (5-100截斷) |
| 白血球數 | 連續變數 (10⁹/L) | Observation | +0.8/10⁹/L 上升 (3-15截斷) |
| 既往出血史 | 布林值 | Condition | +7 分 |
| 長期口服抗凝血劑 | 布林值 | MedicationRequest | +5 分 |
| ARC-HBR 因素 | 布林值 | Condition | +3 分 (任一因素) |

**輸出結果**

| 輸出項目 | 說明 |
|----------|------|
| 總分 | 整數，範圍 2-60+ |
| 風險等級 | 非高風險 (≤22) / 高風險 (23-26) / 極高風險 (≥27) |
| 1 年出血風險率 | 百分比 (BARC 3 或 5 型出血) |
| 各項目貢獻度 | 每個參數的分數貢獻 |

**業務規則**
- BR-001: 缺少任一必要參數時，顯示警告並要求手動輸入
- BR-002: eGFR 不可用時，自動從肌酸酐計算
- BR-003: 檢驗值超過 3 個月標記為過期

#### 4.1.2 出血-血栓權衡分析

**功能描述**
同時評估出血與血栓風險，提供視覺化權衡分析圖表。

**分析模型**
- 基於 JAMA Cardiology 研究的雙風險預測模型
- 支援 26+ 臨床因素的動態調整
- 即時重算功能

**視覺化元素**
- 散點圖：出血風險 vs. 血栓風險
- 參考線：等權衡線 (1:1)、死亡率加權線 (1:1.9)
- 風險區域：顏色編碼的風險象限

**互動功能**
- 勾選/取消勾選風險因素
- 即時更新風險數值
- 因素分類顯示 (影響出血/血栓/兩者)

#### 4.1.3 CDS Hooks 臨床整合

**功能描述**
透過 CDS Hooks 標準提供即時臨床警示。

**支援的 Hooks**

| Hook 類型 | 觸發時機 | 回應內容 |
|-----------|----------|----------|
| patient-view | 開啟病歷時 | 風險評估卡片 |
| medication-prescribe | 開立處方時 | 高風險用藥警示 |

**警示等級**

| 等級 | 條件 | 顯示樣式 |
|------|------|----------|
| Critical | 分數 ≥27 且處方高風險藥物 | 紅色警告卡片 |
| Warning | 分數 23-26 | 橘色警告卡片 |
| Info | 分數 ≤22 | 藍色資訊卡片 |

#### 4.1.4 資料匯出功能

**功能描述**
提供風險評估結果的複製與匯出功能。

**匯出格式**
- 剪貼簿複製：純文字格式
- C-CDA 文件：符合 ONC 45 CFR 170.315(b)(6) 規範 (規劃中)

**匯出內容**
- 患者基本資料
- 風險評分與等級
- 各項目數值與貢獻度
- 評估時間戳記

### 4.2 輔助功能模組

#### 4.2.1 單位換算

**支援的換算**

| 參數 | 單位選項 |
|------|----------|
| 血紅素 | g/dL ↔ mmol/L |
| eGFR | mL/min/1.73m² |
| 白血球 | 10⁹/L |

#### 4.2.2 數值驗證

**驗證規則**

| 參數 | 有效範圍 | 警告範圍 |
|------|----------|----------|
| 年齡 | 18-120 歲 | >100 歲 |
| 血紅素 | 3-22 g/dL | <7 或 >18 |
| eGFR | 0-200 mL/min | <15 或 >150 |
| 白血球 | 0.1-50 10⁹/L | <4 或 >20 |

#### 4.2.3 問題回報系統

**功能**
- 結構化問題回報表單
- 嚴重程度分級 (Critical/High/Medium/Low)
- CAPTCHA 防護
- 追蹤編號產生

### 4.3 台灣在地化功能

#### 4.3.1 Taiwan Core IG 整合

**支援項目**
- 中文姓名解析 (Patient.name.text)
- 身分證/居留證驗證
- 病歷號碼對應
- 健保藥品代碼 (NHI Code) 對應

#### 4.3.2 在地化調適

**調適邏輯**
- 優先使用 ICD-10-CM 台灣版
- 支援健保署藥品代碼系統
- 中文介面與提示訊息

---

## 5. 非功能需求

### 5.1 效能需求

| 指標 | 目標值 | 測量方式 |
|------|--------|----------|
| 風險計算回應時間 | < 3 秒 | API 回應時間 |
| 頁面載入時間 | < 2 秒 | 首次內容繪製 (FCP) |
| 並發用戶支援 | 100 用戶/實例 | 負載測試 |
| API 吞吐量 | 10 req/min/用戶 | 速率限制 |

### 5.2 可用性需求

| 指標 | 目標值 |
|------|--------|
| 服務可用性 | 99.5% |
| 計畫性維護窗口 | 每月 < 4 小時 |
| 平均故障恢復時間 (MTTR) | < 30 分鐘 |
| 資料備份頻率 | 每日 |

### 5.3 安全性需求

| 需求類別 | 規格 |
|----------|------|
| 傳輸加密 | TLS 1.2+ |
| 認證機制 | OAuth 2.0 + PKCE |
| 會話管理 | HttpOnly、SameSite、Secure Cookies |
| 存取控制 | SMART on FHIR Scopes |
| 稽核日誌 | 防竄改雜湊鏈 |

### 5.4 合規需求

| 法規/標準 | 要求 |
|-----------|------|
| HIPAA | 技術、管理、實體防護措施 |
| ONC 45 CFR 170.315 | (b)(6) 資料匯出、(d)(2) 稽核、(d)(5) 會話逾時 |
| SMART on FHIR | 標準授權流程 |
| FDA SaMD | 第二類醫療器材軟體要求 |

### 5.5 可擴展性需求

| 項目 | 規格 |
|------|------|
| 水平擴展 | 支援 1-10 實例自動擴展 |
| 垂直擴展 | 支援實例規格升級 |
| 多租戶 | 支援多醫院部署 |
| 國際化 | 支援多語言擴展 |

### 5.6 可維護性需求

| 項目 | 規格 |
|------|------|
| 程式碼覆蓋率 | > 80% |
| 文件完整度 | API 文件、使用手冊、技術文件 |
| 日誌標準化 | JSON 結構化日誌 |
| 組態管理 | 外部化組態 (環境變數/組態檔) |

---

## 6. 系統架構

### 6.1 整體架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                         使用者層                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   網頁瀏覽器   │  │  EHR 系統   │  │  CDS Client │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         介面層                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Web Routes │  │  API Routes │  │  CDS Hooks  │              │
│  │  (Flask BP) │  │  (REST API) │  │  Endpoints  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         服務層                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  FHIR Data Service (Facade)               │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ FHIR Client │  │  PRECISE-   │  │  Tradeoff   │              │
│  │   Service   │  │    HBR      │  │   Model     │              │
│  │             │  │ Calculator  │  │ Calculator  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Condition  │  │    Unit     │  │   Config    │              │
│  │   Checker   │  │  Converter  │  │   Loader    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │   TW Core   │  │   Audit     │                               │
│  │   Adapter   │  │   Logger    │                               │
│  └─────────────┘  └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         資料層                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Session   │  │  Audit Log  │  │   Config    │              │
│  │   Storage   │  │   (JSONL)   │  │   Files     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       外部整合層                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ FHIR Server │  │   OAuth     │  │   Google    │              │
│  │  (EHR)      │  │   Server    │  │   Secret    │              │
│  │             │  │             │  │   Manager   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 技術堆疊

| 層級 | 技術 | 版本 |
|------|------|------|
| 前端框架 | Bootstrap | 5.x |
| 前端腳本 | Vanilla JavaScript | ES6+ |
| 圖表函式庫 | Chart.js | 4.x |
| 後端框架 | Flask | 3.0.3 |
| FHIR 客戶端 | fhirclient | 4.1.0 |
| 安全套件 | Flask-Talisman, Flask-WTF | Latest |
| 部署平台 | Google App Engine / Docker | - |

### 6.3 服務元件說明

| 元件 | 職責 | 檔案位置 |
|------|------|----------|
| FHIR Data Service | 統一入口，協調各服務 | `services/fhir_data_service.py` |
| FHIR Client Service | FHIR 伺服器通訊 | `services/fhir_client_service.py` |
| PRECISE-HBR Calculator | 風險評分計算 | `services/precise_hbr_calculator.py` |
| Risk Classifier | 風險等級分類 | `services/risk_classifier.py` |
| Tradeoff Calculator | 權衡分析計算 | `services/tradeoff_model_calculator.py` |
| Condition Checker | 疾病狀態檢測 | `services/condition_checker.py` |
| Unit Converter | 單位換算 | `services/unit_conversion_service.py` |
| Config Loader | 組態載入 | `services/config_loader.py` |
| TW Core Adapter | 台灣在地化 | `services/twcore_adapter.py` |
| Audit Logger | 稽核日誌 | `services/audit_logger.py` |

---

## 7. 整合規範

### 7.1 SMART on FHIR 整合

#### 7.1.1 授權流程

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   EHR    │     │   App    │     │  OAuth   │     │   FHIR   │
│  系統    │     │  應用    │     │  Server  │     │  Server  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │  1. Launch     │                │                │
     │  (ISS + launch)│                │                │
     │───────────────>│                │                │
     │                │                │                │
     │                │ 2. Authorize   │                │
     │                │ (PKCE code_    │                │
     │                │  challenge)    │                │
     │                │───────────────>│                │
     │                │                │                │
     │                │ 3. Callback    │                │
     │                │ (auth_code)    │                │
     │                │<───────────────│                │
     │                │                │                │
     │                │ 4. Token       │                │
     │                │ Exchange       │                │
     │                │───────────────>│                │
     │                │                │                │
     │                │ 5. Access Token│                │
     │                │<───────────────│                │
     │                │                │                │
     │                │ 6. FHIR API    │                │
     │                │ Requests       │                │
     │                │────────────────────────────────>│
     │                │                │                │
     │                │ 7. FHIR Data   │                │
     │                │<────────────────────────────────│
```

#### 7.1.2 支援的 FHIR Scopes

| Scope | 用途 |
|-------|------|
| `launch` | 啟動上下文 |
| `openid` | OpenID Connect |
| `fhirUser` | 使用者識別 |
| `patient/Patient.read` | 患者基本資料 |
| `patient/Observation.read` | 檢驗結果 |
| `patient/Condition.read` | 診斷資料 |
| `patient/MedicationRequest.read` | 用藥資料 |
| `patient/Procedure.read` | 處置記錄 |

### 7.2 CDS Hooks 整合

#### 7.2.1 服務探索

**端點**: `GET /cds-services`

**回應範例**:
```json
{
  "services": [
    {
      "hook": "patient-view",
      "id": "precise_hbr_patient_view",
      "title": "PRECISE-HBR Bleeding Risk Assessment",
      "description": "Calculates bleeding risk for PCI patients",
      "prefetch": {
        "patient": "Patient/{{context.patientId}}",
        "observations": "Observation?patient={{context.patientId}}&category=laboratory",
        "conditions": "Condition?patient={{context.patientId}}&clinical-status=active"
      }
    },
    {
      "hook": "medication-prescribe",
      "id": "precise_hbr_bleeding_risk_alert",
      "title": "High Bleeding Risk Alert",
      "description": "Alerts when prescribing antiplatelet/anticoagulant to high-risk patients"
    }
  ]
}
```

#### 7.2.2 Hook 請求/回應

**請求格式**:
```json
{
  "hookInstance": "uuid",
  "hook": "patient-view",
  "context": {
    "userId": "Practitioner/123",
    "patientId": "Patient/456"
  },
  "prefetch": {
    "patient": { "resourceType": "Patient", ... },
    "observations": { "resourceType": "Bundle", ... }
  }
}
```

**回應格式**:
```json
{
  "cards": [
    {
      "uuid": "card-uuid",
      "summary": "PRECISE-HBR Score: 25 (High Bleeding Risk)",
      "detail": "1-year bleeding risk: 4.75%",
      "indicator": "warning",
      "source": {
        "label": "PRECISE-HBR Calculator"
      }
    }
  ]
}
```

### 7.3 FHIR 資源對應

#### 7.3.1 LOINC 代碼對應

| 參數 | LOINC 代碼 |
|------|-----------|
| 血紅素 | 718-7, 30350-3, 30313-1 |
| eGFR | 33914-3, 62238-1, 88293-6 |
| 肌酸酐 | 2160-0, 38483-4 |
| 白血球 | 6690-2, 26464-8 |

#### 7.3.2 SNOMED CT 代碼對應

| 條件 | SNOMED CT 代碼 |
|------|---------------|
| 既往出血 | 131148009, 74474003, 230690007 |
| 肝硬化 | 19943007 |
| 惡性腫瘤 | 363346000 |
| 血小板減少 | 302215000 |

---

## 8. 安全與合規

### 8.1 認證與授權

#### 8.1.1 OAuth 2.0 + PKCE

| 項目 | 規格 |
|------|------|
| 授權類型 | Authorization Code Grant |
| PKCE 方法 | S256 |
| Token 類型 | Bearer |
| Token 儲存 | 加密 Session |

#### 8.1.2 會話管理

| 項目 | 設定 |
|------|------|
| Cookie 旗標 | HttpOnly, Secure, SameSite=Lax |
| 會話逾時 | 5 分鐘無活動自動登出 |
| 逾時警告 | 逾時前 60 秒顯示警告 |

### 8.2 資料保護

#### 8.2.1 傳輸安全

- TLS 1.2+ 加密所有通訊
- HSTS 標頭強制 HTTPS
- 憑證固定 (Certificate Pinning) 於正式環境

#### 8.2.2 存放安全

- Session 資料以 SECRET_KEY 簽章
- 敏感組態存於 Google Secret Manager
- 稽核日誌防竄改 (雜湊鏈)

### 8.3 輸入驗證

#### 8.3.1 患者 ID 驗證

```python
# 驗證規則
- 允許字元: a-z, A-Z, 0-9, -, _
- 最大長度: 256 字元
- 禁止: SQL 關鍵字、特殊字元
```

#### 8.3.2 URL 驗證

```python
# 驗證規則
- 允許協定: http, https
- 禁止: localhost (正式環境)
- 禁止: 私有 IP 範圍 (RFC 1918)
- 最大長度: 2048 字元
```

### 8.4 安全標頭

| 標頭 | 值 |
|------|----|
| Strict-Transport-Security | max-age=31536000; includeSubDomains |
| Content-Security-Policy | default-src 'self'; script-src 'self' cdn.jsdelivr.net... |
| X-Frame-Options | DENY |
| X-Content-Type-Options | nosniff |
| Cache-Control | no-store, no-cache, must-revalidate |

### 8.5 稽核日誌

#### 8.5.1 日誌格式

```json
{
  "log_type": "EPHI_ACCESS",
  "timestamp": "2026-01-13T15:30:00Z",
  "user_id": "session_abc123",
  "patient_id": "patient_456",
  "action": "calculate_risk_score",
  "resource_type": "Patient,Observation,Condition",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "outcome": "success",
  "previous_hash": "sha256:abc...",
  "entry_hash": "sha256:def..."
}
```

#### 8.5.2 防竄改機制

- 每筆日誌包含前一筆的雜湊值
- 使用 SHA-256 演算法
- 任何竄改將破壞雜湊鏈

### 8.6 法規合規對照

| 法規要求 | 實作方式 | 狀態 |
|----------|----------|------|
| HIPAA 技術防護 | TLS、存取控制、稽核 | ✅ 已實作 |
| ONC (d)(2) 稽核 | 防竄改日誌 | ✅ 已實作 |
| ONC (d)(5) 會話逾時 | 5 分鐘自動登出 | ✅ 已實作 |
| ONC (b)(6) 資料匯出 | C-CDA 產生器 | 🔄 規劃中 |
| ONC (n) 申訴管道 | 問題回報系統 | ✅ 已實作 |

---

## 9. 使用者介面設計

### 9.1 頁面結構

#### 9.1.1 主要頁面

| 頁面 | 路徑 | 說明 |
|------|------|------|
| 風險計算器 | `/main` | 核心功能頁面 |
| 權衡分析 | `/tradeoff_analysis` | 出血/血栓權衡 |
| 文件中心 | `/docs` | 使用說明與文件 |
| 問題回報 | `/report-issue` | 問題回報表單 |
| 獨立啟動 | `/standalone` | 手動輸入啟動 |

#### 9.1.2 頁面佈局

```
┌─────────────────────────────────────────────────┐
│  Header: Logo + 導覽列 + 會話計時器             │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────┐  ┌─────────────────────┐  │
│  │                 │  │                     │  │
│  │   患者資訊卡    │  │    風險評分卡       │  │
│  │                 │  │    (總分+等級)      │  │
│  └─────────────────┘  └─────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │                                           │  │
│  │           評分項目明細表格                 │  │
│  │        (可編輯、即時重算)                  │  │
│  │                                           │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │           HBR 建議區塊                     │  │
│  │        (高風險時顯示)                      │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │           意見回饋區塊                     │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
├─────────────────────────────────────────────────┤
│  Footer: 版本資訊 + 法規聲明                    │
└─────────────────────────────────────────────────┘
```

### 9.2 互動設計

#### 9.2.1 風險計算流程

```
1. 頁面載入
   ↓
2. 自動獲取 FHIR 資料
   ↓
3. 顯示載入動畫
   ↓
4. 渲染患者資訊與評分表格
   ↓
5. 使用者可修改數值
   ↓
6. 即時重新計算 (onChange)
   ↓
7. 更新風險評分顯示
```

#### 9.2.2 數值輸入互動

| 互動類型 | 行為 |
|----------|------|
| 數值輸入 | 即時驗證 + 自動重算 |
| 核取方塊 | 切換後即時重算 |
| 單位切換 | 轉換數值 + 重算 |
| 複製結果 | 一鍵複製至剪貼簿 |

### 9.3 視覺設計規範

#### 9.3.1 色彩系統

| 用途 | 色碼 | 說明 |
|------|------|------|
| 成功/低風險 | #28a745 | 綠色 |
| 警告/中風險 | #fd7e14 | 橘色 |
| 危險/高風險 | #dc3545 | 紅色 |
| 資訊 | #17a2b8 | 藍色 |
| 主色調 | #007bff | Bootstrap Primary |

#### 9.3.2 風險等級視覺化

| 等級 | 分數範圍 | 背景色 | 文字色 |
|------|----------|--------|--------|
| 非高風險 | ≤22 | 綠色 | 白色 |
| 高風險 | 23-26 | 橘色 | 深色 |
| 極高風險 | ≥27 | 紅色 | 白色 |

### 9.4 無障礙設計

| 項目 | 實作 |
|------|------|
| ARIA 標籤 | 所有互動元素 |
| 鍵盤導航 | Tab 順序優化 |
| 色彩對比 | WCAG 2.1 AA 等級 |
| 螢幕閱讀器 | 動態內容 live region |

---

## 10. 資料模型

### 10.1 輸入資料結構

#### 10.1.1 FHIR 資源

```typescript
// Patient 資源 (輸入)
interface PatientInput {
  id: string;
  name: HumanName[];
  birthDate: string;
  gender: 'male' | 'female' | 'other' | 'unknown';
  identifier: Identifier[];
}

// Observation 資源 (檢驗值)
interface ObservationInput {
  code: CodeableConcept;  // LOINC 代碼
  valueQuantity: {
    value: number;
    unit: string;
    system: string;
  };
  effectiveDateTime: string;
}

// Condition 資源 (診斷)
interface ConditionInput {
  code: CodeableConcept;  // ICD-10, SNOMED
  clinicalStatus: CodeableConcept;
  verificationStatus: CodeableConcept;
}
```

### 10.2 輸出資料結構

#### 10.2.1 風險計算結果

```typescript
interface RiskCalculationResult {
  patient_info: {
    patient_id: string;
    name: string;
    age: number;
    gender: string;
  };
  total_score: number;
  risk_level: string;
  recommendation: string;
  score_components: ScoreComponent[];
}

interface ScoreComponent {
  parameter: string;
  value: string | number;
  raw_value: number | null;
  is_present: boolean | null;
  score: number;
  date: string;
  is_outdated: boolean;
  is_arc_hbr_element: boolean;
}
```

#### 10.2.2 權衡分析結果

```typescript
interface TradeoffResult {
  model: {
    bleedingEvents: { predictors: Predictor[] };
    thromboticEvents: { predictors: Predictor[] };
  };
  detected_factors: Record<string, boolean>;
  initial_scores: {
    bleeding_risk: number;
    thrombotic_risk: number;
  };
}
```

### 10.3 組態資料結構

#### 10.3.1 評分參數

```json
{
  "base_score": 2,
  "coefficients": {
    "age": {
      "threshold": 30,
      "coefficient": 0.26,
      "truncation_min": 30,
      "truncation_max": 80
    },
    "hemoglobin": {
      "threshold": 15.0,
      "coefficient": 2.5,
      "truncation_min": 5.0,
      "truncation_max": 15.0
    }
  },
  "binary_scores": {
    "prior_bleeding": 7,
    "oral_anticoagulation": 5,
    "arc_hbr": 3
  }
}
```

### 10.4 儲存結構

#### 10.4.1 Session 資料

```python
session['fhir_data'] = {
    'token': str,           # OAuth access token
    'patient': str,         # Patient ID
    'server': str,          # FHIR server URL
    'client_id': str,       # OAuth client ID
    'expires_in': int,      # Token 有效期 (秒)
    'refresh_token': str    # Refresh token (可選)
}
```

#### 10.4.2 稽核日誌

- 格式: JSONL (每行一筆 JSON)
- 位置: `instance/audit/audit_log.jsonl`
- 特性: 僅附加、雜湊鏈防竄改

---

## 11. API 規格

### 11.1 認證相關 API

#### 11.1.1 啟動應用程式

```
GET /launch?iss={fhir_server_url}&launch={launch_token}
```

| 參數 | 必要 | 說明 |
|------|------|------|
| iss | 是 | FHIR 伺服器 URL |
| launch | 是 | 啟動 Token |

**回應**: 302 重導向至 OAuth 授權端點

#### 11.1.2 Token 交換

```
POST /api/exchange-code
Content-Type: application/json

{
  "code": "authorization_code",
  "state": "state_parameter"
}
```

**成功回應** (200):
```json
{
  "success": true,
  "redirect_url": "/main"
}
```

### 11.2 核心功能 API

#### 11.2.1 計算風險評分

```
POST /api/calculate_risk
Content-Type: application/json
X-CSRFToken: {csrf_token}

{
  "patientId": "patient-123"
}
```

**成功回應** (200):
```json
{
  "patient_info": {
    "patient_id": "patient-123",
    "name": "王小明",
    "age": 65,
    "gender": "male"
  },
  "total_score": 25,
  "risk_level": "High Bleeding Risk (score 23-26)",
  "recommendation": "1-year risk of major bleeding: 4.75%...",
  "score_components": [
    {
      "parameter": "PRECISE-HBR - Age",
      "value": "65 years",
      "raw_value": 65,
      "score": 9,
      "date": "2026-01-13",
      "is_outdated": false
    }
  ]
}
```

**錯誤回應**:
| 狀態碼 | 說明 |
|--------|------|
| 400 | 缺少或無效的患者 ID |
| 401 | 未授權 (Session 過期) |
| 404 | 患者不存在 |
| 429 | 請求過於頻繁 |
| 500 | 伺服器內部錯誤 |
| 503 | FHIR 伺服器無法連線 |

#### 11.2.2 取得評分設定

```
GET /api/config/scoring
```

**成功回應** (200):
```json
{
  "base_score": 2,
  "coefficients": {
    "age": { "threshold": 30, "coefficient": 0.26, ... },
    "hemoglobin": { "threshold": 15.0, "coefficient": 2.5, ... },
    "egfr": { "threshold": 100, "coefficient": 0.05, ... },
    "wbc": { "threshold": 3.0, "coefficient": 0.8, ... }
  },
  "binary_scores": {
    "prior_bleeding": 7,
    "oral_anticoagulation": 5,
    "arc_hbr": 3
  }
}
```

#### 11.2.3 計算權衡分析

```
POST /api/calculate_tradeoff
Content-Type: application/json
X-CSRFToken: {csrf_token}

// 初始載入
{ "patientId": "patient-123" }

// 重新計算
{ "active_factors": { "diabetes": true, "prior_stroke": false, ... } }
```

### 11.3 CDS Hooks API

#### 11.3.1 服務探索

```
GET /cds-services
```

#### 11.3.2 Patient View Hook

```
POST /cds-services/precise_hbr_patient_view
Content-Type: application/json

{
  "hookInstance": "uuid",
  "hook": "patient-view",
  "context": { "patientId": "123" },
  "prefetch": { ... }
}
```

#### 11.3.3 Medication Prescribe Hook

```
POST /cds-services/precise_hbr_bleeding_risk_alert
Content-Type: application/json

{
  "hookInstance": "uuid",
  "hook": "medication-prescribe",
  "context": {
    "patientId": "123",
    "medications": { ... }
  },
  "prefetch": { ... }
}
```

### 11.4 健康檢查 API

```
GET /health
```

**成功回應** (200):
```json
{
  "status": "healthy",
  "timestamp": "2026-01-13T15:30:00.000000",
  "service": "PRECISE-HBR SMART on FHIR",
  "version": "1.0.0"
}
```

---

## 12. 部署與維運

### 12.1 部署架構

#### 12.1.1 Google App Engine

```yaml
# app.yaml
runtime: python311
entrypoint: gunicorn -b :$PORT -t 120 APP:app

instance_class: F2

automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.65

env_variables:
  FLASK_ENV: production
```

#### 12.1.2 Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn", "-b", ":8080", "-t", "120", "APP:app"]
```

### 12.2 環境變數

| 變數名稱 | 必要 | 說明 |
|----------|------|------|
| FLASK_SECRET_KEY | 是 | 應用程式密鑰 (≥32 字元) |
| FLASK_ENV | 是 | production / development |
| SMART_CLIENT_ID | 是 | OAuth 客戶端 ID |
| SMART_CLIENT_SECRET | 否 | OAuth 客戶端密鑰 |
| SMART_REDIRECT_URI | 是 | OAuth 回調 URL |
| GOOGLE_CLOUD_PROJECT | 否 | GCP 專案 ID |

### 12.3 監控與告警

#### 12.3.1 健康檢查

| 項目 | 設定 |
|------|------|
| 端點 | `/health` |
| 間隔 | 30 秒 |
| 逾時 | 4 秒 |
| 失敗閾值 | 3 次 |

#### 12.3.2 告警條件

| 條件 | 閾值 | 動作 |
|------|------|------|
| 錯誤率 | > 1% | 通知 on-call |
| 回應時間 | > 5 秒 | 通知 on-call |
| 實例數 | = 10 (上限) | 評估擴容 |
| 可用性 | < 99% | 緊急處理 |

### 12.4 備份與還原

| 項目 | 策略 |
|------|------|
| 組態檔 | Git 版本控制 |
| 稽核日誌 | 每日歸檔至 Cloud Storage |
| Session | 無狀態設計，無需備份 |

### 12.5 維運程序

#### 12.5.1 版本更新

1. 建立功能分支
2. 完成開發與測試
3. 提交 Pull Request
4. 程式碼審查
5. 合併至主分支
6. 自動部署至 Staging
7. 驗收測試
8. 部署至 Production

#### 12.5.2 緊急修補

1. 建立 hotfix 分支
2. 修復問題
3. 快速審查
4. 直接部署至 Production
5. 回溯合併至 develop

---

## 13. 測試策略

### 13.1 測試層級

| 層級 | 覆蓋率目標 | 工具 |
|------|------------|------|
| 單元測試 | > 80% | pytest |
| 整合測試 | 關鍵路徑 100% | pytest |
| 端對端測試 | 主要流程 | Selenium |
| 效能測試 | 基準線 | Locust |
| 安全測試 | OWASP Top 10 | 手動 + 自動 |

### 13.2 測試案例分類

#### 13.2.1 功能測試

| 測試項目 | 檔案 |
|----------|------|
| 風險計算正確性 | `test_precise_hbr_calculator.py` |
| FHIR 資料擷取 | `test_fhir_client_service.py` |
| 權衡分析 | `test_tradeoff_model.py` |
| CDS Hooks | `test_hooks.py` |

#### 13.2.2 安全測試

| 測試項目 | 檔案 |
|----------|------|
| OAuth 流程 | `test_auth_security.py` |
| SMART 安全 | `test_smart_security.py` |
| 輸入驗證 | `test_input_validation.py` |
| ePHI 保護 | `test_ephi_protection.py` |

### 13.3 驗證標準

#### 13.3.1 演算法驗證

- 使用 Golden Dataset 驗證
- 誤差容忍範圍: ±0.5 分
- 邊界案例 100% 覆蓋

#### 13.3.2 合規驗證

| 要求 | 驗證方式 |
|------|----------|
| SMART on FHIR | Inferno 測試套件 |
| CDS Hooks | Sandbox 驗證 |
| HIPAA | 安全評估報告 |

---

## 14. 風險評估

### 14.1 技術風險

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|--------|------|----------|
| FHIR 伺服器不相容 | 中 | 高 | 多 vendor 測試 |
| 效能瓶頸 | 低 | 中 | 負載測試、快取 |
| 第三方函式庫漏洞 | 中 | 高 | 定期更新、安全掃描 |

### 14.2 業務風險

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|--------|------|----------|
| 用戶採用率低 | 中 | 高 | 教育訓練、易用性優化 |
| 法規變更 | 低 | 高 | 持續監控法規動態 |
| 競品威脅 | 中 | 中 | 功能差異化 |

### 14.3 臨床風險

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|--------|------|----------|
| 演算法錯誤 | 低 | 極高 | 嚴格驗證、免責聲明 |
| 資料品質不佳 | 中 | 高 | 資料驗證、缺失警告 |
| 過度依賴系統 | 中 | 中 | 使用者教育 |

### 14.4 風險矩陣

```
        │ 低影響 │ 中影響 │ 高影響 │ 極高影響
────────┼────────┼────────┼────────┼──────────
高可能性│        │        │        │
中可能性│        │ 競品   │ 採用率 │
低可能性│        │ 效能   │ 法規   │ 演算法
```

---

## 15. 附錄

### 15.1 術語表

| 術語 | 說明 |
|------|------|
| PCI | 經皮冠狀動脈介入治療 (Percutaneous Coronary Intervention) |
| DAPT | 雙重抗血小板治療 (Dual Antiplatelet Therapy) |
| HBR | 高出血風險 (High Bleeding Risk) |
| ARC-HBR | Academic Research Consortium 高出血風險標準 |
| BARC | Bleeding Academic Research Consortium |
| FHIR | Fast Healthcare Interoperability Resources |
| SMART | Substitutable Medical Applications and Reusable Technologies |
| CDS | Clinical Decision Support |
| ePHI | 電子受保護健康資訊 |
| ONC | Office of the National Coordinator for Health IT |

### 15.2 參考文獻

1. Costa F, et al. Derivation and validation of the predicting bleeding complications in patients undergoing stent implantation and subsequent dual antiplatelet therapy (PRECISE-DAPT) score. Lancet. 2017.

2. Urban P, et al. Defining High Bleeding Risk in Patients Undergoing Percutaneous Coronary Intervention. Circulation. 2019.

3. HL7 FHIR R4 Specification. https://hl7.org/fhir/R4/

4. SMART App Launch Framework. https://hl7.org/fhir/smart-app-launch/

5. CDS Hooks Specification. https://cds-hooks.org/

### 15.3 版本歷程

| 版本 | 日期 | 變更說明 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-01-13 | 初版發布 | 產品團隊 |

### 15.4 審核紀錄

| 審核者 | 角色 | 日期 | 狀態 |
|--------|------|------|------|
| | 產品負責人 | | 待審核 |
| | 技術主管 | | 待審核 |
| | 臨床顧問 | | 待審核 |
| | 法規專員 | | 待審核 |

---

**文件結束**

*本文件為 PRECISE-HBR SMART on FHIR 應用程式的產品需求規格書，供產品規劃、開發實作及品質驗證參考使用。*
