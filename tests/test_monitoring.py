import json
from pathlib import Path

from src.monitoring.engine import run_monitoring_cycle


def test_monitoring_cycle_runs_with_fallback(tmp_path: Path) -> None:
    data = tmp_path / "data"
    reports = tmp_path / "reports"
    (data / "research").mkdir(parents=True)
    (data / "review").mkdir(parents=True)
    registry = [
        {
            "source_id": "gofundme-fundraiser-page",
            "canonical_url": "NOT_AVAILABLE",
            "source_type": "fundraiser",
            "publisher": "GoFundMe",
            "access_method": "manual evidence capture",
            "authorization_status": "review_required",
            "reliability": "A",
            "monitoring_enabled": True,
            "polling_frequency": "daily",
            "parser_version": "1.0.0",
            "error_count": 0,
        }
    ]
    (data / "source_registry.json").write_text(json.dumps(registry), encoding="utf-8")

    summary = run_monitoring_cycle(data, reports)

    assert summary["sources_checked"] == 1
    assert (reports / "system-health.json").exists()
    assert (data / "events" / "events.jsonl").exists()
