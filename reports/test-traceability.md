# Test Traceability Report (IEC 62304)
Generated: 2026-03-12T06:21:03.051960+00:00
Total traced tests: 13 (passed: 13, failed: 0)

| Test | Result | Requirements | Risks | Design |
|------|--------|-------------|-------|--------|
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_low_risk` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_moderate_risk` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_high_risk` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_boundary_score_23` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_boundary_score_27` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_zero_score` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_very_high_score` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_22_not_hbr` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_23_hbr` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_26_hbr` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_27_very_high_hbr` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestBleedingRiskFormula::test_bleeding_risk_increases_with_score` | passed | SRS-002 | - | - |
| `tests/test_risk_classifier.py::TestBleedingRiskFormula::test_bleeding_risk_reasonable_range` | passed | SRS-002 | - | - |