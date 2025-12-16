# PRECISE-HBR SMART on FHIR 應用程式說明文件

## 1. 簡介 (Introduction)

**PRECISE-HBR SMART on FHIR** 是一款專為心導管介入治療（PCI）後病患設計的臨床決策輔助系統（CDSS）。本系統基於 HL7 FHIR R4 標準開發，旨在協助臨床醫師評估病患的雙重抗血小板治療（DAPT）後的出血風險，並提供出血與血栓風險的權衡分析（Trade-off Analysis）。

本系統已通過 **SMART Health IT 沙盒** 與 **Oracle Cerner** 開發者沙盒驗證，並針對台灣醫療環境進行在地化適配（TW Core IG），具備高度的互操作性與合規性。

---

## 2. 系統架構 (System Architecture)

本應用程式採用微服務架構設計，確保模組的獨立性與可擴充性。

### 2.1 技術堆疊 (Tech Stack)
*   **後端框架**: Python Flask
*   **前端技術**: Jinja2 Templates, Bootstrap 5, JavaScript
*   **資料標準**: HL7 FHIR R4, SMART on FHIR (OAuth 2.0 / OIDC)
*   **部署環境**: Google App Engine (Standard Environment) / Docker
*   **安全機制**: Google Secret Manager, CSRF Protection, Content Security Policy (CSP)

### 2.2 核心模組 (Core Modules)
系統將功能拆解為以下獨立服務模組（位於 `services/` 目錄）：
*   **fhir_client_service.py**: 負責與外部 FHIR Server 進行 OAuth 2.0 認證與資料交換。
*   **precise_hbr_calculator.py**: 執行 PRECISE-HBR 風險評分運算核心。
*   **tradeoff_model_calculator.py**: 執行出血與血栓風險權衡分析模型。
*   **twcore_adapter.py**: 台灣核心實作指引（TW Core IG）適配器，處理在地化資料格式。
*   **risk_classifier.py**: 負責將數值分數轉換為風險類別（如 Very High, High, Moderate, Low）。
*   **condition_checker.py**: 臨床條件判讀引擎（如識別活動性癌症、肝硬化等）。

---

## 3. 核心功能說明 (Core Features)

### 3.1 PRECISE-HBR 出血風險計算
系統自動從電子病歷（EHR）中提取以下 5 項關鍵指標進行運算：
1.  **年齡 (Age)**: 自動計算有效年齡分數。
2.  **腎功能 (eGFR)**: 優先使用檢驗值，若無則依據肌酸酐（Creatinine）、年齡、性別自動推算。
3.  **血紅素 (Hemoglobin)**: 評估貧血狀況。
4.  **白血球計數 (WBC)**: 發炎指標評估。
5.  **出血病史 (Prior Bleeding)**: 透過 ICD-10 與 SNOMED CT 代碼自動識別過往出血紀錄。

計算結果將病患分為四個風險等級，並提供具體的臨床建議（如 DAPT 持續時間建議）。

### 3.2 出血與血栓權衡分析 (Trade-off Analysis)
系統不僅評估出血風險，還引入了 ARC-HBR 定義的權衡模型，同時計算：
*   **出血風險 (Bleeding Risk)**: 預測 BARC 3 或 5 型出血機率。
*   **血栓風險 (Thrombotic Risk)**: 預測心肌梗塞或支架內血栓機率。

透過互動式圖表，醫師可直觀比較不同治療策略下的風險消長，輔助精準醫療決策。

### 3.3 CDS Hooks 臨床決策支援
系統實作了 CDS Hooks 1.0 規範，支援以下 Hooks：
*   **patient-view**: 當醫師開啟病患病歷時，自動在背景計算風險，若為高風險病患（Score ≥ 25）主動推送警示卡片。
*   **medication-prescribe**: 當醫師開立抗凝血或抗血小板藥物時，即時檢查藥物交互作用與出血風險，攔截潛在的不當用藥。

### 3.4 台灣在地化支援 (TW Core Integration)
內建智慧型 `TWCoreAdapter`，具備「動態適配機制」：
*   **中文姓名解析**: 自動識別 `Patient.name.text` 中的中文姓名。
*   **身分證驗證**: 支援台灣身分證字號（`http://www.moi.gov.tw/`）與居留證號驗證。
*   **健保藥碼支援**: 可解析台灣健保藥品代碼（NHI Codes），並將其對應至國際標準藥理分類。
*   **ICD-10-CM 支援**: 優先處理台灣臨床慣用的 ICD-10-CM 診斷碼。

---

## 4. 法規遵循與安全性 (Compliance & Security)

### 4.1 美國 ONC Health IT 認證支援
*   **資料匯出 (b)(6)**: 內建 `CCDGenerator`，可將風險評估結果與病患摘要匯出為標準 C-CDA XML 文件。
*   **自動登出 (d)(5)**: 實作閒置逾時自動登出機制。
*   **審計日誌**: 完整記錄 ePHI 存取與使用者操作（登入、計算、匯出），符合 ASTM 標準。
*   **客訴處理 (n)**: 提供標準化的問題回報介面與後端處理流程。

### 4.2 HIPAA 合規性
*   **ePHI 保護**: 資料傳輸強制 TLS 1.2+ 加密，資料庫（Session）採加密儲存。
*   **日誌脫敏**: 實作 `logging_filter.py`，確保應用程式日誌中不包含任何病患個資。

---

## 5. API 技術規格 (API Specifications)

### 5.1 主要端點
| HTTP Method | Endpoint | 描述 |
|-------------|----------|------|
| `GET` | `/launch` | SMART App Launch 入口點 |
| `POST` | `/api/calculate_risk` | 觸發 PRECISE-HBR 風險計算 (需 Auth) |
| `POST` | `/api/export-ccd` | 匯出 C-CDA 文件 (需 Auth) |
| `POST` | `/cds-services/precise_hbr_patient_view` | CDS Hooks: 病患檢視觸發點 |
| `GET` | `/cds-services` | CDS Hooks 服務發現 (Discovery) |

### 5.2 認證授權
採用 **OAuth 2.0 Authorization Code Grant** 流程。
*   **Scopes**: `launch`, `openid`, `fhirUser`, `patient/Patient.read`, `patient/Observation.read`, `patient/Condition.read`, `patient/MedicationRequest.read`。

---

本文件最後更新於: 2025-12-03
版權所有 © 2025 PRECISE-HBR Team

