# PRECISE-HBR 安全測試指南

## 概述

本文檔描述 PRECISE-HBR 應用程式的安全測試策略和實施方法。我們的安全測試涵蓋 OWASP Top 10、HIPAA 合規性、SMART on FHIR 安全要求，以及醫療資訊系統特定的安全需求。

## 測試範圍

### 1. OWASP Top 10 (2021)

#### A01:2021 - Broken Access Control (存取控制失效)
- **測試文件**: `test_security_comprehensive.py::TestOWASPTop10`
- **測試項目**:
  - 未授權存取保護端點
  - 患者資料存取控制
  - API 端點身份驗證
  - 水平權限提升防護

#### A02:2021 - Cryptographic Failures (加密失效)
- **測試文件**: `test_security_comprehensive.py::TestOWASPTop10`
- **測試項目**:
  - Session cookie 安全標誌
  - HTTPOnly cookie 設定
  - SECRET_KEY 強度驗證
  - 敏感資料加密

#### A03:2021 - Injection (注入攻擊)
- **測試文件**: `test_input_validation.py`
- **測試項目**:
  - SQL 注入防護
  - 命令注入防護
  - LDAP 注入防護
  - XSS 防護
  - XML 注入防護

#### A04:2021 - Insecure Design (不安全設計)
- **測試文件**: `test_security_comprehensive.py::TestOWASPTop10`
- **測試項目**:
  - 速率限制
  - Session 超時設定
  - 安全預設值

#### A05:2021 - Security Misconfiguration (安全設定錯誤)
- **測試文件**: `test_security_comprehensive.py::TestOWASPTop10`
- **測試項目**:
  - Debug 模式檢查
  - 錯誤訊息安全性
  - 安全標頭設定
  - 預設憑證檢查

#### A06:2021 - Vulnerable Components (易受攻擊元件)
- **測試文件**: `test_security_comprehensive.py::TestOWASPTop10`
- **測試項目**:
  - 依賴套件版本檢查
  - requirements.txt 存在性

#### A07:2021 - Authentication Failures (身份驗證失效)
- **測試文件**: `test_smart_security.py::TestAuthenticationSecurity`
- **測試項目**:
  - OAuth state 參數驗證
  - PKCE 實施
  - Session 固定攻擊防護
  - Token 安全性

#### A08:2021 - Software and Data Integrity Failures (軟體與資料完整性失效)
- **測試文件**: `test_security_comprehensive.py::TestOWASPTop10`
- **測試項目**:
  - JWT 簽章驗證
  - 未簽名資料拒絕

#### A09:2021 - Logging Failures (日誌與監控失效)
- **測試文件**: `test_security_comprehensive.py::TestOWASPTop10`
- **測試項目**:
  - 稽核日誌啟用
  - 失敗登入記錄
  - 敏感資料脫敏

#### A10:2021 - Server-Side Request Forgery (SSRF)
- **測試文件**: `test_security_comprehensive.py::TestOWASPTop10`
- **測試項目**:
  - FHIR 伺服器 URL 驗證
  - 內部網路存取防護

### 2. HIPAA 合規性測試

#### §164.308(a)(1)(ii)(D) - 稽核控制
- **測試文件**: `test_ephi_protection.py::TestePHILogging`
- **測試項目**:
  - ePHI 存取記錄
  - 稽核日誌完整性
  - 日誌保留期限

#### §164.312(a)(2)(i) - 唯一使用者識別
- **測試文件**: `test_security_comprehensive.py::TestHIPAACompliance`
- **測試項目**:
  - 使用者識別追蹤
  - Session 使用者 ID

#### §164.312(a)(2)(iii) - 自動登出
- **測試文件**: `test_security_comprehensive.py::TestHIPAACompliance`
- **測試項目**:
  - Session 超時設定
  - 閒置自動登出

#### §164.312(e)(1) - 傳輸加密
- **測試文件**: `test_ephi_protection.py::TestePHITransmission`
- **測試項目**:
  - HTTPS 強制執行
  - TLS 版本檢查

### 3. SMART on FHIR 安全測試

#### Launch Sequence Security
- **測試文件**: `test_smart_security.py::TestSMARTLaunchSecurity`
- **測試項目**:
  - ISS 參數驗證
  - Launch 參數消毒
  - URL 格式驗證

#### OAuth 2.0 Security
- **測試文件**: `test_smart_security.py::TestOAuthSecurity`
- **測試項目**:
  - State 參數 CSRF 防護
  - PKCE 實施
  - Authorization code 單次使用

#### Token Security
- **測試文件**: `test_smart_security.py::TestTokenSecurity`
- **測試項目**:
  - Token 不在 URL
  - Token 安全儲存
  - Token 過期檢查

#### Scope Security
- **測試文件**: `test_smart_security.py::TestScopeSecurity`
- **測試項目**:
  - Scope 驗證
  - 最小權限原則
  - Scope 強制執行

### 4. ePHI 保護測試

#### Access Control
- **測試文件**: `test_ephi_protection.py::TestePHIAccessControl`
- **測試項目**:
  - 身份驗證要求
  - 授權檢查
  - 最小必要原則

#### Transmission Security
- **測試文件**: `test_ephi_protection.py::TestePHITransmission`
- **測試項目**:
  - HTTPS 強制
  - PHI 不在 URL
  - POST body 傳輸

#### Storage Security
- **測試文件**: `test_ephi_protection.py::TestePHIStorage`
- **測試項目**:
  - Session 儲存安全
  - Cookie 安全性
  - 資料加密

### 5. 輸入驗證測試

#### XSS Prevention
- **測試文件**: `test_input_validation.py::TestXSSPrevention`
- **測試項目**:
  - Reflected XSS
  - Stored XSS
  - DOM-based XSS

#### Injection Prevention
- **測試文件**: `test_input_validation.py`
- **測試項目**:
  - SQL 注入
  - 命令注入
  - Path traversal
  - XML 注入
  - JSON 注入

#### Input Size Validation
- **測試文件**: `test_input_validation.py::TestInputSizeValidation`
- **測試項目**:
  - 最大請求大小
  - JSON 巢狀深度
  - 陣列大小限制

## 執行安全測試

### 執行所有安全測試

```powershell
# PowerShell
python -m pytest tests/ -v -m security

# 或使用測試腳本
.\run_tests.ps1
# 選擇選項 5: 僅執行安全測試
```

```bash
# Bash
python -m pytest tests/ -v -m security

# 或使用測試腳本
./run_tests.sh
```

### 執行特定安全測試類別

```powershell
# OWASP Top 10 測試
python -m pytest tests/test_security_comprehensive.py::TestOWASPTop10 -v

# HIPAA 合規性測試
python -m pytest tests/test_security_comprehensive.py::TestHIPAACompliance -v

# SMART on FHIR 安全測試
python -m pytest tests/test_smart_security.py -v

# ePHI 保護測試
python -m pytest tests/test_ephi_protection.py -v

# 輸入驗證測試
python -m pytest tests/test_input_validation.py -v
```

### 執行滲透測試場景

```powershell
python -m pytest tests/test_smart_security.py::TestPenetrationTestScenarios -v
```

## 安全測試標記

使用 pytest markers 來標記和執行特定類型的安全測試：

```python
@pytest.mark.security
class TestSecurityFeature:
    """Security test class"""
    pass
```

## 測試覆蓋率

安全測試應該覆蓋：

1. **所有輸入點**
   - URL 參數
   - POST body
   - HTTP headers
   - Cookies
   - File uploads

2. **所有輸出點**
   - HTML 響應
   - JSON API
   - XML 輸出
   - Error messages
   - Logs

3. **所有身份驗證點**
   - Login
   - OAuth callback
   - API endpoints
   - Session management

4. **所有資料存取點**
   - Patient data
   - Lab results
   - Medications
   - Conditions

## 安全測試最佳實踐

### 1. 使用真實攻擊向量

```python
def test_sql_injection_prevention(self, client):
    """Test SQL injection prevention"""
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM users--",
    ]
    for payload in sql_payloads:
        response = client.get(f'/launch?iss={payload}')
        assert response.status_code in [200, 302, 400, 404]
```

### 2. 測試邊界條件

```python
def test_maximum_request_size(self, client):
    """Test maximum request size limit"""
    large_payload = {'patientId': 'a' * 1000000}
    response = client.post('/api/calculate_risk', json=large_payload)
    assert response.status_code in [400, 413]
```

### 3. 驗證安全標頭

```python
def test_security_headers_present(self, client):
    """Test that security headers are configured"""
    response = client.get('/')
    assert 'X-Content-Type-Options' in response.headers
    assert 'X-Frame-Options' in response.headers
```

### 4. 檢查敏感資料洩漏

```python
def test_no_sensitive_data_in_logs(self, client, caplog):
    """Test that sensitive data is not logged"""
    client.get('/health')
    log_text = caplog.text.lower()
    sensitive_patterns = ['password', 'secret', 'token']
    for pattern in sensitive_patterns:
        assert pattern not in log_text or 'redacted' in log_text
```

### 5. 測試存取控制

```python
def test_unauthorized_access_blocked(self, client):
    """Test that unauthorized access is blocked"""
    response = client.get('/main')
    assert response.status_code in [302, 401, 403]
```

## 常見安全漏洞檢查清單

### ✅ 身份驗證與授權
- [ ] 所有保護端點需要身份驗證
- [ ] Session 管理安全
- [ ] OAuth 實施正確
- [ ] PKCE 用於 OAuth
- [ ] Token 安全儲存
- [ ] Token 過期檢查

### ✅ 輸入驗證
- [ ] XSS 防護
- [ ] SQL 注入防護
- [ ] 命令注入防護
- [ ] Path traversal 防護
- [ ] 輸入大小限制
- [ ] 資料類型驗證

### ✅ 輸出編碼
- [ ] HTML 自動轉義
- [ ] JSON 正確編碼
- [ ] XML 正確編碼
- [ ] 錯誤訊息消毒

### ✅ 加密
- [ ] HTTPS 強制執行
- [ ] 強密鑰使用
- [ ] Session 加密
- [ ] 敏感資料加密

### ✅ Session 管理
- [ ] Session 超時
- [ ] Session 固定防護
- [ ] Secure cookie 標誌
- [ ] HTTPOnly cookie
- [ ] SameSite cookie

### ✅ 錯誤處理
- [ ] 通用錯誤訊息
- [ ] 無堆疊追蹤洩漏
- [ ] 錯誤日誌安全

### ✅ 日誌與監控
- [ ] ePHI 存取記錄
- [ ] 失敗登入記錄
- [ ] 敏感資料脫敏
- [ ] 稽核日誌完整性

### ✅ 安全標頭
- [ ] X-Content-Type-Options
- [ ] X-Frame-Options
- [ ] Content-Security-Policy
- [ ] Strict-Transport-Security
- [ ] X-XSS-Protection

## 持續安全測試

### 1. CI/CD 整合

在 CI/CD pipeline 中執行安全測試：

```yaml
# .github/workflows/security-tests.yml
name: Security Tests
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run security tests
        run: |
          pip install -r requirements.txt
          pytest tests/ -v -m security
```

### 2. 定期掃描

- **每週**: 執行完整安全測試套件
- **每月**: 執行依賴套件漏洞掃描 (`pip-audit`)
- **每季**: 進行滲透測試
- **每年**: 進行全面安全審計

### 3. 依賴套件掃描

```powershell
# 安裝 pip-audit
pip install pip-audit

# 掃描已知漏洞
pip-audit

# 掃描並生成報告
pip-audit --format json > security-audit.json
```

## 安全測試報告

### 測試結果解讀

```
✅ PASSED - 安全控制正常運作
⚠️ SKIPPED - 測試被跳過（可能是測試環境限制）
❌ FAILED - 發現安全漏洞，需要修復
```

### 漏洞嚴重性分級

- **Critical (嚴重)**: 立即修復，可能導致資料洩漏或系統入侵
- **High (高)**: 優先修復，存在明顯安全風險
- **Medium (中)**: 計劃修復，存在潛在安全風險
- **Low (低)**: 建議修復，最佳實踐改進
- **Info (資訊)**: 僅供參考，無直接風險

## 安全測試工具

### 1. Pytest 插件
- `pytest-security`: 安全測試插件
- `pytest-cov`: 覆蓋率報告
- `pytest-xdist`: 並行測試

### 2. 靜態分析工具
- `bandit`: Python 安全掃描
- `safety`: 依賴套件漏洞掃描
- `pip-audit`: 套件審計

### 3. 動態分析工具
- OWASP ZAP: Web 應用程式安全掃描
- Burp Suite: 滲透測試工具

## 修復安全漏洞

### 1. 識別漏洞

```powershell
# 執行測試找出失敗項目
python -m pytest tests/test_security_comprehensive.py -v
```

### 2. 分析根本原因

查看測試失敗訊息和堆疊追蹤，理解漏洞成因。

### 3. 實施修復

根據最佳實踐修復漏洞：

```python
# 範例：修復 XSS 漏洞
# 錯誤做法
return f"<div>{user_input}</div>"

# 正確做法（Jinja2 自動轉義）
return render_template('page.html', user_input=user_input)
```

### 4. 驗證修復

```powershell
# 重新執行測試
python -m pytest tests/test_security_comprehensive.py::test_xss_prevention -v
```

### 5. 回歸測試

```powershell
# 執行完整測試套件確保無副作用
python -m pytest tests/ -v
```

## 安全聯絡資訊

如果發現安全漏洞，請通過以下方式報告：

- **Email**: security@example.com
- **Bug Tracker**: 標記為 [SECURITY]
- **負責任披露**: 請給我們 90 天修復時間

## 參考資源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/)
- [SMART on FHIR Security](https://docs.smarthealthit.org/authorization/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)

## 更新歷史

- **2025-11-28**: 創建完整安全測試套件
  - 新增 OWASP Top 10 測試
  - 新增 HIPAA 合規性測試
  - 新增 SMART on FHIR 安全測試
  - 新增 ePHI 保護測試
  - 新增輸入驗證測試

