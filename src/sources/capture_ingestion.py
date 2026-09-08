from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ALLOWED_CAPTURE_TYPES = {"html", "screenshot", "export", "archive", "mixed"}
ALLOWED_SOURCES = {"authorized_capture", "public_reporting", "archive"}
PROHIBITED_FIELDS = {"email", "phone", "address", "private_social_account"}
CONFIDENCE_RANK = {"UNRESOLVED": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
HTML_MEDIA_TYPES = {"text/html", "application/xhtml+xml"}
JSON_MEDIA_TYPES = {"application/json"}
IMAGE_MEDIA_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_iso(value: str | None) -> str:
    if not value:
        return datetime.now(UTC).isoformat()
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    dt = datetime.fromisoformat(normalized)
    return dt.astimezone(UTC).isoformat()


def _money_to_float(value: str | float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    token = str(value).strip()
    if not token:
        return None
    multiplier = 1.0
    upper = token.upper()
    if upper.endswith("M"):
        multiplier = 1_000_000.0
    elif upper.endswith("K"):
        multiplier = 1_000.0
    cleaned = re.sub(r"[^0-9.\-]", "", token)
    if cleaned.count(".") > 1 or cleaned in {"", "-", ".", "-."}:
        return None
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def _to_int(value: str | float | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    cleaned = re.sub(r"[^0-9]", "", str(value))
    if not cleaned:
        return None
    return int(cleaned)


def _determine_confidence(source: str, method: str) -> str:
    if source == "authorized_capture" and method in {"structured_export", "known_html"}:
        return "HIGH"
    if source in {"public_reporting", "archive"} and method in {"structured_export", "known_html"}:
        return "MEDIUM"
    if method == "pattern_text":
        return "LOW"
    return "UNRESOLVED"


def _manifest_event(capture_id: str, event_type: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "source_id": "capture-pack",
        "timestamp": datetime.now(UTC).isoformat(),
        "capture_id": capture_id,
        "details": details,
    }


def validate_capture_manifest(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"capture_id", "source", "source_url", "captured_at", "collector_version", "capture_type", "artifacts"}
    missing = sorted(required - set(payload))
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")

    if str(payload.get("source", "")) not in ALLOWED_SOURCES:
        errors.append("source must be authorized_capture|public_reporting|archive")
    if str(payload.get("capture_type", "")) not in ALLOWED_CAPTURE_TYPES:
        errors.append("capture_type must be html|screenshot|export|archive|mixed")

    source_url = str(payload.get("source_url", ""))
    if not source_url.startswith(("http://", "https://")):
        errors.append("source_url must be http(s)")

    try:
        _parse_iso(str(payload.get("captured_at", "")))
    except ValueError:
        errors.append("captured_at must be ISO datetime")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("artifacts must be a non-empty list")
    else:
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                errors.append(f"artifact[{index}] must be object")
                continue
            for key in ("path", "sha256", "media_type"):
                if key not in artifact:
                    errors.append(f"artifact[{index}] missing {key}")
            sha = str(artifact.get("sha256", ""))
            if sha and (len(sha) != 64 or not re.fullmatch(r"[0-9a-fA-F]{64}", sha)):
                errors.append(f"artifact[{index}] sha256 must be 64 hex chars")
    return errors


def _verify_artifact_hashes(pack_dir: Path, artifacts: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, artifact in enumerate(artifacts):
        rel = str(artifact.get("path", ""))
        expected = str(artifact.get("sha256", "")).lower()
        artifact_path = (pack_dir / rel).resolve()
        if not artifact_path.exists():
            errors.append(f"artifact[{index}] missing file {rel}")
            continue
        if pack_dir.resolve() not in artifact_path.parents:
            errors.append(f"artifact[{index}] escapes pack directory")
            continue
        actual = _sha256_file(artifact_path)
        if actual != expected:
            errors.append(f"artifact[{index}] hash mismatch for {rel}")
    return errors


def _sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    clean = dict(record)
    for key in PROHIBITED_FIELDS:
        clean.pop(key, None)
    return clean


def _normalize_donation_record(
    record: dict[str, Any],
    *,
    capture_id: str,
    source: str,
    source_url: str,
    captured_at: str,
    evidence_reference: str,
    extraction_method: str,
    default_index: int,
) -> dict[str, Any] | None:
    displayed_amount = record.get("displayed_amount") or record.get("amount")
    normalized_amount = record.get("normalized_amount")
    if normalized_amount is None:
        normalized_amount = _money_to_float(displayed_amount)
    if displayed_amount is None and normalized_amount is None:
        return None

    confidence = str(record.get("confidence") or _determine_confidence(source, extraction_method)).upper()
    if confidence not in CONFIDENCE_RANK:
        confidence = "UNRESOLVED"

    display_name = record.get("displayed_donor_name") or record.get("display_name")
    message = record.get("displayed_message") or record.get("message")
    donation_id = str(record.get("donation_id") or f"{capture_id}-donation-{default_index:04d}")
    displayed_date = record.get("displayed_date")
    normalized_datetime = record.get("normalized_datetime")
    if normalized_datetime is None and displayed_date:
        date_token = str(displayed_date)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_token):
            normalized_datetime = f"{date_token}T00:00:00+00:00"

    cleaned = _sanitize_record(
        {
            "donation_id": donation_id,
            "source_id": str(record.get("source_id") or "gofundme-fundraiser-page"),
            "source_url": str(record.get("source_url") or source_url),
            "displayed_donor_name": display_name,
            "displayed_amount": str(displayed_amount if displayed_amount is not None else normalized_amount),
            "normalized_amount": float(normalized_amount) if normalized_amount is not None else None,
            "currency": record.get("currency") or "USD",
            "displayed_date": displayed_date,
            "normalized_datetime": normalized_datetime,
            "displayed_message": message,
            "anonymous_indicator": bool(record.get("anonymous_indicator", display_name in {None, "", "Anonymous"})),
            "organization_claim": record.get("organization_claim"),
            "public_figure_claim": record.get("public_figure_claim"),
            "verification_status": record.get("verification_status") or "UNVERIFIED",
            "verification_source": record.get("verification_source"),
            "confidence": confidence,
            "first_observed_at": record.get("first_observed_at") or captured_at,
            "last_observed_at": record.get("last_observed_at") or captured_at,
            "collection_method": record.get("collection_method") or extraction_method,
            "collection_timestamp": record.get("collection_timestamp") or captured_at,
            "evidence_reference": record.get("evidence_reference") or evidence_reference,
            "notes": record.get("notes"),
        }
    )
    return cleaned


def _normalize_aggregate_observation(
    record: dict[str, Any],
    *,
    capture_id: str,
    source: str,
    source_url: str,
    captured_at: str,
    evidence_reference: str,
    extraction_method: str,
) -> dict[str, Any] | None:
    total = _money_to_float(record.get("fundraiser_total") or record.get("total_raised") or record.get("amount_raised"))
    goal = _money_to_float(record.get("fundraiser_goal") or record.get("goal"))
    donor_count = _to_int(record.get("displayed_donation_count") or record.get("donation_count") or record.get("donor_count"))
    if total is None and goal is None and donor_count is None:
        return None

    confidence = str(record.get("confidence") or _determine_confidence(source, extraction_method)).upper()
    if confidence not in CONFIDENCE_RANK:
        confidence = "UNRESOLVED"

    observed_at = record.get("normalized_datetime") or record.get("observed_at") or captured_at
    if observed_at and isinstance(observed_at, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", observed_at):
        observed_at = f"{observed_at}T00:00:00+00:00"
    observed_at = _parse_iso(str(observed_at))

    payload = {
        "capture_id": capture_id,
        "source": source,
        "source_url": source_url,
        "observed_at": observed_at,
        "captured_at": captured_at,
        "fundraiser_total": total,
        "fundraiser_goal": goal,
        "displayed_donation_count": donor_count,
        "currency": record.get("currency") or "USD",
        "observation_state": record.get("observation_state") or "OBSERVED",
        "extraction_method": extraction_method,
        "confidence": confidence,
        "evidence_reference": record.get("evidence_reference") or evidence_reference,
    }
    payload["observation_id"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def _extract_from_structured_payload(
    payload: dict[str, Any],
    *,
    manifest: dict[str, Any],
    evidence_reference: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records_out: list[dict[str, Any]] = []
    aggregates_out: list[dict[str, Any]] = []
    records = payload.get("records")
    if not isinstance(records, list):
        records = [payload]

    captured_at = _parse_iso(str(manifest["captured_at"]))
    for idx, item in enumerate(records):
        if not isinstance(item, dict):
            continue
        donation_record = _normalize_donation_record(
            item,
            capture_id=str(manifest["capture_id"]),
            source=str(manifest["source"]),
            source_url=str(manifest["source_url"]),
            captured_at=captured_at,
            evidence_reference=evidence_reference,
            extraction_method="structured_export",
            default_index=idx,
        )
        if donation_record:
            records_out.append(donation_record)
        aggregate_record = _normalize_aggregate_observation(
            item,
            capture_id=str(manifest["capture_id"]),
            source=str(manifest["source"]),
            source_url=str(manifest["source_url"]),
            captured_at=captured_at,
            evidence_reference=evidence_reference,
            extraction_method="structured_export",
        )
        if aggregate_record:
            aggregates_out.append(aggregate_record)
    return records_out, aggregates_out


def _extract_from_html_text(
    html_text: str,
    *,
    manifest: dict[str, Any],
    evidence_reference: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = " ".join(re.sub(r"<[^>]+>", " ", html_text).split())
    aggregates: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    raised_match = re.search(r"\$?\s*([\d,]+(?:\.\d{1,2})?)\s+(?:raised|funded)", text, re.IGNORECASE)
    goal_match = re.search(r"(?:goal|of)\s+\$?\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    donor_count_match = re.search(r"([\d,]+)\s+(?:donations|donors)", text, re.IGNORECASE)

    aggregate_hint = {
        "fundraiser_total": raised_match.group(1) if raised_match else None,
        "fundraiser_goal": goal_match.group(1) if goal_match else None,
        "displayed_donation_count": donor_count_match.group(1) if donor_count_match else None,
    }
    aggregate = _normalize_aggregate_observation(
        aggregate_hint,
        capture_id=str(manifest["capture_id"]),
        source=str(manifest["source"]),
        source_url=str(manifest["source_url"]),
        captured_at=_parse_iso(str(manifest["captured_at"])),
        evidence_reference=evidence_reference,
        extraction_method="known_html" if any(aggregate_hint.values()) else "pattern_text",
    )
    if aggregate:
        aggregates.append(aggregate)
    return records, aggregates


def _extract_for_artifact(
    pack_dir: Path,
    artifact: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rel_path = str(artifact["path"])
    media_type = str(artifact["media_type"])
    artifact_path = pack_dir / rel_path
    evidence_reference = f"{manifest['capture_id']}:{rel_path}"
    events: list[dict[str, Any]] = []

    if media_type in JSON_MEDIA_TYPES or artifact_path.suffix.lower() == ".json":
        payload = _load_json(artifact_path, {})
        if isinstance(payload, dict):
            records, aggregates = _extract_from_structured_payload(payload, manifest=manifest, evidence_reference=evidence_reference)
            return records, aggregates, events
        events.append(_manifest_event(str(manifest["capture_id"]), "CAPTURE_PARSE_WARNING", {"artifact": rel_path, "reason": "json payload is not object"}))
        return [], [], events

    if media_type in HTML_MEDIA_TYPES or artifact_path.suffix.lower() in {".html", ".htm"}:
        html_text = artifact_path.read_text(encoding="utf-8", errors="ignore")
        records, aggregates = _extract_from_html_text(html_text, manifest=manifest, evidence_reference=evidence_reference)
        return records, aggregates, events

    if media_type in IMAGE_MEDIA_TYPES:
        events.append(
            _manifest_event(
                str(manifest["capture_id"]),
                "OCR_FALLBACK_REQUIRED",
                {"artifact": rel_path, "reason": "image artifact needs manual/OCR review"},
            )
        )
    return [], [], events


def _review_item(source_id: str, claim: str, evidence: str, risk_level: str = "MEDIUM_RISK") -> dict[str, Any]:
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


def ingest_capture_packs(data_dir: Path) -> dict[str, Any]:
    captures_root = data_dir / "captures"
    state_path = data_dir / "research" / "capture_ingestion_state.json"
    quarantine_path = data_dir / "review" / "capture_quarantine.json"
    review_queue_path = data_dir / "review" / "queue.json"
    manual_export_path = data_dir / "raw" / "gofundme_manual_export.json"
    aggregate_path = data_dir / "research" / "fundraiser_observations.json"
    events_path = data_dir / "events" / "capture_events.jsonl"
    source_health_path = data_dir / "research" / "capture_source_health.json"

    state = _load_json(state_path, {"processed_manifest_hashes": {}})
    processed_hashes = dict(state.get("processed_manifest_hashes", {}))
    quarantine = _load_json(quarantine_path, [])
    review_queue = _load_json(review_queue_path, [])
    existing_export = _load_json(manual_export_path, {"records": []})
    existing_records = existing_export.get("records", []) if isinstance(existing_export, dict) else []
    existing_aggregates = _load_json(aggregate_path, [])

    canonical_by_id = {str(rec.get("donation_id")): rec for rec in existing_records if isinstance(rec, dict) and rec.get("donation_id")}
    aggregate_by_id = {
        str(obs.get("observation_id")): obs for obs in existing_aggregates if isinstance(obs, dict) and obs.get("observation_id")
    }
    existing_conflicts = {
        str(item.get("evidence", ""))
        for item in review_queue
        if isinstance(item, dict) and str(item.get("claim", "")).lower() == "conflict_detected"
    }

    seen = 0
    accepted = 0
    quarantined = 0
    records_added = 0
    records_updated = 0
    aggregates_added = 0
    conflicts = 0
    channel_counts: dict[str, int] = {key: 0 for key in sorted(ALLOWED_SOURCES)}
    events: list[dict[str, Any]] = []

    if not captures_root.exists():
        _save_json(source_health_path, {"sources": [], "summary": {"captures_seen": 0, "captures_accepted": 0}})
        return {
            "capture_packs_seen": 0,
            "capture_packs_accepted": 0,
            "capture_packs_quarantined": 0,
            "records_added": 0,
            "records_updated": 0,
            "aggregate_observations_added": 0,
            "conflicts_detected": 0,
        }

    pack_dirs = sorted([path for path in captures_root.iterdir() if path.is_dir()])
    for pack_dir in pack_dirs:
        manifest_path = pack_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        seen += 1
        raw_manifest = manifest_path.read_text(encoding="utf-8")
        manifest_hash = hashlib.sha256(raw_manifest.encode("utf-8")).hexdigest()
        capture_id = pack_dir.name
        if processed_hashes.get(capture_id) == manifest_hash:
            continue

        try:
            manifest = json.loads(raw_manifest)
        except json.JSONDecodeError:
            quarantined += 1
            quarantine.append({"capture_dir": str(pack_dir), "reasons": ["manifest is not valid json"], "timestamp": datetime.now(UTC).isoformat()})
            continue

        reasons = validate_capture_manifest(manifest)
        artifacts = manifest.get("artifacts", [])
        if isinstance(artifacts, list):
            reasons.extend(_verify_artifact_hashes(pack_dir, artifacts))
        else:
            reasons.append("artifacts must be list")

        if reasons:
            quarantined += 1
            quarantine.append(
                {
                    "capture_id": manifest.get("capture_id", capture_id),
                    "capture_dir": str(pack_dir),
                    "reasons": reasons,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            events.append(_manifest_event(str(manifest.get("capture_id", capture_id)), "CAPTURE_QUARANTINED", {"reasons": reasons}))
            continue

        accepted += 1
        source = str(manifest["source"])
        channel_counts[source] = channel_counts.get(source, 0) + 1
        pack_records: list[dict[str, Any]] = []
        pack_aggregates: list[dict[str, Any]] = []
        for artifact in artifacts:
            recs, aggs, artifact_events = _extract_for_artifact(pack_dir, artifact, manifest)
            pack_records.extend(recs)
            pack_aggregates.extend(aggs)
            events.extend(artifact_events)

        for record in pack_records:
            key = str(record["donation_id"])
            current = canonical_by_id.get(key)
            if current is None:
                canonical_by_id[key] = record
                records_added += 1
                continue
            new_rank = CONFIDENCE_RANK.get(str(record.get("confidence", "UNRESOLVED")), 0)
            old_rank = CONFIDENCE_RANK.get(str(current.get("confidence", "UNRESOLVED")), 0)
            if new_rank > old_rank:
                canonical_by_id[key] = record
                records_updated += 1
                continue
            if new_rank == old_rank and current != record:
                conflict_key = f"donation:{key}"
                if conflict_key not in existing_conflicts:
                    review_queue.append(
                        _review_item(
                            "gofundme-fundraiser-page",
                            "conflict_detected",
                            conflict_key,
                            "HIGH_RISK",
                        )
                    )
                    existing_conflicts.add(conflict_key)
                    conflicts += 1
                events.append(
                    _manifest_event(
                        str(manifest["capture_id"]),
                        "CONFLICT_DETECTED",
                        {"field": "donation_record", "record_id": key},
                    )
                )

        for aggregate in pack_aggregates:
            oid = str(aggregate["observation_id"])
            if oid not in aggregate_by_id:
                aggregate_by_id[oid] = aggregate
                aggregates_added += 1

        processed_hashes[capture_id] = manifest_hash

    aggregate_values_by_day: dict[tuple[str, str], set[str]] = {}
    aggregate_sources_by_day: dict[tuple[str, str], set[str]] = {}
    for observation in aggregate_by_id.values():
        observed_at = str(observation.get("observed_at", ""))
        observed_day = observed_at[:10] if len(observed_at) >= 10 else "UNKNOWN"
        for field in ("fundraiser_total", "fundraiser_goal", "displayed_donation_count"):
            value = observation.get(field)
            if value is None:
                continue
            aggregate_key = (observed_day, field)
            aggregate_values_by_day.setdefault(aggregate_key, set()).add(str(value))
            aggregate_sources_by_day.setdefault(aggregate_key, set()).add(str(observation.get("source", "UNKNOWN")))

    for aggregate_key, values in aggregate_values_by_day.items():
        if len(values) <= 1:
            continue
        day, field = aggregate_key
        conflict_key = f"aggregate:{day}:{field}:{'|'.join(sorted(values))}"
        if conflict_key in existing_conflicts:
            continue
        review_queue.append(
            _review_item(
                "gofundme-fundraiser-page",
                "conflict_detected",
                conflict_key,
                "HIGH_RISK",
            )
        )
        events.append(
            _manifest_event(
                "aggregate",
                "CONFLICT_DETECTED",
                {
                    "field": field,
                    "observed_day": day,
                    "values": sorted(values),
                    "sources": sorted(aggregate_sources_by_day.get(aggregate_key, set())),
                },
            )
        )
        conflicts += 1
        existing_conflicts.add(conflict_key)

    canonical_records = sorted(canonical_by_id.values(), key=lambda item: str(item.get("donation_id", "")))
    aggregate_records = sorted(aggregate_by_id.values(), key=lambda item: str(item.get("observed_at", "")))
    _save_json(
        manual_export_path,
        {
            "status": "AUTOGENERATED_FROM_CAPTURE_PACKS",
            "message": "Generated from validated capture packs. Do not edit manually.",
            "records": canonical_records,
        },
    )
    _save_json(aggregate_path, aggregate_records)
    _save_json(quarantine_path, quarantine)
    _save_json(review_queue_path, review_queue)
    _save_json(state_path, {"processed_manifest_hashes": processed_hashes, "last_run": datetime.now(UTC).isoformat()})
    _append_jsonl(events_path, events)

    sources_payload = []
    for source_name in sorted(ALLOWED_SOURCES):
        count = int(channel_counts.get(source_name, 0))
        status = "HEALTHY" if count > 0 else "STALE"
        sources_payload.append(
            {
                "source": source_name,
                "last_success": datetime.now(UTC).isoformat() if count > 0 else None,
                "last_attempt": datetime.now(UTC).isoformat(),
                "last_change": datetime.now(UTC).isoformat() if count > 0 else None,
                "record_count": len(canonical_records),
                "aggregate_observations": len(aggregate_records),
                "status": status,
                "failure_reason": None if count > 0 else "NO_CAPTURE_PACKS",
                "parser_version": "capture-pack-v1",
            }
        )
    _save_json(
        source_health_path,
        {
            "sources": sources_payload,
            "summary": {
                "captures_seen": seen,
                "captures_accepted": accepted,
                "captures_quarantined": quarantined,
                "records_added": records_added,
                "records_updated": records_updated,
                "aggregate_observations_added": aggregates_added,
                "conflicts_detected": conflicts,
            },
        },
    )

    return {
        "capture_packs_seen": seen,
        "capture_packs_accepted": accepted,
        "capture_packs_quarantined": quarantined,
        "records_added": records_added,
        "records_updated": records_updated,
        "aggregate_observations_added": aggregates_added,
        "conflicts_detected": conflicts,
    }


def _copy_artifact(src: Path, dst: Path) -> dict[str, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    suffix = src.suffix.lower()
    if suffix in {".html", ".htm"}:
        media_type = "text/html"
    elif suffix == ".json":
        media_type = "application/json"
    elif suffix in {".png"}:
        media_type = "image/png"
    elif suffix in {".jpg", ".jpeg"}:
        media_type = "image/jpeg"
    elif suffix in {".webp"}:
        media_type = "image/webp"
    else:
        media_type = "application/octet-stream"
    return {"path": dst.name, "sha256": _sha256_file(dst), "media_type": media_type}


def create_capture_pack(
    *,
    data_dir: Path,
    source: str,
    source_url: str,
    capture_type: str,
    collector_version: str,
    html_path: Path | None = None,
    export_path: Path | None = None,
    screenshot_paths: list[Path] | None = None,
    metadata_path: Path | None = None,
    notes: str | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    if source not in ALLOWED_SOURCES:
        raise ValueError("source must be authorized_capture|public_reporting|archive")
    if capture_type not in ALLOWED_CAPTURE_TYPES:
        raise ValueError("capture_type must be html|screenshot|export|archive|mixed")

    now_iso = _parse_iso(captured_at)
    stamp = now_iso.replace(":", "-").replace("+00:00", "Z")
    capture_id = f"{stamp}-{uuid4().hex[:8]}"
    pack_dir = data_dir / "captures" / capture_id
    pack_dir.mkdir(parents=True, exist_ok=False)

    artifacts: list[dict[str, str]] = []
    if html_path is not None:
        artifacts.append(_copy_artifact(html_path, pack_dir / "page.html"))
    if export_path is not None:
        artifacts.append(_copy_artifact(export_path, pack_dir / "export.json"))
    for index, screenshot in enumerate(screenshot_paths or []):
        artifacts.append(_copy_artifact(screenshot, pack_dir / f"screenshot-{index + 1}{screenshot.suffix.lower()}"))
    if metadata_path is not None:
        artifacts.append(_copy_artifact(metadata_path, pack_dir / "metadata.json"))
    elif notes:
        payload = {"notes": notes, "created_at": datetime.now(UTC).isoformat()}
        metadata_file = pack_dir / "metadata.json"
        metadata_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        artifacts.append({"path": metadata_file.name, "sha256": _sha256_file(metadata_file), "media_type": "application/json"})

    if not artifacts:
        raise ValueError("at least one artifact must be provided")

    manifest = {
        "capture_id": capture_id,
        "source": source,
        "source_url": source_url,
        "captured_at": now_iso,
        "collector_version": collector_version,
        "capture_type": capture_type,
        "artifacts": artifacts,
    }
    errors = validate_capture_manifest(manifest)
    if errors:
        raise ValueError("; ".join(errors))
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"capture_id": capture_id, "capture_dir": str(pack_dir), "manifest": manifest}


def git_commit_capture_pack(repo_root: Path, capture_dir: Path, message: str) -> None:
    rel_dir = capture_dir.relative_to(repo_root)
    subprocess.run(["git", "add", str(rel_dir)], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_root, check=True)
