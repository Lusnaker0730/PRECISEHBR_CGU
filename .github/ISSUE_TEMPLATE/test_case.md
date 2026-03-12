---
name: "Test Case (V&V)"
about: "IEC 62304 - Verification & Validation test case"
title: "[TEST] "
labels: "test, verification"
assignees: ''
---

## Test ID
<!-- Format: TC-XXX (e.g., TC-001) -->
**ID**: TC-

## Test Level
- [ ] Unit Test
- [ ] Integration Test
- [ ] System Test (E2E)
- [ ] Performance Test
- [ ] Security Test

## Traces to
- Requirement: # <!-- SRS issue -->
- Design: # <!-- SDS issue -->
- Risk Control: # <!-- RISK issue, if testing a mitigation -->

## Preconditions
<!-- What must be true before the test can execute? -->

1.

## Test Steps
<!-- Detailed, reproducible steps -->

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |

## Test Data
<!-- Specific data values used -->

## Pass/Fail Criteria
<!-- Unambiguous criteria -->

## Automated Test Location
<!-- Path to the pytest test function that implements this test case -->
**File**: `tests/`
**Function**: `test_`

## Test Execution Record
<!-- Filled in after execution - can reference CI run -->
- **Date**:
- **Tester**:
- **CI Run**: <!-- Link to GitHub Actions run -->
- **Result**: Pass / Fail
- **Evidence**: <!-- Link to test output/screenshot -->
