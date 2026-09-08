from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.sources.capture_ingestion import (
    create_capture_pack,
    ingest_capture_packs,
    validate_capture_manifest,
)


def _setup_data_root(root: Path) -> Path:
    data = root / "data"
    (data / "captures").mkdir(parents=True)
    (data / "review").mkdir(parents=True)
    (data / "research").mkdir(parents=True)
    (data / "events").mkdir(parents=True)
    (data / "raw").mkdir(parents=True)
    return data


def _write_manifest(pack_dir: Path, manifest: dict) -> None:
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def test_validate_capture_manifest_rejects_missing_fields() -> None:
    errors = validate_capture_manifest({"capture_id": "x"})
    assert errors
    assert any("missing fields" in item for item in errors)


def test_capture_ingestion_accepts_structured_export_and_aggregate(tmp_path: Path) -> None:
    data = _setup_data_root(tmp_path)
    pack_dir = data / "captures" / "2026-09-08T15-30-00Z-fixture1"
    pack_dir.mkdir(parents=True)
    export_payload = {
        "records": [
            {
                "donation_id": "donor-1",
                "source_id": "gofundme-fundraiser-page",
                "source_url": "https://example.test/fundraiser",
                "displayed_donor_name": "Public Donor",
                "displayed_amount": "$25",
                "normalized_amount": 25.0,
                "displayed_date": "2026-09-08",
                "anonymous_indicator": False,
                "verification_status": "UNVERIFIED",
                "confidence": "HIGH",
                "evidence_reference": "fixture:donor-1",
            },
            {
                "fundraiser_total": 1250,
                "fundraiser_goal": 3000,
                "displayed_donation_count": 44,
                "normalized_datetime": "2026-09-08T15:30:00+00:00",
            },
        ]
    }
    export_file = pack_dir / "export.json"
    export_file.write_text(json.dumps(export_payload, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "capture_id": "fixture-capture-1",
        "source": "authorized_capture",
        "source_url": "https://example.test/fundraiser",
        "captured_at": "2026-09-08T15:30:00+00:00",
        "collector_version": "capture-pack-v1",
        "capture_type": "export",
        "artifacts": [
            {
                "path": "export.json",
                "sha256": hashlib.sha256(export_file.read_bytes()).hexdigest(),
                "media_type": "application/json",
            }
        ],
    }
    _write_manifest(pack_dir, manifest)

    summary = ingest_capture_packs(data)
    manual_export = json.loads((data / "raw" / "gofundme_manual_export.json").read_text(encoding="utf-8"))
    observations = json.loads((data / "research" / "fundraiser_observations.json").read_text(encoding="utf-8"))
    normalized = json.loads((data / "research" / "capture_observations.normalized.json").read_text(encoding="utf-8"))

    assert summary["capture_packs_accepted"] == 1
    assert summary["records_added"] == 1
    assert summary["aggregate_observations_added"] == 1
    assert len(manual_export["records"]) == 1
    assert manual_export["records"][0]["donation_id"] == "donor-1"
    assert manual_export["records"][0]["capture_metadata"]["source"] == "authorized_capture"
    assert observations[0]["fundraiser_total"] == 1250.0
    assert normalized["observations"]


def test_capture_ingestion_accepts_contract_envelope(tmp_path: Path) -> None:
    data = _setup_data_root(tmp_path)
    pack_dir = data / "captures" / "2026-09-08T15-30-10Z-fixture-contract"
    pack_dir.mkdir(parents=True)
    export_payload = {
        "observations": [
            {
                "capture_metadata": {
                    "capture_id": "fixture-capture-contract",
                    "source": "authorized_capture",
                    "source_url": "https://example.test/fundraiser",
                    "captured_at": "2026-09-08T15:30:10+00:00",
                    "collector_version": "capture-pack-v1",
                    "capture_type": "mixed",
                    "source_reliability": "A",
                    "evidence_reference": "fixture-contract:export.json",
                },
                "observed_facts": {
                    "donation_id": "donor-contract-1",
                    "displayed_amount": "$30",
                    "normalized_amount": 30,
                    "displayed_date": "2026-09-08",
                },
                "provenance": {
                    "evidence_reference": "fixture-contract:export.json",
                    "artifact_sha256": "a" * 64,
                    "extraction_method": "structured_export",
                    "parser_confidence": "HIGH",
                    "hash_verified": True,
                },
            }
        ]
    }
    export_file = pack_dir / "export.json"
    export_file.write_text(json.dumps(export_payload, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "capture_id": "fixture-capture-contract",
        "source": "authorized_capture",
        "source_url": "https://example.test/fundraiser",
        "captured_at": "2026-09-08T15:30:10+00:00",
        "collector_version": "capture-pack-v1",
        "capture_type": "export",
        "source_reliability": "A",
        "artifacts": [
            {
                "path": "export.json",
                "sha256": hashlib.sha256(export_file.read_bytes()).hexdigest(),
                "media_type": "application/json",
            }
        ],
    }
    _write_manifest(pack_dir, manifest)
    summary = ingest_capture_packs(data)
    manual_export = json.loads((data / "raw" / "gofundme_manual_export.json").read_text(encoding="utf-8"))
    assert summary["capture_packs_accepted"] == 1
    assert manual_export["records"][0]["donation_id"] == "donor-contract-1"


def test_capture_ingestion_flags_impossible_aggregate_regression(tmp_path: Path) -> None:
    data = _setup_data_root(tmp_path)
    (data / "research" / "automation_config.json").write_text(
        json.dumps({"zero_drop_min_previous": 100, "near_zero_fraction": 0.05}),
        encoding="utf-8",
    )
    existing_observations = [
        {
            "observation_id": "existing-1",
            "source": "authorized_capture",
            "source_url": "https://example.test/fundraiser",
            "observed_at": "2026-09-08T10:00:00+00:00",
            "captured_at": "2026-09-08T10:00:00+00:00",
            "fundraiser_total": 1000.0,
            "fundraiser_goal": 3000.0,
            "displayed_donation_count": 10,
            "currency": "USD",
            "observation_state": "OBSERVED",
            "extraction_method": "structured_export",
            "confidence": "HIGH",
            "evidence_reference": "existing",
        }
    ]
    (data / "research" / "fundraiser_observations.json").write_text(json.dumps(existing_observations), encoding="utf-8")
    pack_dir = data / "captures" / "2026-09-08T15-31-10Z-fixture-regression"
    pack_dir.mkdir(parents=True)
    export_payload = {"records": [{"fundraiser_total": 20, "fundraiser_goal": 3000, "displayed_donation_count": 11}]}
    export_file = pack_dir / "export.json"
    export_file.write_text(json.dumps(export_payload), encoding="utf-8")
    manifest = {
        "capture_id": "fixture-capture-regression",
        "source": "authorized_capture",
        "source_url": "https://example.test/fundraiser",
        "captured_at": "2026-09-08T15:31:10+00:00",
        "collector_version": "capture-pack-v1",
        "capture_type": "export",
        "source_reliability": "A",
        "artifacts": [{"path": "export.json", "sha256": hashlib.sha256(export_file.read_bytes()).hexdigest(), "media_type": "application/json"}],
    }
    _write_manifest(pack_dir, manifest)

    summary = ingest_capture_packs(data)
    queue = json.loads((data / "review" / "queue.json").read_text(encoding="utf-8"))
    observations = json.loads((data / "research" / "fundraiser_observations.json").read_text(encoding="utf-8"))
    assert summary["conflicts_detected"] >= 1
    assert any(item.get("claim") == "conflict_detected" for item in queue)
    assert len(observations) == 1


def test_capture_ingestion_quarantines_hash_mismatch(tmp_path: Path) -> None:
    data = _setup_data_root(tmp_path)
    pack_dir = data / "captures" / "2026-09-08T15-31-00Z-fixture2"
    pack_dir.mkdir(parents=True)
    export_file = pack_dir / "export.json"
    export_file.write_text(json.dumps({"records": []}), encoding="utf-8")
    manifest = {
        "capture_id": "fixture-capture-2",
        "source": "public_reporting",
        "source_url": "https://example.test/report",
        "captured_at": "2026-09-08T15:31:00+00:00",
        "collector_version": "capture-pack-v1",
        "capture_type": "export",
        "artifacts": [{"path": "export.json", "sha256": "0" * 64, "media_type": "application/json"}],
    }
    _write_manifest(pack_dir, manifest)
    summary = ingest_capture_packs(data)
    quarantine = json.loads((data / "review" / "capture_quarantine.json").read_text(encoding="utf-8"))
    assert summary["capture_packs_quarantined"] == 1
    assert quarantine


def test_create_capture_pack_writes_manifest_and_hashes(tmp_path: Path) -> None:
    data = _setup_data_root(tmp_path)
    html_file = tmp_path / "page.html"
    html_file.write_text("<html><body>$100 raised of $500 goal</body></html>", encoding="utf-8")
    pack = create_capture_pack(
        data_dir=data,
        source="authorized_capture",
        source_url="https://example.test/fundraiser",
        capture_type="html",
        collector_version="capture-pack-v1",
        html_path=html_file,
        notes="fixture capture",
    )
    manifest_path = Path(pack["capture_dir"]) / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["source"] == "authorized_capture"
    assert payload["artifacts"]
