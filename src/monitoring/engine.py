from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.sources import GoFundMeAdapter, load_source_registry, write_source_registry
from src.sources.base import SourceMetadata

TRANSIENT_EXCEPTIONS = (TimeoutError, OSError)


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


def _read_jsonl_signatures(path: Path) -> set[tuple[str, str, str]]:
    if not path.exists():
        return set()
    signatures: set[tuple[str, str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        signatures.add(
            (
                str(payload.get("source_id", "")),
                str(payload.get("donation_id", "")),
                str(payload.get("record_hash", "")),
            )
        )
    return signatures


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
        token = str(exc)
        if token.startswith("PARSER_ERROR"):
            return "PARSER_ERROR"
        if token.startswith("SOURCE_ERROR"):
            return "SOURCE_ERROR"
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
        "zero_drop_min_previous": 100,
        "near_zero_fraction": 0.05,
        "coverage_drop_alert_ratio": 0.5,
    }
    if not path.exists():
        return default
    cfg = _load_json(path, {})
    return {
        "timezone": cfg.get("timezone", default["timezone"]),
        "stale_warning_hours": int(cfg.get("stale_warning_hours", default["stale_warning_hours"])),
        "stale_critical_hours": int(cfg.get("stale_critical_hours", default["stale_critical_hours"])),
        "scheduler_interval_hours": int(cfg.get("scheduler_interval_hours", default["scheduler_interval_hours"])),
        "zero_drop_min_previous": int(cfg.get("zero_drop_min_previous", default["zero_drop_min_previous"])),
        "near_zero_fraction": float(cfg.get("near_zero_fraction", default["near_zero_fraction"])),
        "coverage_drop_alert_ratio": float(cfg.get("coverage_drop_alert_ratio", default["coverage_drop_alert_ratio"])),
    }


def compute_automation_status(last_successful_run: str | None, config: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    if not last_successful_run:
        return {
            "automation_status": "FAILED",
            "status": "FAILED",
            "age_hours": None,
            "expected_next_run": None,
            "message": "AUTOMATION STATUS: FAILED",
        }

    normalized = f"{last_successful_run[:-1]}+00:00" if last_successful_run.endswith("Z") else last_successful_run
    last = datetime.fromisoformat(normalized)
    age_hours = (now - last).total_seconds() / 3600.0
    expected_next = last + timedelta(hours=int(config["scheduler_interval_hours"]))

    if age_hours > float(config["stale_critical_hours"]):
        level = "STALE"
    elif age_hours > float(config["stale_warning_hours"]):
        level = "DEGRADED"
    else:
        level = "HEALTHY"

    return {
        "automation_status": level,
        "status": level,
        "age_hours": round(age_hours, 3),
        "expected_next_run": expected_next.isoformat(),
        "message": f"AUTOMATION STATUS: {level}",
    }


def _schema_fingerprint(records: list[dict[str, Any]]) -> str:
    if not records:
        return "EMPTY"
    keys = sorted({key for record in records for key in record})
    return "|".join(keys)


def _queue_item(source_id: str, claim: str, evidence: str, risk_level: str = "HIGH_RISK") -> dict[str, Any]:
    return {
        "review_id": str(uuid4()),
        "source": source_id,
        "claim": claim,
        "evidence": evidence,
        "affected_record": "N/A",
        "submitter": "system",
        "risk_level": risk_level,
        "status": "NEW",
        "reviewer": "UNASSIGNED",
        "decision": "PENDING",
        "decision_timestamp": "UNKNOWN",
    }


def run_monitoring_cycle(data_dir: Path, reports_dir: Path) -> dict[str, Any]:
    paths = _ensure_paths(data_dir, reports_dir)
    sources = load_source_registry(paths["registry"])
    prior_state = _load_json(paths["monitor_state"], {})
    existing_donations = _load_json(paths["donations"], [])
    review_queue = _load_json(paths["review_queue"], [])
    run_log = _load_json(paths["run_log"], [])
    previous_live_status = _load_json(paths["live_status"], {})
    automation_config = _read_automation_config(paths["automation_config"])

    now = datetime.now(UTC).isoformat()
    changed_sources = 0
    records_added = 0
    records_modified = 0
    records_rejected = 0
    sources_checked = 0
    sources_healthy = 0
    sources_degraded = 0
    sources_not_automated = 0

    events: list[dict[str, Any]] = []
    donation_observations: list[dict[str, Any]] = []
    existing_observation_sigs = _read_jsonl_signatures(paths["donation_observations"])

    canonical_by_id = {str(d["donation_id"]): d for d in existing_donations if d.get("donation_id")}

    for source in sources:
        if not source.monitoring_enabled:
            continue

        sources_checked += 1
        source.last_checked = now
        adapter = _build_adapter(source, data_dir)

        previous_source_state = prior_state.get(source.source_id, {})
        previous_source_count = int(previous_source_state.get("last_record_count", 0) or 0)

        try:
            result = adapter.run()
            source.error_count = 0
            source.last_successful_collection = now

            new_hash = result.observation.content_hash if result.observation else None
            old_hash = previous_source_state.get("content_hash")
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

            source_records = [r for r in result.records if isinstance(r, dict)]
            source_schema = _schema_fingerprint(source_records)
            previous_schema = str(previous_source_state.get("schema_fingerprint", ""))
            if previous_schema and previous_schema != "EMPTY" and source_schema != previous_schema:
                source.collection_status = "SOURCE_PARSER_ERROR"
                sources_degraded += 1
                events.append(
                    _event(
                        "SOURCE_STRUCTURE_CHANGED",
                        source.source_id,
                        previous_schema,
                        source_schema,
                        "schema fingerprint changed",
                        True,
                    )
                )
                review_queue.append(_queue_item(source.source_id, "parser_structure_change", "schema fingerprint changed"))
                source_records = []
            elif result.source_state == "SOURCE_NOT_AUTOMATED":
                source.collection_status = "SOURCE_NOT_AUTOMATED"
                sources_not_automated += 1
                events.append(_event("SOURCE_NOT_AUTOMATED", source.source_id, None, None, "manual fallback active", False))
                source_records = []
            elif not source_records:
                if previous_source_count >= int(automation_config["zero_drop_min_previous"]):
                    raise ValueError("PARSER_ERROR_ZERO_RESULTS")
                source.collection_status = "SOURCE_EMPTY"
                sources_degraded += 1
                events.append(_event("SOURCE_EMPTY", source.source_id, previous_source_count, 0, "no records observed", True))
            elif previous_source_count >= int(automation_config["zero_drop_min_previous"]) and (
                len(source_records) / previous_source_count <= float(automation_config["near_zero_fraction"])
            ):
                raise ValueError("PARSER_ERROR_NEAR_ZERO_RESULTS")
            elif result.errors:
                source.collection_status = "SOURCE_VALIDATION_ERROR"
                sources_degraded += 1
                records_rejected += len(result.errors)
                review_queue.append(_queue_item(source.source_id, "validation_error", "; ".join(result.errors), "MEDIUM_RISK"))
            else:
                source.collection_status = "SOURCE_HEALTHY"
                sources_healthy += 1

            if source_records and previous_source_count > 0:
                ratio = len(source_records) / previous_source_count
                if ratio < float(automation_config["coverage_drop_alert_ratio"]):
                    sources_degraded += 1
                    source.collection_status = "SOURCE_DEGRADED_COVERAGE"
                    events.append(
                        _event(
                            "COVERAGE_DROP_DETECTED",
                            source.source_id,
                            previous_source_count,
                            len(source_records),
                            f"ratio={ratio:.4f}",
                            True,
                        )
                    )
                    review_queue.append(_queue_item(source.source_id, "coverage_drop", f"source coverage ratio {ratio:.4f}"))

            source_record_ids = {str(rec.get("donation_id")) for rec in source_records if rec.get("donation_id")}
            previous_source_ids = {
                str(key)
                for key, value in canonical_by_id.items()
                if str(value.get("source_id", source.source_id)) == source.source_id
            }
            removed_ids = sorted(previous_source_ids - source_record_ids)
            for donation_id in removed_ids:
                events.append(_event("DONATION_RECORD_REMOVED", source.source_id, donation_id, None, "missing in latest source view", True))

            for rec in source_records:
                key = str(rec.get("donation_id", "")).strip()
                if not key:
                    records_rejected += 1
                    continue

                current = canonical_by_id.get(key)
                if current is None:
                    canonical_by_id[key] = rec
                    records_added += 1
                    events.append(_event("DONATION_RECORD_ADDED", source.source_id, None, key, "ingestion", False))
                elif current != rec:
                    canonical_by_id[key] = rec
                    records_modified += 1
                    events.append(_event("DONATION_RECORD_MODIFIED", source.source_id, key, key, "ingestion", False))

                record_hash = adapter.fingerprint(rec)
                signature = (source.source_id, key, record_hash)
                if signature not in existing_observation_sigs:
                    donation_observations.append(
                        {
                            "observation_id": str(uuid4()),
                            "source_id": source.source_id,
                            "donation_id": key,
                            "observed_at_utc": now,
                            "record_hash": record_hash,
                            "parser_version": source.parser_version,
                            "validation_state": "VALID" if not result.errors else "INVALID",
                            "record": rec,
                        }
                    )
                    existing_observation_sigs.add(signature)

            prior_state[source.source_id] = {
                "source_id": source.source_id,
                "url": source.canonical_url,
                "monitoring_enabled": source.monitoring_enabled,
                "polling_frequency": source.polling_frequency,
                "last_checked": source.last_checked,
                "last_success": source.last_successful_collection,
                "last_change": now if changed else previous_source_state.get("last_change"),
                "content_hash": new_hash,
                "schema_fingerprint": source_schema,
                "last_record_count": len(source_records),
                "parser_version": source.parser_version,
                "status": source.collection_status,
                "error_count": source.error_count,
                "warnings": result.warnings,
            }

        except (ValueError, TypeError, OSError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
            classification = _classify_error(exc)
            source.error_count += 1
            source.collection_status = "SOURCE_UNAVAILABLE" if classification == "TRANSIENT" else "SOURCE_ERROR"
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
                "last_change": previous_source_state.get("last_change"),
                "content_hash": previous_source_state.get("content_hash"),
                "schema_fingerprint": previous_source_state.get("schema_fingerprint"),
                "last_record_count": previous_source_state.get("last_record_count", 0),
                "parser_version": source.parser_version,
                "status": source.collection_status,
                "error_count": source.error_count,
                "next_check_after": next_check,
                "error_classification": classification,
                "error": str(exc),
            }
            review_queue.append(_queue_item(source.source_id, "source_failure", f"{classification}: {exc}"))
            events.append(
                _event(
                    "SOURCE_FAILURE",
                    source.source_id,
                    "SOURCE_HEALTHY",
                    source.collection_status,
                    f"{classification}: {exc}",
                    True,
                )
            )

    canonical_donations = sorted(canonical_by_id.values(), key=lambda item: str(item.get("donation_id")))
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

    run_failed = sources_checked == 0 or (sources_degraded > 0 and sources_healthy == 0 and sources_not_automated == 0)
    last_successful_update = previous_live_status.get("last_successful_update") if run_failed else now

    live_status = {
        "last_attempted_update": datetime.now(UTC).isoformat(),
        "last_successful_update": last_successful_update,
        "sources_checked": sources_checked,
        "sources_changed": changed_sources,
        "records_added": records_added,
        "records_modified": records_modified,
        "records_rejected": records_rejected,
        "records_awaiting_review": len([r for r in review_queue if r.get("status") in {"NEW", "UNDER_REVIEW", "PENDING_REVIEW"}]),
        "dataset_version": "v0.1.0",
        "dataset_size": len(canonical_donations),
        "historical_observation_count": len(existing_observation_sigs),
        "source_health": {
            "total": sources_checked,
            "healthy": sources_healthy,
            "degraded": sources_degraded,
            "not_automated": sources_not_automated,
        },
        "timezone": automation_config["timezone"],
        "run_state": "FAILED" if run_failed else ("DEGRADED" if sources_degraded else "HEALTHY"),
    }

    _save_json(
        paths["health"],
        {
            "health": live_status["run_state"],
            "workflow_status": "ready",
            "source_availability": "healthy" if sources_degraded == 0 else "partial",
            "parser_status": "monitoring",
            "last_successful_run": live_status["last_successful_update"],
            "pending_reviews": live_status["records_awaiting_review"],
        },
    )
    _save_json(paths["live_status"], live_status)

    automation = compute_automation_status(live_status["last_successful_update"], automation_config)
    overall_state = live_status["run_state"]
    if overall_state != "FAILED":
        if automation["automation_status"] == "STALE":
            overall_state = "STALE"
        elif automation["automation_status"] == "DEGRADED" or overall_state == "DEGRADED":
            overall_state = "DEGRADED"
        else:
            overall_state = "HEALTHY"

    system_status = {
        "status": overall_state,
        "automation_status": automation["automation_status"],
        "last_successful_run": live_status["last_successful_update"],
        "last_attempted_ingestion": live_status["last_attempted_update"],
        "last_dataset_update": live_status["last_successful_update"],
        "expected_next_run": automation["expected_next_run"],
        "dataset_version": live_status["dataset_version"],
        "dataset_size": live_status["dataset_size"],
        "historical_observation_count": live_status["historical_observation_count"],
        "sources_total": live_status["source_health"]["total"],
        "sources_healthy": live_status["source_health"]["healthy"],
        "sources_degraded": live_status["source_health"]["degraded"],
        "sources_not_automated": live_status["source_health"]["not_automated"],
        "data_pipeline": "FAILED" if run_failed else ("DEGRADED" if sources_degraded else "HEALTHY"),
        "website": "ONLINE",
        "message": automation["message"],
    }
    _save_json(paths["system_status"], system_status)
    return live_status
