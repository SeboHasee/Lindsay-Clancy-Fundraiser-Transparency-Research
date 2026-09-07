from __future__ import annotations

import json
from pathlib import Path

from src.monitoring import engine
from src.sources.base import BaseSourceAdapter, SourceMetadata


class _StaticAdapter(BaseSourceAdapter):
    def __init__(self, metadata: SourceMetadata, records: list[dict]):
        super().__init__(metadata)
        self._records = records

    def discover(self) -> dict:
        return {}

    def fetch(self) -> dict:
        return {"records": self._records}

    def parse(self, raw: dict) -> dict:
        return raw

    def normalize(self, parsed: dict) -> list[dict]:
        return parsed["records"]

    def validate(self, normalized: list[dict]) -> list[str]:
        return []


class _FailingAdapter(_StaticAdapter):
    def fetch(self) -> dict:
        raise OSError("source unreachable")


def _seed_registry(path: Path) -> None:
    payload = [
        {
            "source_id": "gofundme-fundraiser-page",
            "source_name": "source",
            "canonical_url": "https://example.test",
            "source_type": "fundraiser",
            "publisher": "example",
            "access_method": "manual",
            "authorization_status": "public",
            "collection_status": "active",
            "monitoring_enabled": True,
            "polling_frequency": "daily",
            "parser_version": "1.0.0",
            "error_count": 0,
            "reliability": "A",
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")


def _setup_dirs(root: Path) -> tuple[Path, Path]:
    data = root / "data"
    reports = root / "reports"
    (data / "research").mkdir(parents=True)
    (data / "review").mkdir(parents=True)
    (data / "events").mkdir(parents=True)
    _seed_registry(data / "source_registry.json")
    (data / "research" / "automation_config.json").write_text(
        json.dumps({"scheduler_interval_hours": 24, "stale_warning_hours": 36, "stale_critical_hours": 72}),
        encoding="utf-8",
    )
    return data, reports


def test_normal_update_and_no_change_idempotent(monkeypatch, tmp_path: Path) -> None:
    data, reports = _setup_dirs(tmp_path)
    records = [
        {
            "donation_id": "d1",
            "source_id": "gofundme-fundraiser-page",
            "source_url": "https://example.test",
            "displayed_amount": "$10",
            "normalized_amount": 10.0,
            "evidence_reference": "ev1",
            "collection_timestamp": "2026-09-07T00:00:00+00:00",
        }
    ]

    monkeypatch.setattr(engine, "_build_adapter", lambda s, d: _StaticAdapter(s, records))
    first = engine.run_monitoring_cycle(data, reports)
    second = engine.run_monitoring_cycle(data, reports)

    assert first["records_added"] == 1
    assert second["records_added"] == 0
    saved = json.loads((data / "research" / "donations.json").read_text(encoding="utf-8"))
    assert len(saved) == 1


def test_source_unavailable_preserves_existing_data(monkeypatch, tmp_path: Path) -> None:
    data, reports = _setup_dirs(tmp_path)
    existing = [
        {
            "donation_id": "d1",
            "source_id": "gofundme-fundraiser-page",
            "source_url": "https://example.test",
            "displayed_amount": "$10",
            "normalized_amount": 10.0,
            "evidence_reference": "ev1",
            "collection_timestamp": "2026-09-07T00:00:00+00:00",
        }
    ]
    (data / "research" / "donations.json").write_text(json.dumps(existing), encoding="utf-8")

    monkeypatch.setattr(engine, "_build_adapter", lambda s, d: _FailingAdapter(s, []))
    summary = engine.run_monitoring_cycle(data, reports)

    preserved = json.loads((data / "research" / "donations.json").read_text(encoding="utf-8"))
    queue = json.loads((data / "review" / "queue.json").read_text(encoding="utf-8"))
    assert summary["source_health"]["degraded"] == 1
    assert len(preserved) == 1
    assert queue


def test_zero_result_guard_rejects_drop(monkeypatch, tmp_path: Path) -> None:
    data, reports = _setup_dirs(tmp_path)
    existing = [
        {
            "donation_id": f"d{i}",
            "source_id": "gofundme-fundraiser-page",
            "source_url": "https://example.test",
            "displayed_amount": "$10",
            "normalized_amount": 10.0,
            "evidence_reference": "ev",
            "collection_timestamp": "2026-09-07T00:00:00+00:00",
        }
        for i in range(101)
    ]
    (data / "research" / "donations.json").write_text(json.dumps(existing), encoding="utf-8")

    monkeypatch.setattr(engine, "_build_adapter", lambda s, d: _StaticAdapter(s, []))
    engine.run_monitoring_cycle(data, reports)

    preserved = json.loads((data / "research" / "donations.json").read_text(encoding="utf-8"))
    assert len(preserved) == 101


def test_compute_stale_status() -> None:
    status = engine.compute_automation_status(
        "2000-01-01T00:00:00+00:00",
        {"scheduler_interval_hours": 24, "stale_warning_hours": 36, "stale_critical_hours": 72},
    )
    assert status["automation_status"] == "STALE"
