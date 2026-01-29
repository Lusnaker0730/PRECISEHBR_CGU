
# SMART on FHIR 安全改進待辦清單

> 基於 `docs/Security.md` 標準指南的安全合規性評估

---

## ✅ 已完成項目

### 2026-01-29 已實作

- [x] **id_token JWT 驗證** (標準 2.2.1)
  - 新增 `utils/oidc_validator.py`
  - RS256/ES256 簽章驗證
  - 拒絕 HS256 和 none 演算法
  - 驗證 iss, aud, exp claims
  - JWKS 快取機制
  
- [x] **Patient Context 綁定 / BOLA 防護** (標準 3.2.1)
  - 新增 `utils/patient_context.py`
  - API 請求驗證 patient_id 與授權 context 一致
  - 安全違規事件記錄到稽核日誌
  - 裝飾器 `@require_patient_context`

---

## 🔴 高優先級 (High Priority)

### FHIR 資源安全

- [ ] **meta.security 標籤處理** (標準 6.1.1)
  - 讀取 FHIR 資源時檢查 `meta.security` 元素
  - 處理 `N` (Normal), `R` (Restricted), `V` (Very Restricted) 標籤
  - 對 R/V 等級資源實施 UI 警告或資料遮蔽
  - **預估工時**: 4-6 小時
  - **實作位置**: `services/fhir_data_service.py`

### Token 安全

- [ ] **Refresh Token Rotation** (標準 2.4.2)
  - 使用 refresh token 換取新 access token 時，invalidate 舊的 refresh token
  - 限制 refresh token 重放攻擊窗口
  - **預估工時**: 2-3 小時
  - **實作位置**: `routes/auth_routes.py`

---

## 🟡 中優先級 (Medium Priority)

### 隱私控制

- [ ] **Consent 資源查詢** (標準 6.2)
  - 存取病患資料前查詢 FHIR Consent 資源
  - 根據 Consent 過濾可存取的資源類型
  - 支援細粒度隱私偏好
  - **預估工時**: 8-12 小時
  - **實作位置**: `services/fhir_client_service.py`

### 多因子認證

- [ ] **MFA 驗證 (amr claim)** (標準 3.1.1 / V2)
  - 從 id_token 中檢查 `amr` (Authentication Methods Reference) claim
  - 對敏感操作要求 MFA 認證
  - 記錄認證方法到稽核日誌
  - **預估工時**: 3-4 小時
  - **實作位置**: `utils/oidc_validator.py`, `routes/auth_routes.py`

### 輸入驗證

- [ ] **FHIR Search Injection 防護** (標準 3.2.3)
  - 對 FHIR 搜尋參數進行嚴格型別檢查
  - 使用白名單過濾搜尋參數
  - 防止 Query String 注入攻擊
  - **預估工時**: 4-6 小時
  - **實作位置**: `services/fhir_client_service.py`, `utils/input_validator.py`

---

## 🟢 低優先級 (Low Priority)

### 資料溯源

- [ ] **Provenance 資源創建** (標準 7.2)
  - 若新增寫入功能，需創建 FHIR Provenance 資源
  - 記錄資料來源、創建者、時間戳記
  - **現狀**: 目前為唯讀應用，暫不需要
  - **預估工時**: 12-16 小時

### Token 綁定

- [ ] **DPoP (Demonstrating Proof-of-Possession) Token Binding** (標準 3.2.2)
  - 將 Token 與客戶端 TLS 通道綁定
  - 防止 Bearer Token 被竊後重放
  - **預估工時**: 16-24 小時
  - **備註**: 需要 FHIR 伺服器支援

### 台灣法規

- [ ] **醫事人員憑證 (HCA) 整合** (標準 4.1.3)
  - 整合台灣醫事人員卡進行電子簽章
  - 需要客戶端元件配合 (ActiveX/瀏覽器擴充)
  - 簽章後寫入 FHIR `Provenance.signature` 欄位
  - **預估工時**: 40+ 小時
  - **備註**: 需要醫院資訊室配合

---

## 🔵 維運相關 (Operational)

### 年度安全檢核

- [ ] **年度滲透測試** (標準 4.2)
  - 安排專業資安團隊進行滲透測試
  - 測試範疇：
    - OAuth 授權流程繞過
    - FHIR API 存取邏輯漏洞
    - PKCE 實作正確性
    - Session 管理
  - **頻率**: 每年一次
  - **負責單位**: 資安部門 / 外部廠商

### 合規認證

- [ ] **雲端 ISO 認證確認** (標準 4.1.1)
  - 確認 GCP 部署範圍在以下認證範圍內：
    - ISO/CNS 27001
    - ISO/CNS 27017
    - ISO/CNS 27018
    - ISO/CNS 27701
  - **負責單位**: 資訊部門

### 持續監控

- [ ] **弱點掃描排程**
  - 設定每季自動執行弱點掃描
  - 整合到 CI/CD 流程
  - 使用 `bandit`, `pip-audit` 等工具
  - **現狀**: 已有工具，需設定排程

- [ ] **依賴套件更新**
  - 定期檢查並更新依賴套件
  - 監控 CVE 漏洞通報
  - **指令**: `pip list --outdated`, `pip-audit`

---

## 📊 進度追蹤

| 類別 | 總項目 | 已完成 | 進度 |
|------|--------|--------|------|
| 高優先級 | 2 | 0 | 0% |
| 中優先級 | 3 | 0 | 0% |
| 低優先級 | 3 | 0 | 0% |
| 維運相關 | 4 | 0 | 0% |
| **已完成** | 2 | 2 | 100% ✅ |

---

## 參考資源

- [SMART on FHIR Security Standards](file:///d:/PRECISEHBR/smart_fhir_app/docs/Security.md)
- [ONC Compliance Status](file:///d:/PRECISEHBR/smart_fhir_app/docs/compliance/ONC_COMPLIANCE_STATUS_SUMMARY.md)
- [Security Deployment Guide](file:///d:/PRECISEHBR/smart_fhir_app/docs/deployment/SECURITY_DEPLOYMENT_GUIDE.md)
- [TW Core IG](https://twcore.mohw.gov.tw/ig/twcore/)

---

*最後更新: 2026-01-29*
