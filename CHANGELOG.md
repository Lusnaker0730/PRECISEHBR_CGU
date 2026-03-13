# Changelog — PRECISE-HBR SMART on FHIR Application

本文件記錄 PRECISE-HBR SMART on FHIR 應用程式的所有重大變更。
格式依據 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，版本號遵循 [Semantic Versioning](https://semver.org/)。

---

## [Unreleased]

### CI/CD 基礎建設 (Infrastructure)
- **新增 `clinical-validation.yml` CI 工作流程** — 當 `config/cdss_config.json` 或計算核心（`precise_hbr_calculator.py`、`risk_classifier.py`、`condition_checker.py`、`unit_conversion_service.py`）被修改時，自動觸發 Golden Dataset 驗證（`verify_precise_hbr.py`）+ 風險分類測試 + 設定完整性測試。報告保留 2555 天（TFDA 合規）。設為 GitHub branch protection required check 即可強制 Class C 變更必須通過驗證
- **新增 `regulatory-compliance.yml` CI 工作流程** — PR 時自動檢查所有測試是否具備 IEC 62304 法規追溯標記（`@pytest.mark.requirement`/`@pytest.mark.risk`/`@pytest.mark.design`），缺少標記的測試將導致 CI 失敗。產出追溯覆蓋率報告並上傳至 GitHub Step Summary
- **增強 `regulatory_plugin.py`** — 新增 `--enforce-regulatory-markers` CLI 選項，啟用時若有測試缺少法規標記則 session exit code 設為 1，並輸出詳細的未追溯測試清單與覆蓋率統計
- **修正 `test.yml` paths filter** — 加入 `config/**`，確保臨床參數變更也會觸發測試套件
- **更新 PR 範本** — Class C 變更提醒區段，列出會觸發 Golden Dataset 驗證的檔案清單

### 安全性 (Security)
- **ePHI 日誌過濾器重構為嚴格白名單模式** — 完全取代舊版黑名單方式：
  - **FHIR Resource 偵測器**：任何含 `resourceType`、`subject`、`identifier`、`telecom` 等 FHIR 結構鍵的 dict 整包遮蔽，防禦 FHIR 規格更新引入新 ePHI 欄位
  - **Dict Key 白名單**：僅允許 `SAFE_DICT_KEYS` 中的系統除錯鍵通過，未知鍵一律 `[REDACTED]`
  - **台灣 ePHI 格式支援**：台灣身分證號（A123456789）、居留證號、NHI 藥品代碼、台灣電話、中文姓名
  - **JSON Blob 深層清洗**：字串中嵌入的 FHIR JSON（含 `resourceType`）自動偵測並遮蔽
  - **52 項新增測試**（`tests/test_ephi_allowlist_filter.py`）：6 層防禦逐層驗證
- **修復深層 BOLA 越權存取漏洞** — 兩項關鍵修復：
  - `tradeoff_routes.py` `/api/calculate_tradeoff` 端點新增 `validate_patient_context()` 檢查，防止攻擊者在 payload 中替換 patientId 查詢他人資料
  - `fhir_client_service.py` 新增 FHIR 回傳資源 Ownership 驗證（`_validate_resource_ownership` / `_filter_owned_resources`），檢查每筆 Observation/Condition 的 `subject.reference` 是否指向授權病患，防禦 FHIR Server 異常或中間人攻擊
- **新增 17 項深層 BOLA 測試** (`tests/test_bola_deep.py` PT-062~PT-075)：Tradeoff 端點越權拒絕/接受、FHIR 資源 Ownership 驗證、混合 ownership 過濾、整合測試
- **修復 ConfigLoader singleton thread safety** — `config_loader.py` 加入 `threading.Lock` double-checked locking，防止 Gunicorn gthread worker 下的 race condition（半初始化實例、重複 `_load_config`）
- **新增 7 項 ConfigLoader 執行緒安全測試** (`tests/test_config_loader_thread_safety.py` PT-076~PT-078)：10 執行緒並行建立 singleton、`_load_config` 僅執行一次、並行讀取一致性、無半初始化實例
- **修復 token exchange 資訊洩露漏洞** — `auth_routes.py:458` 移除 `"details": e.response.text`，防止後端錯誤訊息（DB 連線字串、密鑰等）洩露給客戶端
- **新增 61 項自動化滲透測試** (`tests/test_penetration.py`)，涵蓋 15 個攻擊類別：
  - PT-001: CDS Hooks 惡意 Payload 注入（巨量 payload、深層巢狀 JSON、XSS、SQL 注入、Null byte）
  - PT-002: CDS Hooks CORS 安全驗證
  - PT-003: Session 安全（fixation、hijacking、tampering）
  - PT-004: BOLA/IDOR 病人資料越權存取
  - PT-005: OAuth2/PKCE 認證繞過（state 篡改、PKCE 過期、refresh 濫用）
  - PT-006: 注入攻擊（XSS、SSTI、CRLF、Host Header Injection）
  - PT-007: SSRF 防護（私有 IP、雲端 metadata、DNS rebinding）
  - PT-008: 資訊洩露（堆疊追蹤、token、內部錯誤、health endpoint）
  - PT-009: HTTP Method Tampering
  - PT-010: Patient ID 格式驗證與注入防護
  - PT-011: Security Headers 完整性（CSP、HSTS、X-Frame-Options 等）
  - PT-012: Tradeoff 端點安全
  - PT-013: Complaint Form 濫用防護（CAPTCHA 繞過、replay）
  - PT-014: Logout Session 清除驗證
  - PT-015: Token Exchange 資訊洩露回歸測試

### 重構 (Refactoring)
- **Legacy Facade 退場機制（Phase 1）** — `fhir_data_service.py` 正式標記為 Deprecated：
  - 所有 facade wrapper 函式加入 `warnings.warn(DeprecationWarning)`，含遷移指引
  - 4 個含獨有邏輯的函式遷移至 canonical service：
    - `get_patient_demographics` → `twcore_adapter.get_patient_demographics()`
    - `check_arc_hbr_factors` → `condition_checker.check_arc_hbr_factors_summary()`
    - `get_active_medications` → `condition_checker.get_active_medications()`
    - `get_score_from_table` → `risk_classifier.get_score_from_table()`
  - `check_medication_interactions_bleeding_risk` → `condition_checker.check_medication_interactions_bleeding_risk()`
  - Facade 模組 docstring 包含完整遷移對照表
- **新增 22 項 Facade 退場測試** (`tests/test_facade_deprecation.py`)：16 項 DeprecationWarning 觸發驗證 + 6 項 facade/canonical 輸出一致性驗證

### 法規合規 (Regulatory Compliance)
- **新增法規文件自動化生成規範至 `CLAUDE.md`**，記錄 TFDA SaMD 認證相關開發規範
- **所有測試加入 IEC 62304 法規追溯標記**：`@pytest.mark.requirement`、`@pytest.mark.risk`、`@pytest.mark.design`
- **新增法規腳本工具**：
  - `scripts/create_regulatory_issues.py` — 批次建立 SRS/SDS/RISK/TC GitHub Issues
  - `scripts/add_pytest_markers.py` — 自動為測試加入法規標記
- **更新 test-traceability 報告與 regulatory-issue-mapping**

### 功能改進 (Features)
- **Unit Conversion Fail-Safe — 未知/缺失單位拒絕猜測機制** — 當 EHR 回傳的檢驗值單位無法辨認（如 `mg/L` 代替 `g/dL`）或完全缺失時：
  - **後端**：`UnitConversionService.get_value_with_status()` 新增 5 種狀態碼（`ok`/`no_data`/`no_value`/`missing_unit`/`unknown_unit`），區分「FHIR 無資料」vs「有資料但單位無法轉換」
  - **Calculator**：`extract_inputs()` 追蹤 `unit_issues[]`，`_check_unit_issue_warnings()` 產生 `unrecognized_unit` 類型警告（severity=high），明確告知醫師原始值、未知單位、預期單位
  - **前端**：`main.html` 新增 `#unit-warning` alert-danger 區塊，`main.js` 新增 `displayUnitWarnings()` 函式
  - **安全策略**：系統**拒絕猜測單位**，將該參數排除於計分之外（score=0），並在 UI 標示「Not available」+ 明確原因
  - **30 項新增測試**（`tests/test_unit_failsafe.py`）：狀態碼驗證、追蹤機制、警告產生、邊界案例、向下相容
  - 依 ISO 14971 RISK-001 設計：猜錯單位可能造成 10 倍量級誤差，直接影響風險分類
- **Data Quality Warning — 數值截斷警告機制** — 當 EHR 傳入的檢驗值超出臨床預期範圍（如血紅素因單位錯誤被放大 10 倍），系統不再默默截斷，而是：
  - **後端**：`PreciseHBRCalculator._check_truncation_warnings()` 偵測 Age/Hb/eGFR/WBC 四項參數的截斷情況，產生結構化警告（含原始值、截斷值、方向、預期範圍、建議訊息）
  - **元件顯示**：截斷的參數在 component display 中顯示 `(capped to X)`，並附帶 `is_truncated` / `effective_value` 標記
  - **前端**：`main.html` 新增 `#truncation-warning` alert-danger 區塊，`main.js` 新增 `displayTruncationWarnings()` 函式，明確警告醫師「該數值異常，系統已採用截斷值計算」
  - **19 項新增測試**（`tests/test_truncation_warnings.py`）：截斷偵測、邊界值、元件顯示、警告訊息品質
  - 依 ISO 14971 RISK-001（Score Calculation Integrity）設計，防止默默截斷導致醫療誤判
- `condition_checker.py` 臨床狀態偵測邏輯更新
- `precise_hbr_calculator.py` 計算邏輯改進
- `cdss_config.json` 臨床參數更新

---

## [1.0.0] — 2026-03-12

### 安全性 (Security)
- **修復 30 項滲透測試漏洞** (C-01 ~ M-14)：
  - C-01: id_token 簽章驗證 fail-closed 策略（拒絕 HS256/none 演算法）
  - C-03: CDS Hooks JSON 解析安全化（`silent=True`）
  - C-04: BOLA 防護 — `validate_patient_context()` 立即驗證 patient_id
  - C-05: Refresh token 速率限制（5 次/小時）+ 最小間隔 30 秒
  - C-07: API 錯誤回應移除內部細節
  - H-01: PKCE 參數 600 秒過期限制
  - H-02: Token URL SSRF 驗證（session 中的 token_url 也驗證）
  - H-03: SMART 配置回應大小限制（1MB）
  - M-03: Session cookie HTTPONLY + SECURE 標記
  - M-04: 稽核日誌檔案權限 0o600
  - M-06: Session fingerprint（IP + User-Agent SHA256）
  - M-07: X-Content-Type-Options: nosniff
  - M-08: 投訴表單輸入消毒（`markupsafe.escape`）
  - M-12: 投訴檔案路徑穿越防護（`os.path.abspath` 驗證）
  - M-13: 投訴表單速率限制（5 次/小時）
- SSRF 防護：DNS 解析 + 私有 IP 封鎖 + 雲端 metadata 封鎖
- CSP nonce-based 腳本安全策略（移除 `unsafe-inline`）
- Flask-Talisman HSTS（1 年 + includeSubDomains）
- Flask-Limiter API 速率限制（10 次/分鐘）
- CSRF 保護（全域啟用，CDS Hooks 依規範豁免）
- ePHI 日誌過濾器 — 防止病人健康資料出現在應用程式日誌

### 功能 (Features)
- **PRECISE-HBR 出血風險分數計算**
  - Config-driven 計算（係數/閾值/截斷來自 `cdss_config.json`）
  - 風險分類：Non-HBR (≤22) / HBR (23-26) / Very-HBR (≥27)
  - 出血-血栓權衡分析（ARC-HBR 模型）
- **SMART on FHIR OAuth2 + PKCE 認證**
  - 支援 Epic / Cerner EHR 系統
  - OIDC id_token 簽章驗證（RS256/ES256）
  - Token 刷新 + 旋轉
- **FHIR R4 資料擷取**
  - Patient / Observation / Condition / MedicationRequest
  - LOINC 代碼驅動的實驗室值查詢
  - 安全標籤檢查（restricted/very-restricted）
- **CDS Hooks v1.2 整合**
  - medication-prescribe Hook — 偵測 DAPT/抗凝藥
  - patient-view Hook — 病歷開啟時顯示 HBR 分數
- **台灣核心實作指引 (TW Core IG) 支援**
  - 中文姓名擷取、台灣身分證號、NHI 藥品代碼
  - ICD-10-CM 診斷代碼回退
- **實驗室值單位自動轉換**
  - Hb: g/L, mmol/L → g/dL
  - Creatinine: µmol/L → mg/dL
  - CKD-EPI 2021 無種族 eGFR 公式
- **ePHI 稽核日誌** — SHA-256 雜湊鏈、防竄改、ONC 45 CFR 170.315(d)(2) 合規
- **FHIR Consent 同意管理** — 查詢/檢查/過濾/優雅降級
- **投訴/問題回報表單** — CAPTCHA 防護、路徑穿越防護

### 測試 (Testing)
- 300+ 既有安全測試（OWASP Top 10 全覆蓋）
- 61 項滲透測試
- Golden dataset 驗證（`verify_precise_hbr.py`）
- 邊界值分析測試
- 單元測試覆蓋所有核心服務

### 基礎建設 (Infrastructure)
- GitHub Actions CI/CD（ci.yml, test.yml, security-scan.yml, cd.yml, docker-build.yml）
- `regulatory-artifacts.yml` — TFDA 法規產出物自動生成（7 年保留）
- Google App Engine + Docker 部署支援
- PR 範本含 IEC 62304 法規追溯區段

---

## [0.x] — 2025-05-25 ~ 2025-12-20（早期開發）

### 里程碑
- **2025-05-25**: 初版 — SMART 認證、CDS Hooks、UI 風險計算整合
- **2025-06-11**: 第一個穩定版本
- **2025-09-08**: CSP 修正、CSRF 保護
- **2025-10-28**: CI/CD pipeline、Docker 支援
- **2025-11-10**: Config-driven 架構重構（LOINC/SNOMED/NHI 統一至 cdss_config.json）
- **2025-11-20**: 微服務架構重構、TW Core IG 整合
- **2025-11-28**: 完整測試套件（161+ 測試）
- **2025-12-16**: PRECISE-HBR 計算器服務、驗證資產
- **2026-01-01**: UI 重構、FHIR 服務 facade
- **2026-01-13**: XSS 修復、記憶體洩漏修復、未使用模板清理

---

_此 Changelog 由 PRECISE-HBR 開發團隊維護，符合 TFDA 醫療器材軟體變更歷史要求（IEC 62304 §5.8.4）。_
