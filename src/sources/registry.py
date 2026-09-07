from __future__ import annotations

import json
from pathlib import Path

from .base import SourceMetadata


def load_source_registry(path: Path) -> list[SourceMetadata]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result: list[SourceMetadata] = []
    for item in payload:
        result.append(
            SourceMetadata(
                source_id=item["source_id"],
                canonical_url=item.get("canonical_url", "NOT_AVAILABLE"),
                source_type=item.get("source_type", "unknown"),
                publisher=item.get("publisher", "UNKNOWN"),
                access_method=item.get("access_method", "manual evidence capture"),
                collection_status=item.get("collection_status", "active"),
                terms_status=item.get("authorization_status", "review_required"),
                reliability=item.get("reliability", "E"),
                last_checked=item.get("last_checked"),
                limitations=item.get("limitations", ""),
                monitoring_enabled=item.get("monitoring_enabled", True),
                polling_frequency=item.get("polling_frequency", "daily"),
                parser_version=item.get("parser_version", "1.0.0"),
                error_count=int(item.get("error_count", 0)),
            )
        )
    return result


def write_source_registry(path: Path, records: list[SourceMetadata]) -> None:
    payload = []
    for record in records:
        payload.append(
            {
                "source_id": record.source_id,
                "canonical_url": record.canonical_url,
                "source_type": record.source_type,
                "publisher": record.publisher,
                "access_method": record.access_method,
                "collection_status": record.collection_status,
                "authorization_status": record.terms_status,
                "reliability": record.reliability,
                "last_checked": record.last_checked,
                "last_successful_collection": record.last_successful_collection,
                "limitations": record.limitations,
                "monitoring_enabled": record.monitoring_enabled,
                "polling_frequency": record.polling_frequency,
                "parser_version": record.parser_version,
                "error_count": record.error_count,
            }
        )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
