import json
from pathlib import Path

import pytest

from src.publication.filtering import apply_publication_filter


def test_publication_filter_blocks_sensitive_strings(tmp_path: Path) -> None:
    classification = {
        "donation_id": "PUBLIC",
        "displayed_message": "PUBLIC",
        "email": "PROHIBITED",
    }
    path = tmp_path / "classification.json"
    path.write_text(json.dumps(classification), encoding="utf-8")

    records = [{"donation_id": "1", "displayed_message": "contact me at test@example.com", "email": "x@y.com"}]

    with pytest.raises(ValueError):
        apply_publication_filter(records, path)
