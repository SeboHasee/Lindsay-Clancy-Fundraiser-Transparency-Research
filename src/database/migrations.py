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
  access_method TEXT,
  collection_status TEXT,
  terms_status TEXT,
  reliability TEXT,
  last_checked TEXT,
  last_successful_collection TEXT,
  limitations TEXT
);
CREATE TABLE IF NOT EXISTS source_observations (
  observation_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  observed_at_utc TEXT NOT NULL,
  original_datetime TEXT,
  original_timezone TEXT,
  source_url TEXT NOT NULL,
  content_hash TEXT,
  payload_json TEXT,
  evidence_reference TEXT,
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
  original_datetime TEXT,
  original_timezone TEXT,
  normalized_datetime_utc TEXT,
  displayed_message TEXT,
  anonymous_indicator INTEGER NOT NULL DEFAULT 0,
  conversion_rate REAL,
  conversion_source TEXT,
  conversion_timestamp TEXT,
  converted_amount REAL,
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
  source TEXT,
  verification_date TEXT,
  confidence TEXT,
  reviewer TEXT,
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
  source_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  event_type TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  evidence TEXT,
  confidence TEXT,
  review_required INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  record_id TEXT,
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
CREATE TABLE IF NOT EXISTS community_submissions (
  submission_id TEXT PRIMARY KEY,
  contributor TEXT,
  timestamp TEXT NOT NULL,
  claim TEXT NOT NULL,
  source TEXT,
  evidence TEXT,
  affected_record TEXT,
  status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_queue (
  review_id TEXT PRIMARY KEY,
  source TEXT,
  claim TEXT NOT NULL,
  evidence TEXT,
  affected_record TEXT,
  submitter TEXT,
  risk_level TEXT,
  status TEXT,
  reviewer TEXT,
  decision TEXT,
  decision_timestamp TEXT
);
CREATE TABLE IF NOT EXISTS conflicts (
  conflict_id TEXT PRIMARY KEY,
  field TEXT NOT NULL,
  source_A TEXT NOT NULL,
  value_A TEXT,
  source_B TEXT NOT NULL,
  value_B TEXT,
  timestamp_A TEXT,
  timestamp_B TEXT,
  evidence TEXT,
  status TEXT NOT NULL,
  resolution TEXT
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
CREATE TABLE IF NOT EXISTS dataset_versions (
  version TEXT PRIMARY KEY,
  previous_version TEXT,
  created_at TEXT NOT NULL,
  records_added INTEGER,
  records_modified INTEGER,
  records_removed INTEGER,
  sources_changed INTEGER,
  methodology_changes TEXT,
  verification_changes TEXT
);
CREATE TABLE IF NOT EXISTS publication_records (
  publication_id TEXT PRIMARY KEY,
  dataset_version TEXT NOT NULL,
  published_at TEXT NOT NULL,
  artifact_path TEXT NOT NULL,
  privacy_scan_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
  audit_id TEXT PRIMARY KEY,
  actor TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  field_name TEXT,
  old_value TEXT,
  new_value TEXT,
  reason TEXT,
  source TEXT,
  reviewer TEXT,
  workflow_run TEXT,
  dataset_version TEXT
);
"""


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
