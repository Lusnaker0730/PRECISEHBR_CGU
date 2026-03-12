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

## Important Notes

- The `.env` file is in `.gitignore` but exists locally - never commit secrets
- `APP.py` (uppercase) is the entry point, not `app.py`
- CDS Hooks endpoints are CORS-enabled for all origins (per CDS Hooks spec requirement)
- `get_precise_hbr_display_info()` returns a **dict** (from `RiskClassifierService`) with keys: `score`, `risk_category`, `score_range`, `bleeding_risk_percent`, `color_class`, `full_label`, `recommendation`
- `fhir_data_service.py` is a facade - when modifying service logic, edit the actual service class, not the facade wrappers
