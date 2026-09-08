from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_export_defaults_to_public_mode(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    data_research = repo / "data" / "research"
    data_public = repo / "data" / "public"
    data_research.mkdir(parents=True, exist_ok=True)
    data_public.mkdir(parents=True, exist_ok=True)
    donations_path = data_research / "donations.json"
    public_path = data_public / "donations.public.json"
    original_donations = donations_path.read_text(encoding="utf-8") if donations_path.exists() else "[]"
    original_public = public_path.read_text(encoding="utf-8") if public_path.exists() else "[]"

    sample = [
        {
            "donation_id": "d1",
            "source_id": "s1",
            "source_url": "https://example.test",
            "displayed_amount": "$10",
            "normalized_amount": 10,
            "anonymous_indicator": False,
        }
    ]
    try:
        donations_path.write_text(json.dumps(sample), encoding="utf-8")
        subprocess.run(["python", "-m", "research", "export"], cwd=repo, check=True)
        exported = json.loads(public_path.read_text(encoding="utf-8"))
        assert isinstance(exported, list)
    finally:
        donations_path.write_text(original_donations, encoding="utf-8")
        public_path.write_text(original_public, encoding="utf-8")
