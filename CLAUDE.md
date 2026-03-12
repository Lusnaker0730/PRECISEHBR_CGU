# PRECISE-HBR SMART on FHIR Application

## Project Overview

A clinical decision support (CDS) web application that calculates **PRECISE-HBR bleeding risk scores** for PCI (Percutaneous Coronary Intervention) patients using SMART on FHIR. It integrates with EHR systems (Epic, Cerner) via OAuth2, retrieves patient data through FHIR APIs, and provides bleeding vs. thrombosis tradeoff analysis.

**Target users**: Cardiologists and interventional medicine clinicians in Taiwan and international healthcare settings.

## Tech Stack

- **Backend**: Python 3.11, Flask 3.0.3, Gunicorn
- **FHIR**: `fhirclient` 4.1.0, FHIR R4 / DSTU2 compatible
- **Auth**: SMART on FHIR OAuth2 with PKCE, OIDC id_token validation
- **Security**: Flask-Talisman (CSP/HSTS), Flask-Limiter, Flask-WTF (CSRF), Bandit, pip-audit
- **Deployment**: Google App Engine (Python 3.11 standard), Docker
- **Testing**: pytest, locust (load tests)
- **CI/CD**: GitHub Actions (ci.yml, test.yml, security-scan.yml, performance.yml, docker-build.yml, cd.yml)

## Architecture

```
APP.py                    # Flask app factory (create_app), entry point
extensions.py             # Flask-Limiter, CSRFProtect instances
├── routes/
│   ├── web_routes.py     # UI pages (/, /main, /docs, /standalone, /report-issue)
│   ├── auth_routes.py    # OAuth2 launch/callback/token exchange/refresh/logout
│   ├── api_routes.py     # REST API (/api/calculate_risk, /api/config/scoring, /api/feedback)
│   ├── tradeoff_routes.py # Tradeoff analysis (/tradeoff_analysis, /api/calculate_tradeoff)
│   └── hooks.py          # CDS Hooks endpoints (/cds-services, medication-prescribe, patient-view)
├── services/
│   ├── app_config.py     # Config class, GCP Secret Manager integration
│   ├── config_loader.py  # Loads cdss_config.json (LOINC codes, scoring params)
│   ├── fhir_client_service.py  # FHIR server HTTP client
│   ├── fhir_data_service.py    # Facade: legacy wrappers for all services
│   ├── precise_hbr_calculator.py # Core PRECISE-HBR score calculation
│   ├── risk_classifier.py       # Risk category classification (non-HBR/HBR/Very-HBR)
│   ├── tradeoff_model_calculator.py # Bleeding vs. thrombosis tradeoff analysis
│   ├── condition_checker.py     # Medical condition/medication detection
│   ├── unit_conversion_service.py # Lab value unit conversions, eGFR calculation
│   ├── twcore_adapter.py        # Taiwan Core IG support (Chinese names, NHI codes)
│   ├── fhir_utils.py            # FHIR date/observation utilities
│   ├── audit_logger.py          # ePHI access audit logging
│   └── consent_service.py       # FHIR Consent resource handling
├── utils/
│   ├── input_validator.py   # URL/patient-ID/FHIR search param validation, SSRF prevention
│   ├── web_utils.py         # Session validation, login_required decorator
│   ├── patient_context.py   # BOLA protection (patient context enforcement)
│   ├── oidc_validator.py    # OpenID Connect id_token validation
│   ├── mfa_validator.py     # MFA validation
│   ├── security_labels.py   # FHIR security label handling
│   └── logging_filter.py    # ePHI logging filter
├── config/
│   ├── cdss_config.json     # Master config: scoring params, LOINC codes, SNOMED codes, medication keywords
│   └── cds-services.json    # CDS Hooks service discovery manifest
├── fhir_resources/
│   └── valuesets/arc-hbr-model.json  # ARC-HBR tradeoff model data
├── templates/               # Jinja2 HTML templates
├── static/                  # CSS, JS, Cerner SMART embed library
└── tests/                   # pytest test suite
```

## Key Conventions

### Code Style
- Python 3.11+ features (walrus operator `:=`, `type[...]` hints)
- Service pattern: each service has a class + global singleton instance (e.g., `precise_hbr_calculator = PreciseHBRCalculator()`)
- Legacy backward-compatible functions wrap service methods (e.g., `calculate_precise_hbr_score()` wraps `precise_hbr_calculator.calculate_score()`)
- `fhir_data_service.py` is a facade providing all legacy function imports in one place

### Configuration
- All scoring coefficients, LOINC codes, SNOMED codes, medication keywords, and thresholds are in `config/cdss_config.json` - avoid hardcoding clinical values
- Secrets (CLIENT_ID, SECRET_KEY) go through GCP Secret Manager in production, env vars in development
- Environment config via `.env` file (loaded by python-dotenv)

### Security (Critical)
- SSRF prevention: `validate_url()` checks DNS resolution, blocks private IPs and cloud metadata endpoints
- BOLA protection: `@require_patient_context` decorator validates patient context on API routes
- Input validation: all user inputs validated before use (patient IDs, URLs, FHIR search params)
- ePHI logging filter: prevents patient health data from appearing in logs
- CSRF protection on all routes except CDS Hooks (which are CSRF-exempt by spec)
- Rate limiting on API endpoints via Flask-Limiter
- CSP nonce-based script security via Flask-Talisman

### Taiwan-Specific (TW Core IG)
- `twcore_adapter.py` handles Chinese names, Taiwan National ID, NHI medication codes
- ICD-10-CM and NHI code systems defined in `cdss_config.json`
- Demographics extraction defaults to TW Core IG adapter (`use_twcore=True`)

## Common Tasks

### Running Locally
```bash
pip install -r requirements.txt
# Set required env vars in .env: FLASK_SECRET_KEY, SMART_CLIENT_ID, SMART_REDIRECT_URI
python APP.py
```

### Running Tests
```bash
pytest                          # Run all tests
pytest -m security              # Security tests only
pytest -m "not slow"            # Skip slow tests
pytest --cov=. --cov-report=html  # With coverage
```

### Key Test Fixtures (tests/conftest.py)
- `app` fixture: creates Flask test app with mocked env vars and disabled CSRF
- `client` fixture: Flask test client
- `mock_patient_data`, `mock_observation_data`: standard FHIR test data

### Deployment
- **GAE**: `gcloud app deploy app.yaml`
- **Docker**: `docker-compose up` (dev) or `docker-compose -f docker-compose.prod.yml up` (prod)

## PRECISE-HBR Score Calculation

The core algorithm (`services/precise_hbr_calculator.py`):
1. **extract_inputs()**: Extracts/normalizes FHIR data with truncation limits
2. **calculate_pure_score()**: Pure math using config coefficients
3. **calculate_score()**: Orchestrates extraction + calculation, returns UI components

Score formula: `base(2) + age_score + hb_score + egfr_score + wbc_score + bleeding(7) + anticoag(5) + arc_hbr(3)`

Risk thresholds: <=22 = non-HBR, 23-26 = HBR (4% risk), >=27 = Very HBR (6% risk)

## 法規文件自動化生成 (TFDA / IEC 62304 / ISO 14971)

本專案目標為取得 **TFDA SaMD（醫療器材軟體）認證**。開發產出物直接作為法規送審證據，避免事後補文件。

### 適用法規標準
- **IEC 62304:2006+A1:2015** — 醫療器材軟體生命週期
- **ISO 14971:2019** — 醫療器材風險管理
- **IEC 82304-1:2016** — 健康軟體產品安全

### 追溯架構

所有法規產出物透過五層追溯鏈串聯：

```
SRS（軟體需求規格）→ SDS（軟體設計規格）→ 實作（PR）→ TEST（驗證）→ RISK（風險控制）
```

- **SRS-001~012**：軟體需求規格（GitHub Issues，標籤 `requirement`）
- **SDS-001~012**：軟體設計規格（GitHub Issues，標籤 `design`）
- **RISK-001~009**：風險分析項目，依 ISO 14971（GitHub Issues，標籤 `risk`）
- **TC-001~014**：驗證與確效測試案例（GitHub Issues，標籤 `test`）

### Pytest 法規追溯標記

測試**必須**使用標記以追溯至需求／風險／設計：

```python
@pytest.mark.requirement("SRS-001")   # 追溯至軟體需求
@pytest.mark.risk("RISK-001")         # 追溯至風險控制措施
@pytest.mark.design("SDS-001")        # 追溯至設計規格
```

標記定義於 `pytest.ini`，已啟用 `--strict-markers`。

### PR 範本（法規追溯區段）

每個 PR **必須**填寫 `.github/PULL_REQUEST_TEMPLATE.md` 中的法規追溯區段：
- **Implements**：連結 `[SRS]` 需求 Issue
- **Design**：連結 `[SDS]` 設計 Issue
- **Mitigates**：連結 `[RISK]` 風險 Issue
- **Verifies**：連結 `[TEST]` 測試 Issue
- **變更分類**：依 IEC 62304 分為 Class A / B / C

### CI/CD 工作流程 — `regulatory-artifacts.yml`

於**發佈標籤**（`v*`）或手動觸發時執行，產生 TFDA 送審文件：

| 產出物 | IEC 62304 條款 | 說明 |
|--------|---------------|------|
| `unit-test-results.xml` | §5.5 軟體單元驗證 | JUnit XML 測試結果 |
| `unit-test-report.html` | §5.5 軟體單元驗證 | 人類可讀測試報告 |
| `security-test-results.xml` | §5.7 軟體風險管理 | 安全測試結果 |
| `coverage-html/` | §5.5.3 測試覆蓋率 | 程式碼覆蓋率報告 |
| `bandit-report.json` | §5.7 風險管理 | 靜態安全分析 |
| `dependency-audit.json` | §5.7 風險管理 | 相依套件弱點掃描（pip-audit） |
| `sbom-pip-packages.json` | §5.8 軟體配置管理 | 軟體物料清單（SBOM） |
| `changelog.md` | §5.8.4 變更歷史 | Git 提交紀錄 |
| `traceability-matrix.md` | §5.1.1 追溯性 | 從 GitHub Issues 產生的需求追溯矩陣 |
| `validation-summary.md` | — | 總體驗證摘要（含法規引用） |

產出物保留 **約 7 年**（2555 天），符合 TFDA 紀錄保存要求。

### 腳本工具

| 腳本 | 用途 |
|------|------|
| `scripts/create_regulatory_issues.py` | 批次建立 SRS/SDS/RISK/TC GitHub Issues 及標籤。用法：`python scripts/create_regulatory_issues.py [--dry-run]` |
| `scripts/setup-regulatory-labels.sh` | 建立法規分類用 GitHub 標籤 |
| `scripts/add_pytest_markers.py` | 為測試檔案加入 `@pytest.mark.requirement` / `@pytest.mark.risk` 標記 |

### GitHub 法規分類標籤

| 標籤 | 顏色 | IEC 62304 對應 |
|------|------|---------------|
| `requirement` | 藍色 | §5.2 軟體需求分析 |
| `design` | 青色 | §5.3 軟體設計 |
| `risk` | 紅色 | ISO 14971 風險分析 |
| `test` | 綠色 | §5.5 軟體驗證 |
| `verification` | 紫色 | §5.5 驗證項目 |
| `class-A` | 淺藍 | 無傷害可能 |
| `class-B` | 黃色 | 非嚴重傷害可能 |
| `class-C` | 紅色 | 死亡或嚴重傷害可能 |

### 關鍵報告

- `reports/test-traceability.json` / `.md` — 測試對需求的追溯對應
- `reports/regulatory-issue-mapping.json` — SRS/SDS/RISK/TC ID 與 GitHub Issue 編號的對應

### 開發規範

1. **每個功能／修復**應追溯至 `[SRS]` 需求 Issue
2. **PR 必須連結**需求／設計／風險／測試 Issue（透過 PR 範本）
3. **新增測試**應包含 `@pytest.mark.requirement("SRS-XXX")` 及／或 `@pytest.mark.risk("RISK-XXX")`
4. **禁止硬編碼**臨床參數 — 所有數值來自 `config/cdss_config.json`
5. **安全關鍵變更**（Class C：分數計算、風險分類、臨床狀態偵測）需執行 golden dataset 驗證（`tests/verify_precise_hbr.py`）

## Important Notes

- The `.env` file is in `.gitignore` but exists locally - never commit secrets
- `APP.py` (uppercase) is the entry point, not `app.py`
- CDS Hooks endpoints are CORS-enabled for all origins (per CDS Hooks spec requirement)
- `get_precise_hbr_display_info()` returns a **dict** (from `RiskClassifierService`) with keys: `score`, `risk_category`, `score_range`, `bleeding_risk_percent`, `color_class`, `full_label`, `recommendation`
- `fhir_data_service.py` is a facade - when modifying service logic, edit the actual service class, not the facade wrappers
