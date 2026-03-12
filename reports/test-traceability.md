# Test Traceability Report (IEC 62304)
Generated: 2026-03-12T04:47:27.467610+00:00
Total traced tests: 34 (passed: 13, failed: 21)

| Test | Result | Requirements | Risks | Design |
|------|--------|-------------|-------|--------|
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case0]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case1]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case2]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case3]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case4]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case5]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case6]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case7]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case8]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case9]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case10]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case11]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case12]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case13]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case14]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case15]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case16]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case17]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case18]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case19]` | failed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_boundary_values` | failed | SRS-001 | RISK-001 | SDS-001 |
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