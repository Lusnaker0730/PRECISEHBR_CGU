# PRECISE-HBR SMART on FHIR Application - CI/CD Documentation

[![CI Status](https://github.com/Lusnaker0730/smart_fhir_app/workflows/CI/badge.svg)](https://github.com/Lusnaker0730/smart_fhir_app/actions)
[![Security Scan](https://github.com/Lusnaker0730/smart_fhir_app/workflows/Security%20Scan/badge.svg)](https://github.com/Lusnaker0730/smart_fhir_app/actions)
[![Docker Build](https://github.com/Lusnaker0730/smart_fhir_app/workflows/Docker%20Build/badge.svg)](https://github.com/Lusnaker0730/smart_fhir_app/actions)

## 📚 Overview

This document provides an overview of the CI/CD (Continuous Integration/Continuous Deployment) pipeline for the PRECISE-HBR SMART on FHIR application.

## 🚀 Quick Links

- **[Complete Setup Guide](CI_CD_SETUP_GUIDE.md)** - Detailed step-by-step setup instructions
- **[Workflows Documentation](.github/workflows/README.md)** - GitHub Actions workflows reference
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute to the project
- **[Security Guidelines](#security)** - Security best practices

---

## 🏗️ Architecture

### CI/CD Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Developer Push                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CI Workflow (Automated)                      │
├─────────────────────────────────────────────────────────────────┤
│  ✓ Code Quality Checks (Black, flake8, pylint)                │
│  ✓ Security Scan (Bandit, pip-audit)                          │
│  ✓ Unit Tests (pytest with coverage)                          │
│  ✓ Build Verification                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
    ┌───────────────────────┐  ┌──────────────────┐
    │   Docker Build        │  │   CD Workflow    │
    │  Multi-platform       │  │   Deployment     │
    │  Push to Registry     │  │   Staging/Prod   │
    └───────────────────────┘  └──────────────────┘
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
            ┌────────────────────┐        ┌────────────────────┐
            │  Staging Env       │        │  Production Env    │
            │  (PRECISE-HBR)     │        │  (main branch)     │
            └────────────────────┘        └────────────────────┘
```

---

## 🔄 Workflows

### 1. Continuous Integration (CI)

**Triggered on:**
- Push to `main`, `PRECISE-HBR`, `PreciseDAPT`, `develop`
- Pull requests to protected branches

**Pipeline stages:**

```yaml
Code Quality → Security Scan → Tests → Build → Artifacts
```

**What it does:**
- ✅ Validates code formatting and style
- ✅ Scans for security vulnerabilities
- ✅ Runs comprehensive test suite
- ✅ Generates coverage reports
- ✅ Creates build artifacts

**Artifacts produced:**
- Code coverage reports (HTML, XML)
- Security scan results (Bandit, pip-audit)
- Build package (tar.gz)

### 2. Continuous Deployment (CD)

**Deployment targets:**

| Branch | Environment | URL | Auto-Deploy |
|--------|-------------|-----|-------------|
| `PRECISE-HBR` | Staging | `staging-smart-fhir-app.appspot.com` | ✅ Yes |
| `main` | Production | `smart-fhir-app.appspot.com` | ✅ Yes (with approval) |

**Deployment process:**

```yaml
Authentication → Backup → Deploy → Health Check → Notify
```

**Features:**
- 🔄 Automatic rollback on failure
- 🏥 Health checks after deployment
- 📊 Deployment tracking
- 🔔 Status notifications

### 3. Docker Build & Push

**Triggered on:**
- Push to `main`, `PRECISE-HBR`
- Version tags (`v*`)
- Manual trigger

**Features:**
- 🐳 Multi-platform builds (amd64, arm64)
- 🏷️ Automatic semantic versioning
- 📦 Push to GitHub Container Registry
- 🔒 Trivy security scanning
- 📋 SBOM generation

**Image tags:**
```
ghcr.io/lusnaker0730/smart_fhir_app:latest
ghcr.io/lusnaker0730/smart_fhir_app:v1.0.0
ghcr.io/lusnaker0730/smart_fhir_app:PRECISE-HBR
ghcr.io/lusnaker0730/smart_fhir_app:sha-abc1234
```

### 4. Security Scanning

**Schedule:** Daily at 2 AM UTC

**Scans performed:**
- 🔍 **Dependency vulnerabilities** (pip-audit, Safety)
- 🔐 **Code security** (Bandit)
- 🕵️ **Advanced security** (CodeQL)
- 🔑 **Secrets detection** (Gitleaks)
- 📜 **License compliance** (pip-licenses)

---

## 🛠️ Development Workflow

### Setting Up Local Environment

```bash
# 1. Clone repository
git clone https://github.com/Lusnaker0730/smart_fhir_app.git
cd smart_fhir_app

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov flake8 black pylint bandit

# 4. Set up environment
cp local.env.template .env
# Edit .env with your configuration

# 5. Run tests
pytest tests/ -v
```

### Making Changes

```bash
# 1. Create feature branch
git checkout -b feature/your-feature

# 2. Make changes and test
# ... code changes ...
pytest tests/ -v

# 3. Check code quality
black .
flake8 .
bandit -r . -ll

# 4. Commit and push
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature

# 5. Create Pull Request on GitHub
```

### Branch Strategy

```
main (production)
  │
  ├── PRECISE-HBR (staging)
  │     │
  │     ├── feature/new-criterion
  │     ├── feature/ui-improvement
  │     └── bugfix/oauth-timeout
  │
  └── hotfix/critical-security-fix
```

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_app_basic.py -v

# Run specific test
pytest tests/test_app_basic.py::test_health_endpoint -v

# Run security tests only
pytest tests/test_security.py -v
```

### Test Structure

```
tests/
├── conftest.py              # Fixtures and configuration
├── test_app_basic.py        # Basic application tests
├── test_fhir_service.py     # FHIR functionality tests
├── test_security.py         # Security tests
├── test_audit_logging.py    # Audit logging tests
└── test_ccd_export.py       # CCD export tests
```

### Coverage Requirements

- **Minimum:** 80% overall coverage
- **Critical paths:** 100% coverage
- **New code:** Must include tests

---

## 🔒 Security

### Security Measures

1. **Automated scanning**
   - Daily security scans
   - Dependency vulnerability checks
   - Secret detection in commits

2. **Code analysis**
   - Bandit for Python security issues
   - CodeQL for advanced analysis
   - Manual security reviews

3. **HIPAA compliance**
   - Audit logging for all PHI access
   - Encrypted data transmission
   - Access controls and authentication

### Running Security Scans Locally

```bash
# Bandit security scan
bandit -r . -f json -o bandit-report.json --exclude venv -ll

# Dependency audit
pip-audit --desc

# Check for secrets
# Install gitleaks: https://github.com/gitleaks/gitleaks
gitleaks detect --source . --verbose
```

### Reporting Security Issues

**⚠️ DO NOT create public issues for security vulnerabilities**

Contact security team privately at: [security contact]

---

## 📦 Deployment

### Automated Deployment

**Staging:**
```bash
# Push to PRECISE-HBR branch
git checkout PRECISE-HBR
git merge feature/your-feature
git push origin PRECISE-HBR
# → Auto-deploys to staging
```

**Production:**
```bash
# Push to main branch (requires approval)
git checkout main
git merge PRECISE-HBR
git push origin main
# → Auto-deploys to production after approval
```

### Manual Deployment

```bash
# Deploy to staging
gcloud app deploy app.yaml \
  --project=your-project-id \
  --version=staging-$(date +%Y%m%d-%H%M%S) \
  --promote

# Deploy to production
gcloud app deploy app.yaml \
  --project=your-project-id \
  --version=prod-$(date +%Y%m%d-%H%M%S) \
  --promote
```

### Rollback

```bash
# List versions
gcloud app versions list --project=your-project-id

# Rollback to previous version
gcloud app versions migrate [previous-version-id] \
  --project=your-project-id \
  --quiet
```

---

## 📊 Monitoring

### Health Checks

```bash
# Staging
curl https://staging-smart-fhir-app.appspot.com/health

# Production
curl https://smart-fhir-app.appspot.com/health
```

### View Logs

```bash
# Real-time logs
gcloud app logs tail --project=your-project-id

# Recent logs
gcloud app logs read --project=your-project-id --limit=50

# Filter by severity
gcloud app logs read --project=your-project-id \
  --filter="severity>=ERROR"
```

### GitHub Actions Status

View workflow runs:
- Go to: `https://github.com/Lusnaker0730/smart_fhir_app/actions`
- Check status of recent runs
- Download artifacts if needed

---

## 🔧 Configuration

### Required Secrets

GitHub repository secrets (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `GCP_PROJECT_ID` | Google Cloud Project ID | `smart-fhir-app-prod` |
| `GCP_SA_KEY` | Service Account JSON key | `{"type": "service_account", ...}` |

### Environment Variables

Application environment variables (in `app.yaml`):

```yaml
env_variables:
  FLASK_ENV: 'production'
  FLASK_SECRET_KEY: 'projects/${PROJECT_ID}/secrets/flask-secret-key/versions/latest'
  SMART_CLIENT_ID: 'projects/${PROJECT_ID}/secrets/smart-client-id/versions/latest'
  SMART_CLIENT_SECRET: 'projects/${PROJECT_ID}/secrets/smart-client-secret/versions/latest'
  SMART_REDIRECT_URI: 'https://smart-fhir-app.appspot.com/callback'
```

---

## 🐛 Troubleshooting

### CI Workflow Fails

**Code quality issues:**
```bash
# Fix formatting
black .

# Check linting
flake8 . --show-source
```

**Test failures:**
```bash
# Run tests with verbose output
pytest tests/ -v --tb=long

# Check specific test
pytest tests/test_file.py::test_name -v -s
```

### Deployment Fails

**Authentication error:**
- Verify `GCP_SA_KEY` is valid JSON
- Check service account permissions
- Ensure project ID is correct

**App Engine error:**
```bash
# Check app status
gcloud app describe --project=your-project-id

# View recent logs
gcloud app logs tail --project=your-project-id
```

### Docker Build Fails

```bash
# Test build locally
docker build -t test:local .

# Check with no cache
docker build --no-cache -t test:local .
```

---

## 📚 Additional Resources

### Documentation
- [CI/CD Setup Guide](CI_CD_SETUP_GUIDE.md)
- [Workflows Reference](.github/workflows/README.md)
- [Contributing Guidelines](CONTRIBUTING.md)
- [PRECISE-HBR Criteria](PRECISE-HBR.md)

### External Links
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Google App Engine](https://cloud.google.com/appengine/docs/standard/python3)
- [SMART on FHIR](http://hl7.org/fhir/smart-app-launch/)
- [Docker Documentation](https://docs.docker.com/)

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request
5. Wait for CI checks to pass
6. Request review

---

## 📝 License

[Add license information]

---

## 👥 Team

- **Project Lead:** [Name]
- **DevOps:** [Name]
- **Security:** [Name]

---

## 🆘 Support

- 📧 Email: [support email]
- 💬 Discussions: [GitHub Discussions]
- 🐛 Issues: [GitHub Issues](https://github.com/Lusnaker0730/smart_fhir_app/issues)

---

**Last Updated:** October 2025

**CI/CD Version:** 1.0.0

