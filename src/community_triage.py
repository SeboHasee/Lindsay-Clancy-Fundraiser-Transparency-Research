from __future__ import annotations

from typing import Any


def classify_submission(item: dict[str, Any]) -> str:
    claim = (item.get("claim") or "").lower()
    evidence = (item.get("evidence") or "").strip()

    if "anonymous donor" in claim or "identify anonymous" in claim:
        return "PRIVACY_RISK"
    if "bug" in claim:
        return "BUG"
    if "method" in claim:
        return "METHODOLOGY_SUGGESTION"
    if "verify" in claim or "public figure" in claim or "organization" in claim:
        return "IDENTITY_CLAIM"
    if "source" in claim and evidence:
        return "VALID_SOURCE"
    if "source" in claim and not evidence:
        return "MISSING_SOURCE"
    if "correction" in claim or "incorrect" in claim:
        return "DATA_CORRECTION"
    return "CONFLICT"
