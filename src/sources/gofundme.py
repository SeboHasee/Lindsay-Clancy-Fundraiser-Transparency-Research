from __future__ import annotations

from pathlib import Path

from .base import SourceMetadata
from .manual_import import ManualImportAdapter


class GoFundMeAdapter(ManualImportAdapter):
    """Compliance-first adapter: uses manual/authorized inputs only."""

    def __init__(self, metadata: SourceMetadata, data_root: Path) -> None:
        super().__init__(metadata, import_path=data_root / "raw" / "gofundme_manual_export.json")

    def fetch(self) -> dict:
        payload = super().fetch()
        if payload.get("status") == "NO_MANUAL_FILE":
            return {
                "records": [],
                "status": "FALLBACK_REQUIRED",
                "message": "Automated collection not configured; use researcher-provided export or manual evidence.",
            }
        return payload
