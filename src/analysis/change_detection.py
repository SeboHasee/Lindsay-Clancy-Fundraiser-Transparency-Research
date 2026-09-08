from __future__ import annotations

from typing import Any

EVENT_MAP = {
    "reported_goal": "GOAL_CHANGED",
    "reported_total_raised": "AMOUNT_CHANGED",
    "reported_donation_count": "DONATION_COUNT_CHANGED",
    "description": "DESCRIPTION_CHANGED",
    "organizer": "ORGANIZER_CHANGED",
    "beneficiary": "BENEFICIARY_CHANGED",
}


def detect_changes(previous: dict[str, Any], current: dict[str, Any], source: str, event_date: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for field, event_type in EVENT_MAP.items():
        old_value = previous.get(field)
        new_value = current.get(field)
        if old_value != new_value:
            events.append(
                {
                    "event_date": event_date,
                    "event_type": event_type,
                    "old_value": old_value,
                    "new_value": new_value,
                    "source": source,
                    "confidence": "MEDIUM",
                }
            )
    return events


def detect_donation_record_changes(previous_records: list[dict[str, Any]], current_records: list[dict[str, Any]], source: str, event_date: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    previous_by_id = {r.get("donation_id"): r for r in previous_records if r.get("donation_id")}
    current_by_id = {r.get("donation_id"): r for r in current_records if r.get("donation_id")}

    for donation_id, record in current_by_id.items():
        if donation_id not in previous_by_id:
            events.append(
                {
                    "event_date": event_date,
                    "event_type": "DONATION_RECORD_ADDED",
                    "old_value": None,
                    "new_value": record,
                    "source": source,
                    "confidence": "MEDIUM",
                }
            )
        elif previous_by_id[donation_id] != record:
            events.append(
                {
                    "event_date": event_date,
                    "event_type": "DONATION_RECORD_MODIFIED",
                    "old_value": previous_by_id[donation_id],
                    "new_value": record,
                    "source": source,
                    "confidence": "MEDIUM",
                }
            )

    for donation_id, record in previous_by_id.items():
        if donation_id not in current_by_id:
            events.append(
                {
                    "event_date": event_date,
                    "event_type": "DONATION_RECORD_REMOVED",
                    "old_value": record,
                    "new_value": None,
                    "source": source,
                    "confidence": "LOW",
                }
            )

    return events
