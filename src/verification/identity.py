from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class IdentityClaim:
    identity_claim: str
    evidence: str
    source: str
    confidence: str
    verification_date: str
    review_status: str
    match_reason: str


def validate_identity_claim(claim: IdentityClaim) -> bool:
    required = [
        claim.identity_claim,
        claim.evidence,
        claim.source,
        claim.confidence,
        claim.verification_date,
        claim.review_status,
        claim.match_reason,
    ]
    return all(bool(item) for item in required)
