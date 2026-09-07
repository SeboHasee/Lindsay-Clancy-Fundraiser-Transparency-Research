from __future__ import annotations

from datetime import datetime, timezone

ALLOWED_CURRENCIES = {"USD"}


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def validate_donation_records(records: list[dict]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    now = datetime.now(timezone.utc)

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

    return issues
