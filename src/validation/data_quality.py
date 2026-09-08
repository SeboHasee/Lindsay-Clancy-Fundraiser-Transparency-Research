from __future__ import annotations

from datetime import UTC, datetime

ALLOWED_CURRENCIES = {"USD"}


def _parse_iso(value: str) -> datetime | None:
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def validate_donation_records(records: list[dict]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_observations: set[tuple[str, str, str]] = set()
    record_snapshots: dict[str, tuple[str | None, str | None]] = {}
    now = datetime.now(UTC)

    for record in records:
        rid = record.get("donation_id", "UNKNOWN")
        if rid in seen_ids:
            issues.append({"record_id": rid, "issue": "duplicate donation id"})
        seen_ids.add(rid)

        if not record.get("source_url"):
            issues.append({"record_id": rid, "issue": "missing source url"})
        if not record.get("evidence_reference"):
            issues.append({"record_id": rid, "issue": "missing provenance"})
        if not record.get("collection_timestamp"):
            issues.append({"record_id": rid, "issue": "missing collection timestamp"})

        amount = record.get("normalized_amount")
        if amount is not None and amount < 0:
            issues.append({"record_id": rid, "issue": "invalid amount"})

        currency = record.get("currency")
        if currency is not None and currency not in ALLOWED_CURRENCIES:
            issues.append({"record_id": rid, "issue": "invalid currency"})

        dt = record.get("normalized_datetime")
        if dt:
            parsed = _parse_iso(dt)
            if parsed is None:
                issues.append({"record_id": rid, "issue": "malformed date"})
            elif parsed > now:
                issues.append({"record_id": rid, "issue": "future date"})

        if record.get("anonymous_indicator") and record.get("displayed_donor_name"):
            issues.append({"record_id": rid, "issue": "inconsistent anonymous flag"})

        obs_key = (
            str(record.get("source_id", "")),
            str(record.get("donation_id", "")),
            str(record.get("collection_timestamp", "")),
        )
        if obs_key in seen_observations:
            issues.append({"record_id": rid, "issue": "duplicate observation"})
        seen_observations.add(obs_key)

        if rid in record_snapshots:
            previous_amount, previous_name = record_snapshots[rid]
            if previous_amount != str(record.get("displayed_amount")):
                issues.append({"record_id": rid, "issue": "conflicting amounts"})
            if previous_name != str(record.get("displayed_donor_name")):
                issues.append({"record_id": rid, "issue": "conflicting names"})
        record_snapshots[rid] = (str(record.get("displayed_amount")), str(record.get("displayed_donor_name")))

        entity_ref = record.get("entity_id")
        if entity_ref is not None and not str(entity_ref).strip():
            issues.append({"record_id": rid, "issue": "invalid entity reference"})

    return issues
