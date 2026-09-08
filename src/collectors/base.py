from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class CollectorResult:
    source_id: str
    collection_timestamp: str
    records: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)


class BaseCollector:
    collector_name = "base"

    def collect(self) -> CollectorResult:
        raise NotImplementedError

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()
