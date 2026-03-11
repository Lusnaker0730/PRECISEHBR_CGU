# PRECISE-HBR SMART on FHIR 產品化差距分析報告

**文件版本：** 1.0
**分析日期：** 2026-02-23
**專案分支：** PRECISE-HBR
**應用版本：** 1.0.0

---

## 目錄

1. [摘要](#摘要)
2. [目前已完成的部分](#目前已完成的部分)
3. [一、架構與基礎設施層面](#一架構與基礎設施層面)
4. [二、可靠性與監控層面](#二可靠性與監控層面)
5. [三、安全與合規層面](#三安全與合規層面)
6. [四、部署與維運層面](#四部署與維運層面)
7. [五、使用者體驗與商業層面](#五使用者體驗與商業層面)
8. [六、優先排序建議](#六優先排序建議)

---

## 摘要

本報告針對 PRECISE-HBR SMART on FHIR 臨床決策支援系統進行產品化準備度評估，識別出從原型/開發階段邁向正式產品所需補足的差距項目。分析涵蓋架構、可靠性、安全合規、部署維運及使用者體驗五大面向，共計 20 項待改善事項，並依優先級排序提供實作建議。

---

## 目前已完成的部分

以下為專案目前已具備且品質良好的功能與基礎設施：

| 類別 | 已完成項目 |
|------|-----------|
| **認證授權** | SMART on FHIR OAuth2 + PKCE 認證流程、多 ISS 支援 (Epic/Cerner)、id_token OIDC 驗證、Refresh Token Rotation |
| **核心演算法** | PRECISE-HBR 計算引擎 (7 因子)、Bleeding vs Thrombosis Tradeoff 模型、ARC-HBR 因子偵測 |
| **標準整合** | CDS Hooks 1.0 整合 (medication-prescribe, patient-view)、FHIR R4 資源存取、台灣 TW Core IG 適配器 |
| **安全防護** | CSP + Nonce、HSTS、Rate Limiting、CSRF Protection、BOLA Protection、Input Validation、defusedxml |
| **合規** | ePHI 審計日誌 (SHA-256 tamper-resistant chain)、FHIR Security Labels 支援、Consent Resource 處理 |
| **CI/CD** | GitHub Actions Pipeline (lint/security scan/test/build/docker) |
| **部署** | Docker 容器化、Google App Engine 部署設定、Kubernetes manifest |
| **測試** | 單元測試、整合測試、安全測試、效能測試 (Locust)、E2E 測試 |
| **文件** | PRD、安全規格、合規文件、使用手冊、架構文件 |

---

## 一、架構與基礎設施層面

### 1. 缺少正式的持久化資料庫

**現況：**
- 審計日誌寫入本地檔案 `instance/audit/audit_log.jsonl`
- 投訴資料寫入本地檔案 `instance/complaints/complaints.jsonl`
- 無資料庫連線設定

**問題：**
- Google App Engine Standard 環境的本地檔案系統是臨時性的 (ephemeral)，部署新版本或 instance 重啟後資料會遺失
- 多 instance 水平擴展時無法共享資料
- 沒有備份與災難復原機制
- 無法滿足 ONC 45 CFR 170.315(d)(2) 審計日誌 7 年保留要求

**建議方案：**

| 資料類型 | 建議儲存方案 | 理由 |
|----------|-------------|------|
| 審計日誌 | Google Cloud Logging + BigQuery | 結構化查詢、長期保留、合規需求 |
| 投訴資料 | Cloud Firestore 或 Cloud SQL (PostgreSQL) | ACID 交易、查詢彈性 |
| 使用者回饋 | 同上 | 與投訴整合管理 |

---

### 2. 缺少伺服器端 Session 儲存

**現況：**
- 使用 Flask 原生 cookie-based session（客戶端簽名 cookie）
- 程式碼中有 `flask-session==0.5.0` 的依賴但實際未使用

**問題：**
- Cookie 大小限制為 4KB，FHIR access token + refresh token + user identity 資料容易超過此限制
- 所有 session 資料存放在客戶端，雖有簽名但敏感度較高
- 無法實作 session revocation（無法登出其他裝置上的 session）
- 無法追蹤活躍 session 數量

**建議方案：**
- 使用 Google Cloud Memorystore (Redis) 做 server-side session storage
- 或使用 Cloud Firestore 做 session backend
- Cookie 僅存放 session ID，實際資料存放在伺服器端

---

### 3. 缺少 Secret Rotation 機制

**現況：**
- `FLASK_SECRET_KEY` 在部署後固定不變
- 透過 GCP Secret Manager 管理，但無自動輪換

**問題：**
- 若 key 洩漏，所有以該 key 簽署的 session cookie 均可被偽造
- 無法在不中斷服務的情況下更換 key

**建議方案：**
- 實作雙 key 機制：新簽署用 primary key、驗證時同時接受 primary + secondary key
- 配合 GCP Secret Manager 的 version 功能做 key rotation
- 定期（如每 90 天）輪換一次

---

## 二、可靠性與監控層面

### 4. 缺少 APM (Application Performance Monitoring)

**現況：**
- 僅有基本的 Python `logging` 模組輸出
- 無 request tracing、latency tracking、error rate 監控

**問題：**
- 無法即時發現效能退化或服務異常
- 無法追蹤跨服務的 request 路徑（如 App → FHIR Server）
- 醫療應用對 SLA 要求較高，需要主動監控

**建議方案：**

| 方案 | 工具 | 適用情境 |
|------|------|---------|
| GCP 原生 | Cloud Monitoring + Cloud Trace + Error Reporting | 已使用 GAE，整合成本低 |
| 第三方 | Sentry (error tracking) + Datadog/New Relic (APM) | 需要更豐富的儀表板 |

**關鍵 Alert 設定建議：**
- Error rate > 1% → Warning
- P95 latency > 2s → Warning
- P99 latency > 5s → Critical
- 5xx rate > 5% → Critical
- Health check failure → Critical

---

### 5. 缺少 Structured Logging

**現況：**
```python
logging.basicConfig(level=log_level, format='%(levelname)s:%(name)s:%(message)s')
```

**問題：**
- 純文字格式的 log 難以在 Cloud Logging 中做結構化查詢和分析
- 缺少 request correlation ID，無法關聯同一請求的多筆 log
- 無法有效地建立 log-based metrics

**建議方案：**
- 使用 JSON structured logging 格式
- 每筆 log 包含：`request_id`, `user_id`, `patient_id` (masked), `duration_ms`, `endpoint`, `status_code`
- 使用 `python-json-logger` 或 GCP 的 `google-cloud-logging` 套件

**範例格式：**
```json
{
  "severity": "INFO",
  "message": "Risk calculation completed",
  "request_id": "abc-123",
  "user_id": "practitioner-456",
  "patient_id": "Patient/***89",
  "duration_ms": 342,
  "endpoint": "/api/calculate_risk",
  "status_code": 200,
  "timestamp": "2026-02-23T10:15:30.000Z"
}
```

---

### 6. 缺少 Circuit Breaker / Retry 機制

**現況：**
- FHIR server 呼叫使用 `requests` 套件，無重試或斷路器模式
- 單次失敗即回傳錯誤給使用者

**問題：**
- FHIR server 暫時性錯誤（網路抖動、短暫過載）會直接導致使用者看到錯誤
- 連續失敗時仍持續嘗試呼叫，可能加重下游服務負擔

**建議方案：**
- 使用 `tenacity` 套件實作 retry with exponential backoff
- 實作 Circuit Breaker pattern（連續 N 次失敗後暫停呼叫一段時間）
- 提供 graceful degradation：部分資料無法取得時仍顯示可用部分

---

### 7. 缺少 Health Check 深度檢查

**現況：**
```python
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', ...}), 200
```

**問題：**
- Health check 總是回傳 healthy，無法反映真實的服務依賴狀態
- Load balancer 可能將流量導向實際上無法服務的 instance

**建議方案：**
- Liveness probe：維持現有簡單檢查（確認 process 存活）
- Readiness probe：加入依賴檢查
  - Session store 連線狀態
  - 設定檔載入狀態
  - 選擇性檢查 FHIR server 可達性（加 timeout 和 cache）

---

## 三、安全與合規層面

### 8. 缺少 Dependency 版本鎖定 (Lock File)

**現況：**
- `requirements.txt` 使用 `==` 固定直接依賴版本（良好）
- 但缺少完整的 lock 檔，transitive dependencies 未鎖定

**問題：**
- 間接依賴的版本可能在不同時間安裝時不同，導致行為不一致
- 供應鏈攻擊風險：惡意套件可能透過間接依賴引入

**建議方案：**
- 使用 `pip-compile`（pip-tools）產生完整的 lock 檔，含所有 transitive dependencies 及 hash 驗證
- 或遷移至 `Poetry` / `PDM` 做依賴管理

---

### 9. 測試/開發工具混入 Production 依賴

**現況：**

`requirements.txt` 包含以下非 production 必要的套件：

| 套件 | 類型 | Production 是否需要 |
|------|------|-------------------|
| `bandit==1.7.5` | 安全掃描工具 | 否 |
| `pip-audit==2.7.2` | 依賴審計工具 | 否 |
| `pytest==8.3.4` | 測試框架 | 否 |
| `pytest-cov==7.0.0` | 測試覆蓋率 | 否 |
| `coverage==7.12.0` | 覆蓋率分析 | 否 |
| `locust==2.24.0` | 負載測試 | 否 |
| `pandas==2.0.3` | 資料分析 | 待確認 |
| `matplotlib==3.7.2` | 資料視覺化 | 待確認 |
| `seaborn==0.12.2` | 統計視覺化 | 待確認 |
| `flask-session==0.5.0` | Session 管理 | 未使用 |

**問題：**
- Production Docker image 體積膨脹（估計 ~500MB → 可壓縮至 ~200MB）
- 增加攻擊面
- 延長部署時間

**建議方案：**
```
requirements.txt           # 僅 production 依賴
requirements-dev.txt       # 測試、linting、安全掃描工具
requirements-analytics.txt # 資料分析套件（如 runtime 需要）
```

---

### 10. 缺少 WAF (Web Application Firewall)

**現況：**
- 依賴應用層的 Rate Limiting 和 Input Validation
- 無網路層防護

**建議方案：**
- 在 GAE 前方啟用 Google Cloud Armor
- 設定規則：DDoS 防護、地理位置限制（如僅允許台灣 IP）、常見攻擊模式過濾
- 搭配 Cloud CDN 做靜態資源加速

---

### 11. 程式碼品質：Dead Code

**檔案：** `services/app_config.py` 第 92 行

**現況：**
```python
def get_client_id_by_iss(cls, iss: str) -> str:
    # ...
    # Fallback to default
    return cls.DEFAULT_CLIENT_ID   # Line 91 - 實際執行
    return cls.DEFAULT_CLIENT_ID   # Line 92 - Dead code，永遠不會執行
```

**建議：** 移除第 92 行的重複 return 語句。

---

## 四、部署與維運層面

### 12. 缺少環境分離

**現況：**
- 僅有一個 `app.yaml` 設定
- 透過環境變數 `FLASK_ENV` 區分開發/生產

**問題：**
- 沒有 Staging 環境用於上線前驗證
- 無法在類似 production 的環境中做最終測試
- 增加直接部署到 production 的風險

**建議方案：**

| 環境 | 設定檔 | 用途 |
|------|--------|------|
| Development | `app-dev.yaml` | 本地/雲端開發 |
| Staging | `app-staging.yaml` | 上線前驗證、UAT |
| Production | `app.yaml` | 正式環境 |

每個環境使用獨立的 GCP Project 或 GAE Service。

---

### 13. 缺少 Database Migration 工具

**現況：**
- 目前無資料庫，因此無此需求

**問題：**
- 導入資料庫後，schema 變更需要系統化管理

**建議方案：**
- 若使用 Cloud SQL：使用 `Alembic`（搭配 SQLAlchemy）做 migration
- 若使用 Firestore：設計 document version 機制

---

### 14. 缺少 Rollback 策略

**現況：**
- 無明確的 rollback SOP
- 無 canary deployment 設定

**建議方案：**
- 利用 GAE 的 version traffic splitting 做 canary deploy（如 5% → 25% → 100%）
- 制定 rollback SOP：
  1. 發現問題後，將流量 100% 切回上一版本
  2. 分析 root cause
  3. 修復後重新走 canary deploy 流程
- 設定自動 rollback trigger（如 error rate 超過閾值）

---

### 15. Dockerfile 安全加固不足

**現況：**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn", "-b", ":8080", "--timeout", "120", "APP:app"]
```

**問題：**
- 以 root 使用者執行（容器逃逸風險）
- 單階段建構，image 包含不必要的建構工具
- 未設定資源限制

**建議方案：**
```dockerfile
# Stage 1: Build
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
CMD ["gunicorn", "-b", ":8080", "--timeout", "120", "--workers", "2", "APP:app"]
```

---

## 五、使用者體驗與商業層面

### 16. 缺少 i18n (國際化) 架構

**現況：**
- 介面混合中英文，無系統化的語言切換機制
- 硬編碼的文字散佈在 templates 和 Python 程式碼中

**問題：**
- 台灣市場需要完整正體中文支援
- 國際市場或學術合作需要英文介面
- 新增語言時需逐一修改檔案

**建議方案：**
- 使用 `Flask-Babel` 做 i18n/l10n
- 建立翻譯檔案目錄 `translations/zh_TW/`, `translations/en/`
- 日期、數字格式根據 locale 自動調整

---

### 17. 缺少 Versioning 策略

**現況：**
- Health endpoint 硬編碼 `version: '1.0.0'`
- 無 API versioning
- 無自動化版本管理

**問題：**
- 無法追蹤部署的確切版本
- API 變更可能破壞現有 CDS Hooks 整合
- 無法做向後相容的 API 演進

**建議方案：**
- 使用 Semantic Versioning (SemVer)
- 從 `pyproject.toml` 或 git tag 自動讀取版本號
- API 加上版本前綴：`/api/v1/calculate_risk`
- CDS Hooks discovery 端點包含版本資訊

---

### 18. 缺少 Terms of Service / Privacy Policy

**現況：**
- 有 `PRICING_TRANSPARENCY.md` 但缺少正式的使用條款和隱私權政策
- 缺少 EULA (End User License Agreement)

**問題：**
- 醫療 SaaS 產品法律上必須提供使用條款
- 處理 ePHI 資料需要明確的隱私權政策
- 台灣《個人資料保護法》要求告知當事人資料蒐集目的

**建議方案：**
- 建立 Terms of Service 頁面（`/terms`）
- 建立 Privacy Policy 頁面（`/privacy`）
- 在首次使用時要求使用者同意
- 諮詢醫療法規律師審核內容

---

### 19. 缺少 Rate Limiting 使用者回饋

**現況：**
- Rate limit 觸發後的使用者體驗未定義
- 可能顯示原始的 429 錯誤

**建議方案：**
- 自訂 429 Too Many Requests 錯誤頁面，說明限制原因和重試時間
- 在 API response header 中加入 `X-RateLimit-Remaining` 和 `X-RateLimit-Reset`
- 前端在接近限制時顯示提示

---

### 20. 缺少 SaMD 法規所需文件

**現況：**
- 已有部分文件：風險分析報告、風險管理計畫、V&V Protocol、Golden Dataset
- 但不完整，尚未達到 SaMD 上市要求

**問題：**
- 若定位為醫療器材軟體 (SaMD)，需符合國內外法規要求

**所需文件清單：**

| 法規標準 | 文件 | 現況 |
|----------|------|------|
| IEC 62304 | 軟體開發生命週期計畫 | 缺少 |
| IEC 62304 | 軟體需求規格 (SRS) | 部分（PRD 涵蓋部分） |
| IEC 62304 | 軟體架構設計文件 (SAD) | 部分（architecture/ 涵蓋部分） |
| IEC 62304 | 軟體測試計畫與報告 | 部分（testing/ 涵蓋部分） |
| IEC 62366 | 可用性工程檔案 | 部分（USER_CENTERED_DESIGN_PROCESS.md） |
| ISO 14971 | 風險管理檔案 | 部分（risk_analysis_report.md） |
| ISO 13485 | 品質管理系統 | 缺少 |
| TFDA | 醫療器材查驗登記申請 | 待評估適用性 |
| FDA 21 CFR Part 11 | 電子記錄電子簽章 | 缺少 |

---

## 六、優先排序建議

### P0 — 上線阻擋 (Must Fix Before Launch)

| # | 項目 | 影響 | 預估工作量 |
|---|------|------|-----------|
| 1 | 分離 production / development 依賴 | 安全、效能、image 大小 | 0.5 天 |
| 2 | 永久化審計日誌 (Cloud Logging / DB) | GAE 本地檔案會遺失，合規要求 | 2-3 天 |
| 3 | Server-side Session 方案 | Cookie 4KB 限制，安全性 | 1-2 天 |
| 4 | 修復 dead code (`app_config.py:92`) | 程式碼品質 | 5 分鐘 |

### P1 — 重要 (Should Fix Before Launch)

| # | 項目 | 影響 | 預估工作量 |
|---|------|------|-----------|
| 5 | APM + Structured Logging | 營運可見性、問題排查 | 2-3 天 |
| 6 | 環境分離 (Staging) | 安全部署流程 | 1 天 |
| 7 | Dockerfile 安全加固 | Container 安全最佳實踐 | 0.5 天 |
| 8 | Terms of Service / Privacy Policy | 法律合規 | 視法律審核時間 |
| 9 | Rollback 策略與 SOP | 營運安全 | 1 天 |

### P2 — 改善 (Post-Launch Improvements)

| # | 項目 | 影響 | 預估工作量 |
|---|------|------|-----------|
| 10 | Circuit Breaker / Retry 機制 | 服務可靠性 | 1-2 天 |
| 11 | API Versioning | 向後相容性 | 1 天 |
| 12 | WAF (Cloud Armor) | 進階網路防護 | 0.5 天 |
| 13 | Health Check 深度檢查 | 負載均衡準確性 | 0.5 天 |
| 14 | Rate Limiting 使用者回饋 | 使用者體驗 | 0.5 天 |
| 15 | i18n 國際化 | 市場擴展 | 3-5 天 |
| 16 | Versioning 策略 | 版本管理 | 1 天 |

### P3 — 長期規劃 (Strategic)

| # | 項目 | 影響 | 預估工作量 |
|---|------|------|-----------|
| 17 | SaMD 法規文件完善 | 醫材認證上市 | 數月（需法規顧問） |
| 18 | Dependency Lock File | 供應鏈安全 | 0.5 天 |
| 19 | Secret Rotation 機制 | 長期安全 | 1-2 天 |
| 20 | Database Migration 工具 | 資料庫導入後必需 | 1 天 |

---

## 附錄：專案技術摘要

| 項目 | 內容 |
|------|------|
| **框架** | Flask 3.0.3 (Python 3.11) |
| **部署** | Google App Engine Standard + Docker |
| **認證** | SMART on FHIR OAuth2 + PKCE |
| **標準** | FHIR R4, CDS Hooks 1.0, TW Core IG |
| **安全** | OWASP ASVS Level 2+, ONC 45 CFR 170.315 |
| **測試** | Pytest + Locust (單元/整合/安全/效能/E2E) |
| **CI/CD** | GitHub Actions (6 workflows) |
| **直接依賴** | 28 packages |

---

*本報告由系統架構分析自動產生，建議由技術主管和產品負責人共同審閱後制定實作計畫。*
