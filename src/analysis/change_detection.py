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
