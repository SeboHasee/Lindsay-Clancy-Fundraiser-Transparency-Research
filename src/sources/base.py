from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any


@dataclass(slots=True)
class SourceMetadata:
    source_id: str
    canonical_url: str
    source_type: str
    publisher: str
    access_method: str
    collection_status: str
    terms_status: str
    reliability: str
    last_checked: str | None = None
    last_successful_collection: str | None = None
    limitations: str = ""
    monitoring_enabled: bool = True
    polling_frequency: str = "daily"
    parser_version: str = "1.0.0"
    error_count: int = 0


@dataclass(slots=True)
class SourceObservation:
    source_id: str
    observed_at_utc: str
    original_datetime: str | None
    original_timezone: str | None
    source_url: str
    payload: dict[str, Any]
    evidence_reference: str
    content_hash: str


@dataclass(slots=True)
class SourceResult:
    metadata: SourceMetadata
    records: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    observation: SourceObservation | None = None
    source_state: str = "SOURCE_HEALTHY"
    coverage: dict[str, Any] = field(default_factory=dict)


class BaseSourceAdapter(ABC):
    parser_version = "1.0.0"

    def __init__(self, metadata: SourceMetadata) -> None:
        self.metadata = metadata

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def fingerprint(payload: dict[str, Any]) -> str:
        return sha256(str(sorted(payload.items())).encode("utf-8")).hexdigest()

    @abstractmethod
    def discover(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, parsed: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def validate(self, normalized: list[dict[str, Any]]) -> list[str]:
        raise NotImplementedError

    def compare(self, old_hash: str | None, new_hash: str) -> bool:
        return old_hash != new_hash

    def produce_evidence(self, parsed: dict[str, Any], source_url: str) -> SourceObservation:
        now = self.now_iso()
        return SourceObservation(
            source_id=self.metadata.source_id,
            observed_at_utc=now,
            original_datetime=now,
            original_timezone="UTC",
            source_url=source_url,
            payload=parsed,
            evidence_reference=f"{self.metadata.source_id}:{now}",
            content_hash=self.fingerprint(parsed),
        )

    def run(self) -> SourceResult:
        raw = self.fetch()
        parsed = self.parse(raw)
        normalized = self.normalize(parsed)
        validation_errors = self.validate(normalized)
        obs = self.produce_evidence(parsed, self.metadata.canonical_url)
        warnings: list[str] = []
        source_state = "SOURCE_HEALTHY"
        if isinstance(parsed, dict):
            status = str(parsed.get("status", "")).upper()
            if status in {"NO_MANUAL_FILE", "FALLBACK_REQUIRED"}:
                source_state = "SOURCE_NOT_AUTOMATED"
            elif status in {"PARSER_ERROR", "STRUCTURE_CHANGED"}:
                source_state = "SOURCE_PARSER_ERROR"
            elif status in {"EMPTY"}:
                source_state = "SOURCE_EMPTY"
            if parsed.get("message"):
                warnings.append(str(parsed["message"]))
        return SourceResult(
            metadata=self.metadata,
            records=normalized,
            warnings=warnings,
            errors=validation_errors,
            observation=obs,
            source_state=source_state,
            coverage={"record_count": len(normalized)},
        )
