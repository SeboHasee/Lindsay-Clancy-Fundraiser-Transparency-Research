from src.analysis.change_detection import detect_donation_record_changes


def test_detect_donation_add_modify_remove() -> None:
    prev = [{"donation_id": "a", "displayed_amount": "$10"}, {"donation_id": "b", "displayed_amount": "$20"}]
    curr = [{"donation_id": "a", "displayed_amount": "$11"}, {"donation_id": "c", "displayed_amount": "$30"}]
    events = detect_donation_record_changes(prev, curr, "src", "2026-09-07T00:00:00Z")
    kinds = {e["event_type"] for e in events}
    assert "DONATION_RECORD_ADDED" in kinds
    assert "DONATION_RECORD_MODIFIED" in kinds
    assert "DONATION_RECORD_REMOVED" in kinds
