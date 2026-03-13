"""
Pytest plugin for IEC 62304 regulatory traceability.

Collects @pytest.mark.requirement, @pytest.mark.risk, and @pytest.mark.design
markers and generates a traceability report after test execution.

Enforcement:
    When --enforce-regulatory-markers is passed, the plugin will FAIL the
    test session if any test function lacks at least one regulatory marker
    (requirement, risk, or design). This is used in CI to block PRs with
    untraced tests.

Usage in tests:
    @pytest.mark.requirement("SRS-001")
    @pytest.mark.risk("RISK-003")
    def test_score_calculation():
        ...

CI usage:
    pytest --enforce-regulatory-markers tests/
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

REGULATORY_MARKERS = ("requirement", "risk", "design")


def pytest_addoption(parser):
    parser.addoption(
        "--enforce-regulatory-markers",
        action="store_true",
        default=False,
        help="Fail the test session if any test lacks regulatory traceability markers "
             "(requirement, risk, or design). Used in CI to enforce IEC 62304 compliance.",
    )


def pytest_configure(config):
    config._regulatory_results = []
    config._regulatory_untraced = []


def pytest_runtest_makereport(item, call):
    if call.when != "call":
        return

    traces = {}
    for marker_name in REGULATORY_MARKERS:
        marker = item.get_closest_marker(marker_name)
        if marker and marker.args:
            traces[marker_name] = list(marker.args)

    if traces:
        item.config._regulatory_results.append({
            "test": item.nodeid,
            "outcome": "passed" if call.excinfo is None else "failed",
            "traces": traces,
        })
    else:
        item.config._regulatory_untraced.append(item.nodeid)


def pytest_sessionfinish(session, exitstatus):
    results = getattr(session.config, "_regulatory_results", [])
    untraced = getattr(session.config, "_regulatory_untraced", [])

    total_tests = len(results) + len(untraced)
    if total_tests == 0:
        return

    coverage_pct = (len(results) / total_tests * 100) if total_tests > 0 else 0

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # --- JSON report ---
    report = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total_tests": total_tests,
        "total_traced_tests": len(results),
        "total_untraced_tests": len(untraced),
        "traceability_coverage_pct": round(coverage_pct, 1),
        "passed": sum(1 for r in results if r["outcome"] == "passed"),
        "failed": sum(1 for r in results if r["outcome"] == "failed"),
        "traceability": results,
        "untraced_tests": untraced,
    }
    (reports_dir / "test-traceability.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )

    # --- Markdown report ---
    lines = [
        "# Test Traceability Report (IEC 62304)",
        f"Generated: {report['generated']}",
        "",
        "## Summary",
        f"- Total tests: {total_tests}",
        f"- Traced tests: {len(results)} ({coverage_pct:.1f}%)",
        f"- **Untraced tests: {len(untraced)}**",
        f"- Passed: {report['passed']}, Failed: {report['failed']}",
        "",
        "## Traced Tests",
        "",
        "| Test | Result | Requirements | Risks | Design |",
        "|------|--------|-------------|-------|--------|",
    ]
    for r in results:
        t = r["traces"]
        lines.append(
            f"| `{r['test']}` "
            f"| {r['outcome']} "
            f"| {', '.join(t.get('requirement', ['-']))} "
            f"| {', '.join(t.get('risk', ['-']))} "
            f"| {', '.join(t.get('design', ['-']))} |"
        )

    if untraced:
        lines.extend([
            "",
            "## Untraced Tests (Missing Regulatory Markers)",
            "",
            "The following tests lack `@pytest.mark.requirement`, `@pytest.mark.risk`, "
            "or `@pytest.mark.design` markers and cannot be traced to requirements.",
            "",
        ])
        for nodeid in untraced:
            lines.append(f"- `{nodeid}`")

    (reports_dir / "test-traceability.md").write_text("\n".join(lines))

    # --- Enforcement ---
    if session.config.getoption("enforce_regulatory_markers", default=False) and untraced:
        # Print to terminal for visibility
        print(f"\n{'='*70}")
        print(f"REGULATORY COMPLIANCE FAILURE: {len(untraced)} test(s) missing markers")
        print(f"{'='*70}")
        print(f"Traceability coverage: {coverage_pct:.1f}% ({len(results)}/{total_tests})")
        print(f"\nUntraced tests:")
        for nodeid in untraced:
            print(f"  - {nodeid}")
        print(f"\nAdd @pytest.mark.requirement('SRS-XXX'), @pytest.mark.risk('RISK-XXX'),")
        print(f"or @pytest.mark.design('SDS-XXX') to each test.")
        print(f"{'='*70}\n")
        session.exitstatus = 1
