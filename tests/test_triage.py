from src.community_triage import classify_submission


def test_triage_flags_anonymous_identification_as_privacy_risk() -> None:
    result = classify_submission({"claim": "Please identify anonymous donor", "evidence": ""})
    assert result == "PRIVACY_RISK"
