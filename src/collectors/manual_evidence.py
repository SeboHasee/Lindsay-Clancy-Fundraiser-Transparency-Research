from __future__ import annotations

from .base import BaseCollector, CollectorResult


class ManualEvidenceCollector(BaseCollector):
    collector_name = "manual_evidence"

    def collect(self) -> CollectorResult:
        return CollectorResult(
            source_id="NOT_AVAILABLE",
            collection_timestamp=self.now_iso(),
            records=[],
            warnings=["No input provided"],
            coverage={"status": "partially_observable"},
            provenance={"method": self.collector_name},
        )
