from __future__ import annotations

import json
from pathlib import Path

from src.analysis.reporting import generate_html_reports
from src.analysis.seo_validation import validate_seo_outputs


def test_generate_seo_reports_and_validate(tmp_path: Path) -> None:
    root = tmp_path
    reports = root / "reports"
    status = root / "status"
    data = root / "data" / "research"
    (root / "data").mkdir(parents=True)
    data.mkdir(parents=True)
    status.mkdir(parents=True)

    (reports / "statistical_summary.json").parent.mkdir(parents=True, exist_ok=True)
    (reports / "statistical_summary.json").write_text(json.dumps({"dataset_version": "v0.1.0", "metrics": {}}), encoding="utf-8")
    (reports / "system-health.json").write_text(json.dumps({"health": "HEALTHY"}), encoding="utf-8")
    (reports / "live-data-status.json").write_text(json.dumps({"dataset_version": "v0.1.0"}), encoding="utf-8")
    (status / "system-status.json").write_text(json.dumps({"status": "HEALTHY", "dataset_version": "v0.1.0"}), encoding="utf-8")
    (root / "data" / "source_registry.json").write_text("[]", encoding="utf-8")
    (root / "data" / "source_assessment.json").write_text("[]", encoding="utf-8")
    (data / "site_config.json").write_text(
        json.dumps({"site_url": "https://example.github.io/project/", "site_name": "Project", "publisher_name": "Project"}),
        encoding="utf-8",
    )

    generate_html_reports(reports)
    errors = validate_seo_outputs(reports, "https://example.github.io/project/")

    assert not errors
    assert (reports / "robots.txt").exists()
    assert (reports / "sitemap.xml").exists()
    assert (reports / "404.html").exists()
