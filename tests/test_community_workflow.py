from src.community_workflow import process_submissions


def test_community_submissions_are_validated_and_queued() -> None:
    submissions = [
        {
            "claim": "Data correction for amount",
            "source": "https://example.test",
            "evidence": "screenshot hash",
            "contributor": "user1",
        },
        {
            "claim": "Please identify anonymous donor",
            "source": "https://example.test",
            "evidence": "speculation",
            "contributor": "user2",
        },
    ]
    processed, queue = process_submissions(submissions)
    assert processed[0]["status"] == "PENDING_REVIEW"
    assert processed[1]["status"] == "REJECTED"
    assert queue and queue[0]["status"] == "PENDING_REVIEW"
