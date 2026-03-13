# Pull Request

## Description

<!-- Provide a brief description of the changes in this PR -->

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🔧 Configuration change
- [ ] 🧪 Test update
- [ ] ♻️ Code refactoring
- [ ] 🎨 UI/UX improvement
- [ ] ⚡ Performance improvement
- [ ] 🔒 Security fix

## Regulatory Traceability (IEC 62304 / ISO 14971)

<!-- REQUIRED for TFDA compliance. Link ALL related issues. -->

### Requirements Implemented
<!-- Link to [SRS] issues -->
- Implements: #

### Design Specifications
<!-- Link to [SDS] issues -->
- Design: #

### Risks Mitigated
<!-- Link to [RISK] issues if this PR implements a risk control -->
- Mitigates: #

### Test Cases
<!-- Link to [TEST] issues verified by this PR -->
- Verifies: #

### Change Classification (IEC 62304)
- [ ] Class A change - No impact on safety
- [ ] Class B change - Could cause non-serious injury
- [ ] Class C change - Could cause serious injury or death

> **⚠️ Class C 變更提醒：** 若本 PR 修改了以下檔案，屬於 Class C 變更，`clinical-validation.yml` 會自動觸發 Golden Dataset 驗證，此 check 必須通過才能合併：
> - `config/cdss_config.json`（臨床參數：LOINC、SNOMED、計分權重）
> - `services/precise_hbr_calculator.py`（分數計算核心）
> - `services/risk_classifier.py`（風險分類閾值）
> - `services/condition_checker.py`（臨床狀態偵測）
> - `services/unit_conversion_service.py`（實驗室值轉換/eGFR）

## Related Issues

<!-- Link to related issues using #issue_number -->

Fixes #
Related to #

## Changes Made

<!-- List the main changes made in this PR -->

- 
- 
- 

## Testing

<!-- Describe the tests you ran to verify your changes -->

### Test Environment
- [ ] Local development
- [ ] Staging environment
- [ ] Docker container

### Tests Performed
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Security scan passed
- [ ] Performance testing (if applicable)

### Test Commands
```bash
# Commands used to test
pytest tests/ -v
```

## Screenshots/Recordings

<!-- If applicable, add screenshots or recordings to help explain your changes -->

## Checklist

<!-- Mark completed items with an "x" -->

### Code Quality
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings or errors
- [ ] Code passes linting checks (flake8, pylint)
- [ ] Code is properly formatted (black)

### Testing
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I have tested on multiple browsers (if UI changes)
- [ ] I have tested with different screen sizes (if UI changes)

### Documentation
- [ ] I have updated the documentation accordingly
- [ ] I have updated the README if needed
- [ ] I have added/updated docstrings
- [ ] I have updated configuration examples if needed

### Security
- [ ] I have not introduced any security vulnerabilities
- [ ] I have not committed any secrets or sensitive data
- [ ] Security scan (Bandit) passes
- [ ] Dependency vulnerabilities checked (pip-audit)

### HIPAA/Compliance (if applicable)
- [ ] Changes comply with HIPAA requirements
- [ ] Audit logging is implemented for ePHI access
- [ ] No PHI is logged inappropriately
- [ ] Patient data handling follows compliance guidelines

### Deployment
- [ ] This change requires a deployment guide update
- [ ] Environment variables documented
- [ ] Database migrations included (if applicable)
- [ ] Backward compatible with existing deployments

## Deployment Notes

<!-- Any special instructions for deploying this change -->

### Environment Variables
<!-- List any new or changed environment variables -->

### Configuration Changes
<!-- List any configuration file changes -->

### Migration Steps
<!-- If manual steps are needed for deployment, list them here -->

1. 
2. 
3. 

## Performance Impact

<!-- Describe any performance implications -->

- [ ] No performance impact
- [ ] Improved performance
- [ ] Potential performance impact (explain below)

## Breaking Changes

<!-- If this introduces breaking changes, describe them and migration steps -->

## Additional Notes

<!-- Any additional information that reviewers should know -->

---

## Reviewer Checklist

<!-- For reviewers -->

- [ ] Code review completed
- [ ] Tests reviewed and passing
- [ ] Documentation reviewed
- [ ] Security implications considered
- [ ] Performance implications considered
- [ ] HIPAA compliance verified (if applicable)
- [ ] Ready to merge

---

## Post-Merge Tasks

<!-- Tasks to complete after merging -->

- [ ] Update changelog
- [ ] Create release notes (if applicable)
- [ ] Notify stakeholders
- [ ] Update project board
- [ ] Monitor deployment logs

---

**By submitting this PR, I confirm that:**
- I have read and followed the contributing guidelines
- My code adheres to the project's code of conduct
- I understand this code will be used in a healthcare application and must meet high quality and security standards

