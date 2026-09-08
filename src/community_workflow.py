from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.community_triage import classify_submission


@dataclass(slots=True)
class SubmissionValidationResult:
    valid: bool
    errors: list[str]


def validate_submission(submission: dict[str, Any]) -> SubmissionValidationResult:
    errors: list[str] = []
    for required in ("claim", "source", "evidence"):
        if not str(submission.get(required, "")).strip():
            errors.append(f"missing_{required}")
    return SubmissionValidationResult(valid=not errors, errors=errors)


def dedupe_submission(submission: dict[str, Any], existing: list[dict[str, Any]]) -> bool:
    signature = (
        str(submission.get("claim", "")).strip().lower(),
        str(submission.get("source", "")).strip().lower(),
        str(submission.get("evidence", "")).strip().lower(),
    )
    for row in existing:
        other = (
            str(row.get("claim", "")).strip().lower(),
            str(row.get("source", "")).strip().lower(),
            str(row.get("evidence", "")).strip().lower(),
        )
        if signature == other:
            return True
    return False


def process_submissions(submissions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    processed: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []

    for entry in submissions:
        item = dict(entry)
        item.setdefault("submission_id", str(uuid4()))
        item.setdefault("timestamp", datetime.now(UTC).isoformat())
        item.setdefault("status", "SUBMITTED")
        item["classification"] = classify_submission(item)

        if item["classification"] == "PRIVACY_RISK":
            item["status"] = "REJECTED"
            item["validation_errors"] = ["privacy_risk"]
            processed.append(item)
            continue

        if dedupe_submission(item, processed):
            item["status"] = "REJECTED"
            item["validation_errors"] = ["duplicate_submission"]
            processed.append(item)
            continue

        validation = validate_submission(item)
        if not validation.valid:
            item["status"] = "NEEDS_MORE_EVIDENCE"
            item["validation_errors"] = validation.errors
            processed.append(item)
            continue

        item["status"] = "PENDING_REVIEW"
        processed.append(item)
        review_items.append(
            {
                "review_id": str(uuid4()),
                "source": item.get("source", "UNKNOWN"),
                "claim": item.get("claim", "UNKNOWN"),
                "evidence": item.get("evidence", "UNKNOWN"),
                "affected_record": item.get("affected_record", "UNKNOWN"),
                "submitter": item.get("contributor", "community"),
                "risk_level": "HIGH_RISK" if item["classification"] == "IDENTITY_CLAIM" else "MEDIUM_RISK",
                "status": "PENDING_REVIEW",
                "reviewer": "UNASSIGNED",
                "decision": "PENDING",
                "decision_timestamp": "UNKNOWN",
            }
        )

    return processed, review_items
