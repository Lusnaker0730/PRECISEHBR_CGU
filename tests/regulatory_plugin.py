"""
Pytest plugin for IEC 62304 regulatory traceability.

Collects @pytest.mark.requirement, @pytest.mark.risk, and @pytest.mark.design
markers and generates a traceability report after test execution.

Usage in tests:
    @pytest.mark.requirement("SRS-001")
    @pytest.mark.risk("RISK-003")
    def test_score_calculation():
        ...
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def pytest_configure(config):
    config._regulatory_results = []


def pytest_runtest_makereport(item, call):
    if call.when != "call":
        return

    traces = {}
    for marker_name in ("requirement", "risk", "design"):
        marker = item.get_closest_marker(marker_name)
        if marker and marker.args:
            traces[marker_name] = list(marker.args)

    if traces:
        item.config._regulatory_results.append({
            "test": item.nodeid,
            "outcome": "passed" if call.excinfo is None else "failed",
            "traces": traces,
        })


def pytest_sessionfinish(session, exitstatus):
    results = getattr(session.config, "_regulatory_results", [])
    if not results:
        return

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # JSON for machine processing
    report = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total_traced_tests": len(results),
        "passed": sum(1 for r in results if r["outcome"] == "passed"),
        "failed": sum(1 for r in results if r["outcome"] == "failed"),
        "traceability": results,
    }
    (reports_dir / "test-traceability.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )

    # Markdown for human review
    lines = [
        "# Test Traceability Report (IEC 62304)",
        f"Generated: {report['generated']}",
        f"Total traced tests: {report['total_traced_tests']} "
        f"(passed: {report['passed']}, failed: {report['failed']})",
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

    (reports_dir / "test-traceability.md").write_text("\n".join(lines))
