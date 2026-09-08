from __future__ import annotations

import json
from pathlib import Path

from .base import BaseSourceAdapter, SourceMetadata


class ManualImportAdapter(BaseSourceAdapter):
    def __init__(self, metadata: SourceMetadata, import_path: Path | None = None) -> None:
        super().__init__(metadata)
        self.import_path = import_path

    def discover(self) -> dict[str, str]:
        return {"mode": "manual_import", "path": str(self.import_path) if self.import_path else "NOT_AVAILABLE"}

    def fetch(self) -> dict:
        if self.import_path is None or not self.import_path.exists():
            return {"records": [], "status": "NO_MANUAL_FILE"}
        return json.loads(self.import_path.read_text(encoding="utf-8"))

    def parse(self, raw: dict) -> dict:
        return raw if isinstance(raw, dict) else {"records": []}

    def normalize(self, parsed: dict) -> list[dict]:
        records = parsed.get("records", [])
        return records if isinstance(records, list) else []

    def validate(self, normalized: list[dict]) -> list[str]:
        return []
