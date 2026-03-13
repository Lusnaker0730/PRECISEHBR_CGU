# Test Traceability Report (IEC 62304)
Generated: 2026-03-13T05:05:19.057885+00:00

## Summary
- Total tests: 32
- Traced tests: 32 (100.0%)
- **Untraced tests: 0**
- Passed: 32, Failed: 0

## Traced Tests

| Test | Result | Requirements | Risks | Design |
|------|--------|-------------|-------|--------|
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_low_risk` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_moderate_risk` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_high_risk` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_boundary_score_23` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_boundary_score_27` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_zero_score` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_very_high_score` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskPercentage::test_bleeding_risk_low_score` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskPercentage::test_bleeding_risk_moderate_score` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskPercentage::test_bleeding_risk_high_score` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskPercentage::test_bleeding_risk_zero_score` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskPercentage::test_bleeding_risk_returns_valid_format` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestColorCoding::test_color_for_low_risk` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestColorCoding::test_color_for_moderate_risk` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestColorCoding::test_color_for_high_risk` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskCategoryInfo::test_category_info_includes_percentage` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskCategoryInfo::test_category_info_includes_score_range` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskCategoryInfo::test_category_info_consistency` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestEdgeCases::test_negative_score` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestEdgeCases::test_very_large_score` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestEdgeCases::test_float_score` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestEdgeCases::test_string_score` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_22_not_hbr` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_23_hbr` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_26_hbr` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_27_very_high_hbr` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskFormula::test_bleeding_risk_increases_with_score` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskFormula::test_bleeding_risk_reasonable_range` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestSingletonPattern::test_singleton_instance` | passed | SRS-002 | - | - |
| `tests/test_risk_classifier.py::TestReturnValueStructure::test_classify_risk_returns_dict` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestReturnValueStructure::test_classify_risk_has_required_keys` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestReturnValueStructure::test_bleeding_risk_percentage_type` | passed | SRS-002 | - | SDS-002 |