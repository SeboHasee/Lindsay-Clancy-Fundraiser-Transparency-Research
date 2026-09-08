import pytest

from src.verification.review_queue import enqueue_identity_claim


def test_anonymous_records_are_blocked_from_identity_queue() -> None:
    donation = {"donation_id": "d1", "anonymous_indicator": True}
    with pytest.raises(ValueError, match="Anonymous donation records"):
        enqueue_identity_claim(donation, "claim", "evidence", "reason")
