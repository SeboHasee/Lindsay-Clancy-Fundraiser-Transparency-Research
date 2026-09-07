from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ReviewQueueItem:
    record_id: str
    claim: str
    evidence: str
    reason: str
    status: str = "pending"
    reviewer: str = "UNKNOWN"
    review_timestamp: str = "UNKNOWN"


def enqueue_identity_claim(donation: dict, claim: str, evidence: str, reason: str) -> ReviewQueueItem:
    if donation.get("anonymous_indicator"):
        raise ValueError("Anonymous donation records cannot enter identity-resolution workflows")
    return ReviewQueueItem(record_id=donation["donation_id"], claim=claim, evidence=evidence, reason=reason)
