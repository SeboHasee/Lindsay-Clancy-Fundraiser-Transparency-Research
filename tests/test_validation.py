from src.validation.data_quality import validate_donation_records


def test_validation_flags_inconsistent_anonymous_and_name() -> None:
    issues = validate_donation_records([
        {
            "donation_id": "d1",
            "source_url": "https://example.test",
            "evidence_reference": "ev1",
            "collection_timestamp": "2026-09-07T00:00:00Z",
            "displayed_donor_name": "Name",
            "anonymous_indicator": True,
            "displayed_amount": "$10",
            "verification_status": "UNVERIFIED",
            "confidence": "LOW",
        }
    ])
    assert any(i["issue"] == "inconsistent anonymous flag" for i in issues)
