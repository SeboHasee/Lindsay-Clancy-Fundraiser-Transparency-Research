from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.sources import GoFundMeAdapter, load_source_registry, write_source_registry
from src.sources.base import SourceMetadata

TRANSIENT_EXCEPTIONS = (TimeoutError, OSError)
ZERO_DROP_FRACTION = 0.05
ZERO_DROP_MIN_PREVIOUS = 100


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _build_adapter(source: SourceMetadata, data_dir: Path) -> GoFundMeAdapter:
    if source.source_id.startswith("gofundme"):
        return GoFundMeAdapter(source, data_root=data_dir)
    return GoFundMeAdapter(source, data_root=data_dir)


def _event(
    event_type: str,
    source_id: str,
    old_value: Any,
    new_value: Any,
    evidence: str,
    review_required: bool = False,
) -> dict[str, Any]:
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


def _classify_error(exc: Exception) -> str:
    if isinstance(exc, TRANSIENT_EXCEPTIONS):
        return "TRANSIENT"
    if isinstance(exc, json.JSONDecodeError):
        return "PARSER_ERROR"
    if isinstance(exc, ValueError):
        return "VALIDATION_ERROR"
    if isinstance(exc, KeyError):
        return "CONFIGURATION_ERROR"
    return "UNKNOWN"


def _ensure_paths(data_dir: Path, reports_dir: Path) -> dict[str, Path]:
    status_dir = data_dir.parent / "status"
    return {
        "registry": data_dir / "source_registry.json",
        "events_jsonl": data_dir / "events" / "events.jsonl",
        "monitor_state": data_dir / "research" / "source_monitor_state.json",
        "donations": data_dir / "research" / "donations.json",
        "review_queue": data_dir / "review" / "queue.json",
        "run_log": data_dir / "research" / "collection_runs.json",
        "donation_observations": data_dir / "research" / "donation_observations.jsonl",
        "health": reports_dir / "system-health.json",
        "live_status": reports_dir / "live-data-status.json",
        "system_status": status_dir / "system-status.json",
        "automation_config": data_dir / "research" / "automation_config.json",
    }


def _read_automation_config(path: Path) -> dict[str, Any]:
    default = {
        "timezone": "UTC",
        "stale_warning_hours": 36,
        "stale_critical_hours": 72,
        "scheduler_interval_hours": 24,
    }
    if not path.exists():
        return default
    cfg = _load_json(path, {})
    return {
        "timezone": cfg.get("timezone", "UTC"),
        "stale_warning_hours": int(cfg.get("stale_warning_hours", 36)),
        "stale_critical_hours": int(cfg.get("stale_critical_hours", 72)),
        "scheduler_interval_hours": int(cfg.get("scheduler_interval_hours", 24)),
    }


def compute_automation_status(last_successful_run: str | None, config: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    if not last_successful_run:
        return {
            "automation_status": "STALE",
            "status": "degraded",
            "age_hours": None,
            "expected_next_run": None,
            "message": "No successful scheduled run recorded",
        }

    last = datetime.fromisoformat(last_successful_run)
    age_hours = (now - last).total_seconds() / 3600.0
    expected_next = last + timedelta(hours=int(config["scheduler_interval_hours"]))
    if age_hours > float(config["stale_critical_hours"]):
        level = "STALE"
        status = "degraded"
    elif age_hours > float(config["stale_warning_hours"]):
        level = "WARNING"
        status = "warning"
    else:
        level = "CURRENT"
        status = "healthy"

    return {
        "automation_status": level,
        "status": status,
        "age_hours": round(age_hours, 3),
        "expected_next_run": expected_next.isoformat(),
        "message": f"AUTOMATION STATUS: {level}",
    }


def _zero_data_safety_guard(previous_count: int, new_count: int) -> None:
    if previous_count < ZERO_DROP_MIN_PREVIOUS:
        return
    if new_count == 0:
        raise ValueError("PARSER_ERROR_ZERO_RESULTS")
    if new_count / previous_count <= ZERO_DROP_FRACTION:
        raise ValueError("PARSER_ERROR_NEAR_ZERO_RESULTS")


def run_monitoring_cycle(data_dir: Path, reports_dir: Path) -> dict[str, Any]:
    paths = _ensure_paths(data_dir, reports_dir)

    sources = load_source_registry(paths["registry"])
    prior_state = _load_json(paths["monitor_state"], {})
    existing_donations = _load_json(paths["donations"], [])
    review_queue = _load_json(paths["review_queue"], [])
    run_log = _load_json(paths["run_log"], [])
    automation_config = _read_automation_config(paths["automation_config"])

    now = datetime.now(UTC).isoformat()
    changed_sources = 0
    records_added = 0
    records_modified = 0
    records_rejected = 0
    sources_checked = 0
    sources_healthy = 0
    sources_degraded = 0

    events: list[dict[str, Any]] = []
    donation_observations: list[dict[str, Any]] = []

    canonical_by_id = {str(d["donation_id"]): d for d in existing_donations if d.get("donation_id")}
    previous_total_count = len(canonical_by_id)

    for source in sources:
        if not source.monitoring_enabled:
            continue

        sources_checked += 1
        source.last_checked = now
        adapter = _build_adapter(source, data_dir)

        try:
            result = adapter.run()
            source.error_count = 0
            source.last_successful_collection = now
            source.collection_status = "ok"
            sources_healthy += 1

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

            source_records = result.records
            _zero_data_safety_guard(previous_total_count, len(source_records))

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
                for rec in source_records:
                    donation_id = rec.get("donation_id")
                    if not donation_id:
                        records_rejected += 1
                        continue

                    key = str(donation_id)
                    current = canonical_by_id.get(key)
                    if current is None:
                        canonical_by_id[key] = rec
                        records_added += 1
                        events.append(_event("DONATION_RECORD_ADDED", source.source_id, None, key, "ingestion", False))
                    elif current != rec:
                        canonical_by_id[key] = rec
                        records_modified += 1
                        events.append(_event("DONATION_RECORD_MODIFIED", source.source_id, key, key, "ingestion", False))

                    donation_observations.append(
                        {
                            "observation_id": str(uuid4()),
                            "source_id": source.source_id,
                            "donation_id": key,
                            "observed_at_utc": now,
                            "record_hash": adapter.fingerprint(rec),
                            "record": rec,
                        }
                    )

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

        except (ValueError, TypeError, OSError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
            classification = _classify_error(exc)
            source.error_count += 1
            source.collection_status = "TEMPORARILY_UNAVAILABLE" if classification == "TRANSIENT" else "ERROR"
            sources_degraded += 1

            backoff_minutes = min(180, 2**source.error_count)
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
                "error_classification": classification,
                "error": str(exc),
            }

            review_queue.append(
                {
                    "review_id": str(uuid4()),
                    "source": source.source_id,
                    "claim": "source_failure",
                    "evidence": f"{classification}: {exc}",
                    "affected_record": "N/A",
                    "submitter": "system",
                    "risk_level": "HIGH_RISK",
                    "status": "NEW",
                    "reviewer": "UNASSIGNED",
                    "decision": "PENDING",
                    "decision_timestamp": "UNKNOWN",
                }
            )
            events.append(
                _event(
                    "SOURCE_UNAVAILABLE",
                    source.source_id,
                    "ok",
                    source.collection_status,
                    f"{classification}: {exc}",
                    True,
                )
            )

    canonical_donations = sorted(canonical_by_id.values(), key=lambda x: str(x.get("donation_id")))

    _append_jsonl(paths["events_jsonl"], events)
    _append_jsonl(paths["donation_observations"], donation_observations)

    _save_json(paths["monitor_state"], prior_state)
    _save_json(paths["donations"], canonical_donations)
    _save_json(paths["review_queue"], review_queue)
    _save_json(
        paths["run_log"],
        run_log
        + [
            {
                "run_id": str(uuid4()),
                "start_time": now,
                "end_time": datetime.now(UTC).isoformat(),
                "collector": "monitoring_engine",
                "source": "*",
                "records_seen": len(canonical_donations),
                "records_added": records_added,
                "records_changed": records_modified,
                "records_rejected": records_rejected,
                "errors": "",
                "warnings": "",
                "coverage": "Partially observable dataset",
                "software_version": "0.1.0",
                "dataset_version": "v0.1.0",
            }
        ],
    )
    write_source_registry(paths["registry"], sources)

    live_status = {
        "last_attempted_update": datetime.now(UTC).isoformat(),
        "last_successful_update": now,
        "sources_checked": sources_checked,
        "sources_changed": changed_sources,
        "records_added": records_added,
        "records_modified": records_modified,
        "records_rejected": records_rejected,
        "records_awaiting_review": len([r for r in review_queue if r.get("status") in {"NEW", "UNDER_REVIEW"}]),
        "dataset_version": "v0.1.0",
        "source_health": {"total": sources_checked, "healthy": sources_healthy, "degraded": sources_degraded},
        "timezone": automation_config["timezone"],
    }

    _save_json(paths["health"], {
        "health": "OK" if sources_degraded == 0 else "DEGRADED",
        "workflow_status": "ready",
        "source_availability": "healthy" if sources_degraded == 0 else "partial",
        "parser_status": "monitoring",
        "last_successful_run": live_status["last_successful_update"],
        "pending_reviews": live_status["records_awaiting_review"],
    })
    _save_json(paths["live_status"], live_status)

    automation = compute_automation_status(live_status["last_successful_update"], automation_config)
    system_status = {
        "status": automation["status"],
        "automation_status": automation["automation_status"],
        "last_successful_run": live_status["last_successful_update"],
        "last_dataset_update": live_status["last_successful_update"],
        "expected_next_run": automation["expected_next_run"],
        "dataset_version": live_status["dataset_version"],
        "sources_total": live_status["source_health"]["total"],
        "sources_healthy": live_status["source_health"]["healthy"],
        "sources_degraded": live_status["source_health"]["degraded"],
        "data_pipeline": "DEGRADED" if sources_degraded else "HEALTHY",
        "website": "ONLINE",
        "message": automation["message"],
    }
    _save_json(paths["system_status"], system_status)

    return live_status
