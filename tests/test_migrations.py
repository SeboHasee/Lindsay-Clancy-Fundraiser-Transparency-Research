import sqlite3
from pathlib import Path

from src.database.migrations import initialize_database


def test_migrations_create_required_tables(tmp_path: Path) -> None:
    db = tmp_path / "research.sqlite"
    initialize_database(db)
    with sqlite3.connect(db) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "community_submissions" in tables
    assert "review_queue" in tables
    assert "dataset_versions" in tables
    assert "audit_log" in tables
