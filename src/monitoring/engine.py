from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from src.sources import GoFundMeAdapter, load_source_registry, write_source_registry
from src.sources.base import SourceMetadata


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_adapter(source: SourceMetadata, data_dir: Path):
    if source.source_id.startswith("gofundme"):
        return GoFundMeAdapter(source, data_root=data_dir)
    return GoFundMeAdapter(source, data_root=data_dir)


def _event(event_type: str, source_id: str, old_value, new_value, evidence: str, review_required: bool = False) -> dict:
    return {
        "event_id": str(uuid4()),
        "source_id": source_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "old_value": old_value,
        "new_value": new_value,
        "evidence": evidence,
        "confidence": "MEDIUM",
        "review_required": review_required,
    }


def run_monitoring_cycle(data_dir: Path, reports_dir: Path) -> dict:
    registry_path = data_dir / "source_registry.json"
    events_path = data_dir / "events" / "events.jsonl"
    monitor_state_path = data_dir / "research" / "source_monitor_state.json"
    donations_path = data_dir / "research" / "donations.json"
    review_path = data_dir / "review" / "queue.json"
    run_log_path = data_dir / "research" / "collection_runs.json"

    sources = load_source_registry(registry_path)
    prior_state = _load_json(monitor_state_path, {})
    donations = _load_json(donations_path, [])
    review_queue = _load_json(review_path, [])
    run_log = _load_json(run_log_path, [])

    now = datetime.now(UTC).isoformat()
    changed_sources = 0
    records_added = 0
    records_modified = 0
    records_rejected = 0
    sources_checked = 0
    events: list[dict] = []

    for source in sources:
        if not source.monitoring_enabled:
            continue
        sources_checked += 1
        adapter = _build_adapter(source, data_dir)
        source.last_checked = now

        try:
            result = adapter.run()
            source.error_count = 0
            source.last_successful_collection = now
            source.collection_status = "ok"
            new_hash = result.observation.content_hash if result.observation else None
            old_hash = prior_state.get(source.source_id, {}).get("content_hash")
            changed = bool(new_hash and adapter.compare(old_hash, new_hash))
            if changed:
                changed_sources += 1
                events.append(
                    _event(
                        "SOURCE_CONTENT_CHANGED",
                        source.source_id,
                        old_hash,
                        new_hash,
                        result.observation.evidence_reference if result.observation else "UNKNOWN",
                    )
                )
            if result.errors:
                records_rejected += len(result.errors)
                review_queue.append(
                    {
                        "review_id": str(uuid4()),
                        "source": source.source_id,
                        "claim": "validation_error",
                        "evidence": "; ".join(result.errors),
                        "affected_record": "UNKNOWN",
                        "submitter": "system",
                        "risk_level": "MEDIUM_RISK",
                        "status": "UNDER_REVIEW",
                        "reviewer": "UNASSIGNED",
                        "decision": "PENDING",
                        "decision_timestamp": "UNKNOWN",
                    }
                )
            else:
                existing_ids = {d.get("donation_id") for d in donations}
                for rec in result.records:
                    donation_id = rec.get("donation_id")
                    if donation_id and donation_id in existing_ids:
                        records_modified += 1
                    else:
                        records_added += 1
                    donations.append(rec)

            prior_state[source.source_id] = {
                "source_id": source.source_id,
                "url": source.canonical_url,
                "monitoring_enabled": source.monitoring_enabled,
                "polling_frequency": source.polling_frequency,
                "last_checked": source.last_checked,
                "last_success": source.last_successful_collection,
                "last_change": now if changed else prior_state.get(source.source_id, {}).get("last_change"),
                "content_hash": new_hash,
                "parser_version": source.parser_version,
                "status": source.collection_status,
                "error_count": source.error_count,
            }
        except (ValueError, TypeError, OSError, KeyError, json.JSONDecodeError) as exc:
            source.error_count += 1
            source.collection_status = "TEMPORARILY_UNAVAILABLE"
            backoff_minutes = min(60, 2 ** source.error_count)
            next_check = (datetime.now(UTC) + timedelta(minutes=backoff_minutes)).isoformat()
            prior_state[source.source_id] = {
                "source_id": source.source_id,
                "url": source.canonical_url,
                "monitoring_enabled": source.monitoring_enabled,
                "polling_frequency": source.polling_frequency,
                "last_checked": source.last_checked,
                "last_success": source.last_successful_collection,
                "last_change": prior_state.get(source.source_id, {}).get("last_change"),
                "content_hash": prior_state.get(source.source_id, {}).get("content_hash"),
                "parser_version": source.parser_version,
                "status": source.collection_status,
                "error_count": source.error_count,
                "next_check_after": next_check,
                "error": str(exc),
            }
            review_queue.append(
                {
                    "review_id": str(uuid4()),
                    "source": source.source_id,
                    "claim": "source_failure",
                    "evidence": str(exc),
                    "affected_record": "N/A",
                    "submitter": "system",
                    "risk_level": "HIGH_RISK",
                    "status": "NEW",
                    "reviewer": "UNASSIGNED",
                    "decision": "PENDING",
                    "decision_timestamp": "UNKNOWN",
                }
            )
            events.append(_event("SOURCE_UNAVAILABLE", source.source_id, "ok", "TEMPORARILY_UNAVAILABLE", str(exc), True))

    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as fh:
        for entry in events:
            fh.write(json.dumps(entry) + "\n")

    _save_json(monitor_state_path, prior_state)
    _save_json(donations_path, donations)
    _save_json(review_path, review_queue)
    _save_json(run_log_path, run_log + [{
        "run_id": str(uuid4()),
        "start_time": now,
        "end_time": datetime.now(UTC).isoformat(),
        "collector": "monitoring_engine",
        "source": "*",
        "records_seen": len(donations),
        "records_added": records_added,
        "records_changed": records_modified,
        "records_rejected": records_rejected,
        "errors": "",
        "warnings": "",
        "coverage": "Partially observable dataset",
        "software_version": "0.1.0",
        "dataset_version": "v0.1.0",
    }])
    write_source_registry(registry_path, sources)

    summary = {
        "last_attempted_update": datetime.now(UTC).isoformat(),
        "last_successful_update": now,
        "sources_checked": sources_checked,
        "sources_changed": changed_sources,
        "records_added": records_added,
        "records_modified": records_modified,
        "records_rejected": records_rejected,
        "records_awaiting_review": len([r for r in review_queue if r.get("status") in {"NEW", "UNDER_REVIEW"}]),
        "dataset_version": "v0.1.0",
    }
    _save_json(reports_dir / "system-health.json", {
        "health": "OK",
        "workflow_status": "ready",
        "source_availability": "partial",
        "parser_status": "monitoring",
        "last_successful_run": summary["last_successful_update"],
        "pending_reviews": summary["records_awaiting_review"],
    })
    _save_json(reports_dir / "live-data-status.json", summary)
    return summary
