# PRECISE-HBR Project Structure

## 📂 Directory Organization

```
smart_fhir_app/
├── 🏗️ Core Application Files
│   ├── APP.py                      # Main Flask application
│   ├── config.py                   # Configuration management
│   ├── auth.py                     # Authentication & OAuth
│   ├── hooks.py                    # SMART on FHIR hooks
│   ├── views.py                    # Additional view routes
│   ├── fhir_data_service.py       # FHIR data operations
│   ├── ccd_generator.py           # CCD export functionality
│   ├── audit_logger.py            # HIPAA audit logging
│   ├── logging_filter.py          # Custom logging filters
│   └── tradeoff_analysis_routes.py # Clinical decision routes
│
├── 📋 Configuration Files
│   ├── requirements.txt           # Python dependencies
│   ├── app.yaml                   # Google App Engine config
│   ├── Dockerfile                 # Docker container config
│   ├── docker-compose.yml         # Docker Compose config
│   ├── deploy.yaml                # Deployment configuration
│   ├── pytest.ini                 # Pytest configuration
│   ├── .coveragerc                # Coverage configuration
│   ├── .gitignore                 # Git ignore rules
│   ├── .dockerignore              # Docker ignore rules
│   ├── cds-services.json          # CDS Hooks configuration
│   ├── cdss_config.json           # CDSS configuration
│   ├── local.env.template         # Local environment template
│   └── production.env.template    # Production environment template
│
├── 📁 Static Resources
│   └── static/
│       ├── css/                   # Stylesheets
│       ├── js/                    # JavaScript files
│       ├── images/                # Image assets
│       ├── favicon.ico            # Site favicon
│       ├── logo.svg               # Application logo
│       └── smart_embed_detection.js # SMART detection
│
├── 🎨 Templates
│   └── templates/
│       ├── index.html             # Main page
│       ├── launch.html            # SMART launch page
│       ├── callback.html          # OAuth callback
│       ├── results.html           # Assessment results
│       ├── error.html             # Error page
│       ├── disclaimer.html        # Medical disclaimer
│       └── ... (other templates)
│
├── 🧪 Tests
│   └── tests/
│       ├── __init__.py            # Test package
│       ├── conftest.py            # Pytest fixtures
│       ├── test_app_basic.py      # Basic app tests
│       ├── test_fhir_service.py   # FHIR service tests
│       ├── test_security.py       # Security tests
│       ├── test_audit_logging.py  # Audit logging tests
│       └── test_ccd_export.py     # CCD export tests
│
├── 🔄 CI/CD Configuration
│   └── .github/
│       ├── workflows/
│       │   ├── ci.yml             # Continuous Integration
│       │   ├── cd.yml             # Continuous Deployment
│       │   ├── docker-build.yml   # Docker build & push
│       │   ├── security-scan.yml  # Security scanning
│       │   └── README.md          # Workflows documentation
│       ├── PULL_REQUEST_TEMPLATE.md # PR template
│       └── ISSUE_TEMPLATE/
│           ├── bug_report.md      # Bug report template
│           └── feature_request.md # Feature request template
│
├── 📚 Documentation
│   ├── docs/
│   │   ├── README.md              # Documentation index
│   │   ├── implementation/        # Implementation docs
│   │   ├── compliance/            # Compliance docs
│   │   ├── deployment/            # Deployment docs
│   │   └── guides/                # User guides
│   ├── CI_CD_SETUP_GUIDE.md      # Complete CI/CD setup
│   ├── README_CI_CD.md           # CI/CD overview
│   ├── CONTRIBUTING.md           # Contributing guidelines
│   ├── PRECISE-HBR.md            # PRECISE-HBR criteria
│   ├── PRECISE-HBR.pdf           # PRECISE-HBR paper
│   └── ARC.pdf                   # ARC-HBR reference
│
├── 🔬 FHIR Resources
│   └── fhir_resources/
│       ├── README.md              # FHIR resources index
│       └── valuesets/             # FHIR ValueSets
│           ├── bleeding_diathesis_valueset.json
│           ├── cancer_snomed_valueset.json
│           ├── portal_hypertension_valueset.json
│           ├── prior_bleeding_valueset.json
│           ├── ischemic_stroke_mod_severe_valueset.json
│           └── ... (other valuesets)
│
└── 🔐 Build Artifacts (Ignored by Git)
    ├── __pycache__/               # Python bytecode
    ├── htmlcov/                   # Coverage reports
    └── .pytest_cache/             # Pytest cache
```

## 📦 Key Components

### Core Application
- **Flask Backend**: RESTful API and server-side rendering
- **SMART on FHIR**: OAuth 2.0 integration with EHR systems
- **FHIR Client**: R4 resource querying and manipulation
- **CDS Hooks**: Clinical decision support integration

### Features
- ✅ PRECISE-HBR risk assessment
- ✅ SMART on FHIR launch
- ✅ CCD export (ONC compliance)
- ✅ Audit logging (HIPAA compliance)
- ✅ Multi-EHR support (Cerner, Epic, etc.)
- ✅ Clinical decision support

### DevOps
- ✅ Automated CI/CD with GitHub Actions
- ✅ Docker containerization
- ✅ Google App Engine deployment
- ✅ Security scanning
- ✅ Automated testing

## 🚀 Quick Start

### Local Development
```bash
# Clone repository
git clone https://github.com/Lusnaker0730/smart_fhir_app.git
cd smart_fhir_app

# Set up environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp local.env.template .env
# Edit .env with your settings

# Run application
python APP.py
```

### Run Tests
```bash
pytest tests/ -v --cov=.
```

### Docker
```bash
docker build -t smart-fhir-app .
docker run -p 8080:8080 smart-fhir-app
```

## 📖 Documentation

- **Getting Started**: See `CI_CD_SETUP_GUIDE.md`
- **API Reference**: See inline code documentation
- **Deployment**: See `docs/deployment/`
- **Contributing**: See `CONTRIBUTING.md`
- **Compliance**: See `docs/compliance/`

## 🔒 Security

- All PHI access is audited
- OAuth 2.0 authentication
- HTTPS required in production
- Regular security scans
- Dependency vulnerability checks

## 📝 License

[Add license information]

## 👥 Team

See `CONTRIBUTING.md` for team structure and contact information.

---

**Project Version:** 1.0.0  
**Last Updated:** October 2025

