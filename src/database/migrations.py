from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  canonical_url TEXT,
  source_type TEXT,
  publisher TEXT,
  reliability TEXT,
  limitations TEXT
);
CREATE TABLE IF NOT EXISTS snapshots (
  snapshot_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  source_url TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  reported_total_raised TEXT,
  reported_goal TEXT,
  reported_donation_count TEXT,
  page_metadata TEXT,
  source_hash TEXT,
  coverage_notes TEXT,
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);
CREATE TABLE IF NOT EXISTS donations (
  donation_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  source_url TEXT NOT NULL,
  displayed_donor_name TEXT,
  displayed_amount TEXT NOT NULL,
  normalized_amount REAL,
  currency TEXT,
  displayed_date TEXT,
  normalized_datetime TEXT,
  displayed_message TEXT,
  anonymous_indicator INTEGER NOT NULL DEFAULT 0,
  verification_status TEXT NOT NULL,
  confidence TEXT NOT NULL,
  evidence_reference TEXT NOT NULL,
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);
CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,
  record_id TEXT NOT NULL,
  claim TEXT NOT NULL,
  evidence TEXT NOT NULL,
  status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS organizations (
  organization_id TEXT PRIMARY KEY,
  organization_name TEXT NOT NULL,
  official_url TEXT,
  organization_type TEXT,
  official_source TEXT,
  verification_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  event_date TEXT NOT NULL,
  event_type TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  source TEXT,
  confidence TEXT
);
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  record_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_timestamp TEXT,
  collection_timestamp TEXT NOT NULL,
  observed_value TEXT,
  normalized_value TEXT,
  verification_status TEXT,
  confidence TEXT,
  evidence_reference TEXT,
  notes TEXT,
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);
CREATE TABLE IF NOT EXISTS conflicts (
  conflict_id TEXT PRIMARY KEY,
  field TEXT NOT NULL,
  source_a TEXT NOT NULL,
  value_a TEXT,
  source_b TEXT NOT NULL,
  value_b TEXT,
  resolution_status TEXT NOT NULL,
  resolution_reason TEXT,
  preferred_value TEXT,
  preferred_source TEXT
);
CREATE TABLE IF NOT EXISTS collection_runs (
  run_id TEXT PRIMARY KEY,
  start_time TEXT NOT NULL,
  end_time TEXT,
  collector TEXT NOT NULL,
  source TEXT NOT NULL,
  records_seen INTEGER,
  records_added INTEGER,
  records_changed INTEGER,
  records_rejected INTEGER,
  errors TEXT,
  warnings TEXT,
  coverage TEXT,
  software_version TEXT,
  dataset_version TEXT
);
CREATE TABLE IF NOT EXISTS verification_records (
  verification_id TEXT PRIMARY KEY,
  record_id TEXT NOT NULL,
  identity_claim TEXT NOT NULL,
  evidence TEXT NOT NULL,
  source TEXT NOT NULL,
  confidence TEXT NOT NULL,
  verification_date TEXT NOT NULL,
  review_status TEXT NOT NULL,
  match_reason TEXT NOT NULL
);
"""


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
