from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .sanitizer import sanitize_or_fail


def apply_publication_filter(records: list[dict[str, Any]], classification_path: Path) -> list[dict[str, Any]]:
    classes = json.loads(classification_path.read_text(encoding="utf-8"))
    public_records: list[dict[str, Any]] = []
    for record in records:
        out: dict[str, Any] = {}
        for key, value in record.items():
            cls = classes.get(key, "RESEARCH_ONLY")
            if cls == "PROHIBITED":
                continue
            if cls in {"PUBLIC", "PUBLIC/REVIEW_REQUIRED"}:
                out[key] = value
        public_records.append(out)
    sanitize_or_fail([{k: str(v) for k, v in rec.items() if v is not None} for rec in public_records])
    return public_records
