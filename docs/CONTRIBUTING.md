# Contributing to PRECISE-HBR SMART on FHIR Application

Thank you for your interest in contributing to the PRECISE-HBR project! This document provides guidelines for contributing to this healthcare application.

## 📋 Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Security Guidelines](#security-guidelines)
7. [Pull Request Process](#pull-request-process)
8. [Healthcare Compliance](#healthcare-compliance)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, gender identity, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards others

**Unacceptable behavior includes:**
- Harassment, discrimination, or offensive comments
- Publishing others' private information
- Trolling or insulting comments
- Other unprofessional conduct

---

## Getting Started

### Prerequisites

```bash
# Required
- Python 3.11+
- Git
- Docker (optional)

# Recommended
- Google Cloud SDK (for deployment)
- VS Code or PyCharm
```

### Setting Up Development Environment

1. **Fork and Clone**

```bash
git clone https://github.com/[your-username]/smart_fhir_app.git
cd smart_fhir_app
```

2. **Create Virtual Environment**

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install Dependencies**

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available
pip install pytest pytest-cov flake8 black pylint
```

4. **Set Up Environment Variables**

```bash
cp local.env.template .env
# Edit .env with your configuration
```

5. **Run Tests**

```bash
pytest tests/ -v
```

---

## Development Workflow

### Branch Strategy

- `main` - Production-ready code
- `PRECISE-HBR` - Staging/development branch
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Emergency production fixes

### Creating a Feature Branch

```bash
# Start from PRECISE-HBR branch
git checkout PRECISE-HBR
git pull origin PRECISE-HBR

# Create feature branch
git checkout -b feature/your-feature-name
```

### Making Changes

1. **Write code** following our coding standards
2. **Add tests** for new functionality
3. **Update documentation** as needed
4. **Run tests** locally
5. **Commit changes** with clear messages

```bash
# Run tests
pytest tests/ -v

# Check code quality
black .
flake8 .
pylint *.py

# Commit
git add .
git commit -m "feat: add new HBR criterion evaluation"
```

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `security`: Security improvements
- `perf`: Performance improvements

**Examples:**
```bash
feat(fhir): add support for Observation filtering
fix(auth): resolve OAuth callback timeout issue
docs(readme): update installation instructions
security(api): implement rate limiting
```

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

- **Line length**: 120 characters max (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Single quotes for strings (unless containing single quotes)
- **Imports**: Organized in groups (stdlib, third-party, local)

### Code Formatting

**Use Black for automatic formatting:**

```bash
black .
```

**Configuration** (in `pyproject.toml`):
```toml
[tool.black]
line-length = 120
target-version = ['py311']
```

### Linting

**Run flake8:**

```bash
flake8 . --max-line-length=120 --exclude=venv,env
```

**Run pylint:**

```bash
pylint *.py --max-line-length=120
```

### Documentation

**Docstring Format (Google Style):**

```python
def calculate_hbr_score(major_criteria, minor_criteria):
    """Calculate PRECISE-HBR risk score.
    
    Args:
        major_criteria (list): List of major criterion evaluations
        minor_criteria (list): List of minor criterion evaluations
        
    Returns:
        dict: Risk assessment with following keys:
            - is_high_risk (bool): Whether patient is high bleeding risk
            - major_count (int): Number of major criteria met
            - minor_count (int): Number of minor criteria met
            - recommendation (str): Clinical recommendation
            
    Raises:
        ValueError: If criteria lists are malformed
        
    Example:
        >>> major = [{'met': True}, {'met': False}]
        >>> minor = [{'met': True}, {'met': True}]
        >>> calculate_hbr_score(major, minor)
        {'is_high_risk': True, 'major_count': 1, 'minor_count': 2}
    """
    # Implementation
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_app_basic.py        # Basic app tests
├── test_fhir_service.py     # FHIR functionality
├── test_security.py         # Security tests
├── test_audit_logging.py    # Audit logging
└── test_ccd_export.py       # CCD export
```

### Writing Tests

**Test naming convention:**

```python
def test_[unit]_[scenario]_[expected_result]():
    """Test description."""
    # Arrange
    setup_data = create_test_data()
    
    # Act
    result = function_under_test(setup_data)
    
    # Assert
    assert result == expected_value
```

**Example:**

```python
def test_age_criterion_evaluation_patient_over_75_returns_met():
    """Test age criterion evaluates as met for patient over 75."""
    # Arrange
    birth_date = '1940-01-01'
    
    # Act
    result = evaluate_age_criterion(birth_date)
    
    # Assert
    assert result['met'] is True
    assert result['age'] >= 75
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_app_basic.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test
pytest tests/test_app_basic.py::test_health_endpoint -v

# Run with markers
pytest tests/ -m security -v
```

### Test Coverage

- Aim for **>80%** code coverage
- All new code must include tests
- Critical paths require **100%** coverage

```bash
# Generate coverage report
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

---

## Security Guidelines

### Security Requirements

1. **Never commit secrets**
   - No API keys, passwords, tokens in code
   - Use environment variables or Secret Manager

2. **Input validation**
   - Validate all user inputs
   - Sanitize data before processing
   - Use parameterized queries

3. **Authentication & Authorization**
   - Implement proper SMART on FHIR OAuth
   - Validate JWT tokens
   - Check user permissions

4. **Data protection**
   - Encrypt sensitive data
   - Use HTTPS only
   - Implement audit logging for PHI access

### Security Testing

```bash
# Run Bandit security scan
bandit -r . -ll --exclude venv,env

# Check dependencies
pip-audit

# Run security tests
pytest tests/test_security.py -v
```

### Reporting Security Issues

**DO NOT** create public issues for security vulnerabilities.

Instead, email: [security contact]

---

## Pull Request Process

### Before Submitting

**Checklist:**
- [ ] Code follows style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Security scan passes
- [ ] HIPAA compliance verified
- [ ] Commit messages follow convention
- [ ] Branch is up-to-date with PRECISE-HBR

### Submitting Pull Request

1. **Push your branch**

```bash
git push origin feature/your-feature-name
```

2. **Create Pull Request**

- Go to GitHub repository
- Click "New Pull Request"
- Select your branch
- Fill out PR template completely
- Request reviewers

3. **PR Title Format**

```
<type>: <description>

Examples:
feat: add medication reconciliation support
fix: resolve OAuth timeout in Cerner integration
docs: update deployment guide for GCP
```

4. **PR Description**

Use the PR template to provide:
- Clear description of changes
- Related issues
- Testing performed
- Screenshots (if UI changes)
- Deployment notes
- Breaking changes (if any)

### Review Process

1. **Automated checks** must pass:
   - Code quality checks
   - Security scan
   - Tests
   - Build

2. **Code review** by at least one maintainer

3. **Approval** required before merge

4. **CI/CD** pipeline runs after merge

### After Merge

- Delete feature branch
- Update related issues
- Monitor deployment
- Update project board

---

## Healthcare Compliance

### HIPAA Compliance

This application handles Protected Health Information (PHI). All contributors must:

1. **Understand HIPAA requirements**
   - Access controls
   - Audit logging
   - Data encryption
   - Minimum necessary principle

2. **Follow PHI handling guidelines**
   - No PHI in logs (use patient IDs only)
   - No PHI in test data (use synthetic data)
   - Audit all PHI access
   - Secure data transmission

3. **Implement required safeguards**
   - Authentication and authorization
   - Encryption at rest and in transit
   - Audit trails
   - Access controls

### SMART on FHIR Compliance

- Follow [SMART App Launch](http://hl7.org/fhir/smart-app-launch/) specification
- Implement proper OAuth 2.0 flows
- Request minimum necessary FHIR scopes
- Validate FHIR resources

### Clinical Safety

- This is a **clinical decision support tool**
- Changes must not compromise patient safety
- Clinical accuracy is paramount
- Document clinical decision logic
- Include proper disclaimers

---

## Questions or Need Help?

- 📧 Email: [maintainer email]
- 💬 Discussions: [GitHub Discussions link]
- 📚 Documentation: [Wiki or docs link]
- 🐛 Issues: [GitHub Issues link]

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

## Acknowledgments

Thank you for contributing to improving cardiovascular care through better bleeding risk assessment!

---

**Remember:** This application is used in healthcare settings. Quality, security, and patient safety are our top priorities. When in doubt, ask questions before proceeding.

