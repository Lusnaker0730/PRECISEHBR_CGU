# PRECISE-HBR SMART on FHIR 應用程式滲透測試報告

**測試日期**: 2026-03-12
**測試範圍**: 完整原始碼安全審查（白箱測試）
**測試對象**: PRECISE-HBR SMART on FHIR 臨床決策支援系統
**測試方法**: OWASP Top 10、HIPAA 合規性、FHIR 安全最佳實踐

---

## 摘要

本次安全評估針對 PRECISE-HBR SMART on FHIR 應用程式進行了全面的原始碼審查，涵蓋認證授權、輸入驗證、API 安全、FHIR 資料處理、前端安全及部署配置。

### 風險統計

| 嚴重程度 | 數量 |
|---------|------|
| 嚴重 (Critical) | 7 |
| 高風險 (High) | 9 |
| 中風險 (Medium) | 14 |
| 低風險 (Low) | 10 |
| **合計** | **40** |

### 正面發現

應用程式具備多項優秀的安全實作：PKCE OAuth2 流程、SSRF 防護（DNS 解析驗證）、OIDC Token 驗證（拒絕 `none` 和 `HS256` 演算法）、BOLA 防護裝飾器、ePHI 日誌過濾器、CSRF 保護、速率限制、CSP Nonce 機制、稽核日誌雜湊鏈。

---

## 一、嚴重風險 (Critical)

### C-01：OIDC 驗證失敗後仍允許認證通過

- **檔案**: `routes/auth_routes.py`（約第 351-355 行）
- **類型**: 認證繞過 (Authentication Bypass)
- **OWASP**: A07:2021 - 認證與身份驗證失敗

**說明**: 當 `id_token` 驗證失敗時，系統僅記錄警告並繼續以 `access_token` 進行認證，而非拒絕請求。攻擊者可偽造 `id_token` 並利用不同的 issuer 繞過 OIDC 安全檢查。

```python
if validation_error:
    current_app.logger.warning(
        f"id_token validation failed: {validation_error}. "
        "Continuing with access_token only."  # 驗證失敗卻繼續執行！
    )
```

**建議修復**:
- 採用「失敗即拒絕」(fail-closed) 策略
- 如 issuer 不匹配為預期行為，應透過明確的環境配置旗標處理
- 拒絕無法驗證的 Token

---

### C-02：Consent 服務預設允許所有敏感資源存取

- **檔案**: `services/consent_service.py`（第 182-192 行）
- **類型**: 授權缺陷 (Broken Authorization)
- **OWASP**: A01:2021 - 存取控制失效

**說明**: 當 SMART Client 未配置時，系統預設允許存取所有敏感資源（Observation、Condition、MedicationRequest 等），違反「預設拒絕」原則。

```python
def _default_permit_result(self) -> ConsentResult:
    return ConsentResult(
        status=ConsentStatus.ACTIVE,
        has_active_consent=True,
        permitted_resources=list(CONSENT_SENSITIVE_RESOURCES),  # 全部允許！
        denied_resources=[],
        ...
    )
```

**建議修復**:
- 預設設為 DENY，`denied_resources=list(CONSENT_SENSITIVE_RESOURCES)`
- 或回傳 `ConsentStatus.INACTIVE` 結果

---

### C-03：CDS Hooks JSON 解析漏洞

- **檔案**: `routes/hooks.py`（第 210、287 行）
- **類型**: 異常處理不當
- **OWASP**: A05:2021 - 安全設定錯誤

**說明**: CDS Hooks 端點使用 `request.get_json()` 未加入 `silent=True` 參數，惡意 JSON 可導致未處理的異常，暴露內部堆疊追蹤資訊。

```python
hook_request = request.get_json()  # 無錯誤處理
```

**建議修復**:
- 使用 `request.get_json(silent=True)` 或加入 try-except 區塊
- 確保錯誤回應不包含內部細節

---

### C-04：IDOR/BOLA 裝飾器順序問題

- **檔案**: `routes/api_routes.py`（第 21 行）
- **類型**: 不安全的直接物件參考 (IDOR)
- **OWASP**: A01:2021 - 存取控制失效

**說明**: `@require_patient_context` 裝飾器在 patient_id 已從請求主體提取之後才執行驗證。若存在競爭條件或異常處理路徑，資料可能在驗證前被處理。

```python
@api_bp.route('/api/calculate_risk', methods=['POST'])
@login_required
@require_patient_context  # 在資料提取之後才執行！
@limiter.limit("10 per minute")
def calculate_risk_api():
    data = request.get_json()
    patient_id = data.get('patientId')  # 驗證前已提取
```

**建議修復**:
- 將 `@require_patient_context` 移至裝飾器堆疊最內層
- 或在提取 patient_id 後立即進行驗證

---

### C-05：Refresh Token 缺乏充分驗證

- **檔案**: `routes/auth_routes.py`（第 455-598 行）
- **類型**: 認證缺陷
- **OWASP**: A07:2021 - 認證與身份驗證失敗

**說明**: `/api/refresh-token` 端點從 session 取得 refresh token，但未驗證其使用時間、使用頻率，也未檢查 token 是否被重複使用。且該端點缺少速率限制。

**建議修復**:
- 加入速率限制：`@limiter.limit("5 per hour")`
- 追蹤 refresh token 使用時間戳
- 實作 refresh token 過期策略

---

### C-06：稽核日誌在唯讀檔案系統上靜默失敗

- **檔案**: `services/audit_logger.py`（第 96-97、231-235 行）
- **類型**: 合規性風險
- **法規**: 45 CFR 170.315(d)(2) 要求防竄改稽核日誌

**說明**: 在 Google App Engine（唯讀 /tmp）環境中，當稽核檔案無法寫入時，系統僅記錄警告但繼續運作。關鍵合規事件可能靜默遺失。

```python
except OSError as e:
    logger.warning(f"Could not initialize audit log file: {e}. "
                   "Continuing without file-based audit logging.")  # 靜默失敗！
```

**建議修復**:
- GAE 環境改用 Cloud Logging API 或 Datastore
- 初始化失敗時拋出異常，而非繼續執行

---

### C-07：錯誤訊息洩露 FHIR 伺服器內部資訊

- **檔案**: `services/fhir_client_service.py`（第 124-137 行）、`routes/api_routes.py`（第 48-70 行）
- **類型**: 資訊洩露 (Information Disclosure)
- **OWASP**: A05:2021 - 安全設定錯誤

**說明**: 異常詳細資訊直接回傳給使用者，可能洩露內部系統架構、伺服器版本等敏感資訊。

```python
'details': str(error)  # 包含完整錯誤訊息
```

**建議修復**:
- 僅在伺服器端日誌記錄完整錯誤
- 回傳通用錯誤訊息給客戶端

---

## 二、高風險 (High)

### H-01：PKCE 參數無過期時間限制

- **檔案**: `routes/auth_routes.py`（第 196-228 行）
- **類型**: 認證缺陷

**說明**: PKCE 參數（code_verifier、state）儲存在 session 中但無過期時間戳。攻擊者可重播舊的 PKCE 挑戰，或在數小時/數天後使用擷取的 session 資料。

**建議修復**: 加入時間戳驗證，限制 PKCE 交換必須在 10 分鐘內完成。

---

### H-02：SSRF 驗證競爭條件

- **檔案**: `routes/auth_routes.py`（第 203、421-425 行）
- **類型**: 伺服器端請求偽造 (SSRF)
- **OWASP**: A10:2021 - SSRF

**說明**: `token_url` 在儲存至 session 後才進行驗證。若 session 資料在儲存與驗證之間被修改，驗證可能被繞過。

**建議修復**: 在發現 token_url 後立即驗證，通過後才存入 session。

---

### H-03：FHIR 伺服器中繼資料回應缺乏大小限制

- **檔案**: `routes/auth_routes.py`（第 114、124 行）
- **類型**: 阻斷服務 (DoS)

**說明**: 中繼資料取得請求雖有超時設定（10 秒），但未限制回應大小。惡意伺服器可回傳超大 JSON，導致記憶體耗盡。

**建議修復**: 加入回應大小限制（如 1MB）。

---

### H-04：稽核日誌雜湊鏈 TOCTOU 競爭條件

- **檔案**: `services/audit_logger.py`（第 74、206 行）
- **類型**: 競爭條件 (Race Condition)

**說明**: `_get_last_hash()` 未在鎖內呼叫，兩個執行緒可能同時讀取相同的 `_last_hash`，導致雜湊鏈斷裂，影響防竄改檢測。

**建議修復**: 將雜湊鏈狀態讀取移至鎖的上下文內。

---

### H-05：ePHI 日誌過濾器接受無系統標示的程式碼

- **檔案**: `utils/logging_filter.py`（第 139 行）
- **類型**: ePHI 保護缺陷

**說明**: 安全標籤過濾邏輯 `if system in all_systems or not system` 會接受沒有 system URI 的程式碼作為機密性代碼，可能產生誤判。

**建議修復**: 要求 `system` 必須為已知機密性代碼系統之一。

---

### H-06：醫療狀況關鍵字子字串匹配不精確

- **檔案**: `services/condition_checker.py`（第 143-144 行）
- **類型**: 臨床數據品質

**說明**: 文字關鍵字匹配使用子字串比對，可能導致誤判。例如 "bleeding heart disorder" 會匹配 "bleeding" 關鍵字。

```python
if keyword.lower() in condition_text:  # 子字串匹配！
```

**建議修復**: 使用字詞邊界匹配 `\b{keyword}\b` 或要求完全片語匹配。

---

### H-07：FHIR 搜尋參數缺乏 LOINC 代碼驗證

- **檔案**: `services/fhir_client_service.py`（第 171-174 行）
- **類型**: 輸入驗證不足
- **OWASP**: A03:2021 - 注入攻擊

**說明**: `get_observations_by_loinc()` 方法接受 LOINC 代碼清單但未呼叫 `validate_loinc_code()` 進行驗證即構建 FHIR 搜尋參數。

**建議修復**: 在構建搜尋參數前驗證所有 LOINC 代碼。

---

### H-08：CSP 允許 unsafe-inline 樣式

- **檔案**: `APP.py`（第 57 行）
- **類型**: XSS 防護弱化
- **OWASP**: A03:2021 - 注入攻擊

**說明**: CSP 的 `style-src` 包含 `'unsafe-inline'`，顯著削弱了內容安全策略對 XSS 攻擊的防護能力。

**建議修復**: 將所有行內樣式移至外部 CSS 檔案，移除 `'unsafe-inline'`。

---

### H-09：藥物資料擷取不完整

- **檔案**: `services/condition_checker.py`（第 56-90 行）
- **類型**: 資料完整性

**說明**: 僅擷取 `medicationCodeableConcept`，忽略 FHIR MedicationRequest 中的 `medicationReference`（外部 Medication 資源參考），導致藥物匹配失敗。

**建議修復**: 同時檢查 `medicationReference` 並解析參考資源。

---

## 三、中風險 (Medium)

### M-01：Patient Context 驗證可被繞過

- **檔案**: `utils/patient_context.py`（第 161-164 行）
- **說明**: 請求中不包含 `patient_id` 時，`@require_patient_context` 裝飾器允許請求通過，可能存取非預期資料。
- **建議**: 預設要求 patient_id，明確標註允許省略的端點。

### M-02：CDS Hooks CORS 過度寬鬆

- **檔案**: `routes/hooks.py`（第 22-27 行）、`APP.py`（第 88-95 行）
- **說明**: 雖 CDS Hooks 規範要求 CORS 支援，但 `origins="*"` 仍有風險。
- **建議**: 考慮限制為已知沙箱來源。

### M-03：開發模式 Session Cookie 不安全

- **檔案**: `services/app_config.py`（第 116 行）
- **說明**: 非 GAE 環境中 `SESSION_COOKIE_SECURE = False`，若在無 `GAE_ENV` 的生產伺服器運行，session 將透過 HTTP 傳輸。
- **建議**: 預設為安全，僅在明確開發模式旗標下停用。

### M-04：稽核日誌檔案權限未明確設定

- **檔案**: `services/audit_logger.py`（第 65、92-93 行）
- **說明**: 稽核日誌目錄和檔案以預設權限建立，在 Linux 系統上可能為全域可讀，包含 ePHI 的稽核日誌不應如此。
- **建議**: 使用 `os.makedirs(dir, mode=0o700)` 和 `os.chmod(file, 0o600)`。

### M-05：MFA 未知狀態允許存取

- **檔案**: `utils/mfa_validator.py`（第 172-179 行）
- **說明**: 若 FHIR 伺服器未在 id_token 提供 `amr` 聲明，MFA 保護變為可選。
- **建議**: 對需要 MFA 的操作採用嚴格模式，狀態未知時拒絕存取。

### M-06：缺乏並發 Session 攻擊防護

- **檔案**: `routes/auth_routes.py`（第 367-400 行）
- **說明**: 同一使用者可同時啟動多個 OAuth 流程，無 session 指紋驗證。
- **建議**: 加入 IP + User-Agent 雜湊的 session 指紋機制。

### M-07：缺少安全回應標頭

- **檔案**: `APP.py`（第 120-126 行）
- **說明**: `add_security_headers()` 未設定 `X-Content-Type-Options: nosniff`、`X-Frame-Options`、`Referrer-Policy`。
- **建議**: 加入所有缺少的安全標頭。

### M-08：投訴表單資料重新渲染風險

- **檔案**: `routes/web_routes.py`（第 60-63 行）
- **說明**: 表單資料透過 `prev_data=request.form` 重新渲染至模板，雖 Jinja2 預設自動跳脫，但模式本身有風險。
- **建議**: 在伺服器端驗證並消毒 `prev_data`。

### M-09：重新導向 URL 驗證不足

- **檔案**: `routes/auth_routes.py`（第 452 行）、`templates/callback.html`
- **說明**: 前端驗證可被繞過，協定相對 URL（如 `//evil.com`）可能造成開放重新導向。
- **建議**: 在伺服器端驗證重新導向 URL，僅允許白名單路徑。

### M-10：DOM 中暴露 Patient ID

- **檔案**: `templates/main.html`（第 6 行）
- **說明**: Patient ID 直接渲染在 HTML data 屬性中，頁面原始碼可見。
- **建議**: 改由 `/api/session` 端點透過 AJAX 取得。

### M-11：Tradeoff 圖表 DOM XSS 風險

- **檔案**: `templates/tradeoff_analysis.html`（第 573-584 行）
- **說明**: 使用 `innerHTML` 構建動態內容，雖使用 `escapeHtml()` 但 `badges` 變數插入時未跳脫。
- **建議**: 改用 `createElement()` + `appendChild()` 替代 `innerHTML`。

### M-12：投訴路徑潛在路徑穿越

- **檔案**: `routes/web_routes.py`（第 87-94 行）
- **說明**: 投訴檔案路徑使用 `os.getcwd()` 構建，未驗證是否在應用程式 `instance/` 目錄下。
- **建議**: 使用 `os.path.abspath()` 驗證路徑是否在允許範圍內。

### M-13：CAPTCHA 機制薄弱

- **檔案**: `routes/web_routes.py`（第 44-62 行）
- **說明**: 簡單算術 CAPTCHA 可被機器輕易破解，無錯誤嘗試次數限制。
- **建議**: 改用 reCAPTCHA v3 或 hCaptcha。

### M-14：Patient ID 日誌未完全遮罩

- **檔案**: `services/fhir_client_service.py`（多處）
- **說明**: Patient ID 直接以 INFO 層級記錄，但 ePHI 過濾器僅匹配 `Patient/[id]` 格式，不匹配獨立 ID。
- **建議**: 更新過濾器正規表達式或避免在 INFO 層級記錄 patient_id。

---

## 四、低風險 (Low)

| 編號 | 說明 | 檔案 |
|------|------|------|
| L-01 | 健康檢查端點洩露版本號 | `APP.py`（第 109 行）|
| L-02 | 外部 JS 庫缺少子資源完整性 (SRI) | `templates/` 多處 |
| L-03 | 前端包含備用評分係數（演算法曝露）| `static/js/main.js`（第 65-79 行）|
| L-04 | FHIR 搜尋參數白名單過於寬鬆 | `utils/input_validator.py`（第 338-352 行）|
| L-05 | 肌酸酐驗證無臨床警告上限 | `services/unit_conversion_service.py`（第 149-155 行）|
| L-06 | FHIR 日期排序未處理所有格式 | `services/fhir_utils.py`（第 8-36 行）|
| L-07 | Consent 服務 Patient ID 日誌未遮罩 | `services/consent_service.py`（第 112、122 行）|
| L-08 | 稽核日誌完整性驗證從未被呼叫 | `services/audit_logger.py`（第 237-264 行）|
| L-09 | 投訴提交端點缺少速率限制 | `routes/web_routes.py`（第 49-111 行）|
| L-10 | `app.yaml` 硬編碼重新導向 URI | `app.yaml`（第 25 行）|

---

## 五、合規性評估

### HIPAA 技術保障措施

| 要求 | 狀態 | 說明 |
|------|------|------|
| 存取控制 (§164.312(a)) | ⚠️ 部分符合 | BOLA 防護存在，但裝飾器順序問題（C-04）|
| 稽核控制 (§164.312(b)) | ❌ 不符合 | 稽核日誌在 GAE 上靜默失敗（C-06）|
| 完整性控制 (§164.312(c)) | ⚠️ 部分符合 | 雜湊鏈實作存在，但有競爭條件（H-04）|
| 傳輸安全 (§164.312(e)) | ⚠️ 部分符合 | HTTPS/HSTS 已配置，但開發模式安全設定不足（M-03）|
| 身分驗證 (§164.312(d)) | ❌ 不符合 | OIDC 驗證失敗可繞過（C-01）|

### HL7 FHIR 安全合規

| 要求 | 狀態 | 說明 |
|------|------|------|
| OAuth2/SMART 認證 | ⚠️ 部分符合 | PKCE 實作良好，但缺少過期驗證（H-01）|
| Consent 管理 | ❌ 不符合 | 預設允許所有資源（C-02）|
| 安全標籤處理 | ⚠️ 部分符合 | 標籤檢測存在但未實際過濾受限資源 |
| CDS Hooks 安全 | ⚠️ 部分符合 | CORS 配置正確（依規範），但 JSON 解析有風險（C-03）|

---

## 六、修復優先順序

### 第一優先（立即修復 — 1 週內）

1. **C-01**: OIDC 驗證失敗時拒絕認證
2. **C-02**: Consent 服務改為預設拒絕
3. **C-03**: CDS Hooks 加入 JSON 解析錯誤處理
4. **C-06**: 稽核日誌改用 Cloud Logging API（GAE 環境）
5. **C-07**: 錯誤訊息不回傳內部細節

### 第二優先（緊急修復 — 2 週內）

6. **C-04**: 修正 BOLA 裝飾器順序
7. **C-05**: Refresh Token 加入速率限制與驗證
8. **H-01**: PKCE 參數加入過期時間
9. **H-02**: 修正 SSRF 驗證競爭條件
10. **H-04**: 修正稽核雜湊鏈競爭條件
11. **H-08**: 移除 CSP unsafe-inline

### 第三優先（重要修復 — 1 個月內）

12. **M-01 ~ M-14**: 中風險項目依序處理
13. **H-05 ~ H-09**: 其餘高風險項目

### 第四優先（持續改善）

14. **L-01 ~ L-10**: 低風險項目納入技術債務追蹤

---

## 七、測試方法論

本次測試採用以下方法：

1. **靜態原始碼分析 (SAST)**: 逐行審查所有 Python 後端程式碼、Jinja2 模板、JavaScript 前端程式碼
2. **架構安全審查**: 評估認證流程、授權機制、資料流向
3. **設定檔審查**: 檢查 CSP、CORS、Session、部署配置
4. **合規性對照**: 比對 HIPAA 技術保障措施、HL7 FHIR 安全指引
5. **OWASP Top 10 (2021) 檢核**: 系統性檢查十大 Web 應用安全風險

### 測試範圍

| 類別 | 涵蓋檔案 |
|------|---------|
| 認證與授權 | `auth_routes.py`, `web_utils.py`, `oidc_validator.py`, `mfa_validator.py`, `patient_context.py` |
| 輸入驗證 | `input_validator.py`, `hooks.py`, `api_routes.py` |
| FHIR 資料處理 | `fhir_client_service.py`, `fhir_data_service.py`, `condition_checker.py`, `consent_service.py` |
| 安全控制 | `audit_logger.py`, `logging_filter.py`, `security_labels.py` |
| 前端安全 | `templates/` 全部模板, `static/js/main.js` |
| 部署配置 | `APP.py`, `app.yaml`, `docker-compose.yml`, `app_config.py` |

---

## 八、結論

PRECISE-HBR SMART on FHIR 應用程式在安全基礎架構方面表現良好，已實作多項業界最佳實踐（PKCE、SSRF 防護、BOLA 防護、ePHI 過濾等）。然而，仍存在 7 項嚴重風險需立即修復，特別是 **OIDC 驗證繞過**（C-01）和 **Consent 預設允許**（C-02）直接影響病患資料安全與 HIPAA 合規性。

建議開發團隊優先處理第一、第二優先修復項目，並在修復完成後進行動態應用程式安全測試 (DAST) 以驗證修復效果。

---

*報告結束*
