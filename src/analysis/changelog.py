from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


def append_changelog(path: Path, previous_version: str, new_version: str, records_added: int, records_modified: int, records_removed: int, sources_changed: int) -> None:
    if not path.exists():
        path.write_text("# CHANGELOG\n\n", encoding="utf-8")
    entry = (
        f"## {new_version} - {datetime.now(UTC).date().isoformat()}\n"
        f"- previous version: {previous_version}\n"
        f"- records added: {records_added}\n"
        f"- records modified: {records_modified}\n"
        f"- records removed: {records_removed}\n"
        f"- sources changed: {sources_changed}\n\n"
    )
    with path.open("a", encoding="utf-8") as fh:
        fh.write(entry)
