from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def generate_html_reports(reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    stats = _load_json(reports_dir / "statistical_summary.json", {})
    health = _load_json(reports_dir / "system-health.json", {})
    live = _load_json(reports_dir / "live-data-status.json", {})
    system = _load_json(reports_dir.parent / "status" / "system-status.json", {})
    timestamp = datetime.now(UTC).isoformat()
    dataset_version = stats.get("dataset_version", "UNKNOWN")
    coverage = stats.get("coverage", "Partially observable dataset")

    pages = {
        "fundraiser-overview.html": (
            f"<h1>Fundraiser Overview</h1><p>Generated: {timestamp}</p>"
            f"<p>Dataset version: {dataset_version}</p><p>Coverage: {coverage}</p>"
            f"<p>Automation status: {system.get('automation_status', 'UNKNOWN')}</p>"
            f"<p>Last successful run: {system.get('last_successful_run', 'UNKNOWN')}</p>"
        ),
        "donation-statistics.html": f"<h1>Donation Statistics</h1><pre>{json.dumps(stats.get('metrics', {}), indent=2)}</pre>",
        "donation-timeline.html": "<h1>Donation Timeline</h1><p>Timeline is based on observable records only.</p>",
        "coverage.html": f"<h1>Coverage</h1><pre>{json.dumps(live, indent=2)}</pre>",
        "data-quality.html": "<h1>Data Quality</h1><p>See data_quality_report.json</p>",
        "sources.html": "<h1>Sources</h1><p>See data/source_registry.json</p>",
        "changelog.html": "<h1>Changelog</h1><p>See CHANGELOG.md</p>",
        "dashboard.html": (
            "<h1>Public Research Dashboard</h1>"
            f"<p>SYSTEM STATUS: {system.get('status', 'UNKNOWN')}</p>"
            f"<p>AUTOMATION STATUS: {system.get('automation_status', 'UNKNOWN')}</p>"
            f"<p>Data pipeline: {system.get('data_pipeline', 'UNKNOWN')}</p>"
            f"<p>Last successful automation run: {system.get('last_successful_run', 'UNKNOWN')}</p>"
            f"<p>Expected next run: {system.get('expected_next_run', 'UNKNOWN')}</p>"
            f"<p>Sources healthy/degraded/not automated: {system.get('sources_healthy', 'UNKNOWN')}/{system.get('sources_degraded', 'UNKNOWN')}/{system.get('sources_not_automated', 'UNKNOWN')}</p>"
            f"<p>Dataset size: {system.get('dataset_size', 'UNKNOWN')}</p>"
            f"<p>Historical observations: {system.get('historical_observation_count', 'UNKNOWN')}</p>"
            "<h2>Overview</h2><p>Current fundraiser and dataset status.</p>"
            "<h2>Donation Activity</h2><p>Observable donation statistics only.</p>"
            "<h2>Timeline</h2><p>Historical changes and public events.</p>"
            "<h2>Publicly Displayed Donations</h2><p>Publication-filtered records.</p>"
            "<h2>Organizations</h2><p>Conservatively verified organizations only.</p>"
            "<h2>Sources</h2><p>Source inventory and reliability.</p>"
            "<h2>Coverage</h2><p>Observed vs reported visibility.</p>"
            "<h2>Data Quality</h2><p>Validation results.</p>"
            "<h2>Community Research</h2><p>Accepted submissions and leads.</p>"
            "<h2>Methodology</h2><p>How updates are produced.</p>"
            "<h2>Changelog</h2><p>Dataset evolution and auditability.</p>"
        ),
    }
    for filename, body in pages.items():
        (reports_dir / filename).write_text(
            (
                "<html><body>"
                f"{body}"
                f"<p>Methodology version: v0.1.0</p>"
                f"<p>System health: {health.get('health', 'UNKNOWN')}</p>"
                "<p>Publicly observable data is not necessarily the complete donation ledger.</p>"
                "</body></html>\n"
            ),
            encoding="utf-8",
        )
    (reports_dir / "index.html").write_text((reports_dir / "dashboard.html").read_text(encoding="utf-8"), encoding="utf-8")
