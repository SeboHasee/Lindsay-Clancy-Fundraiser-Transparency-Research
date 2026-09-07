# Architecture

## Main components

- `src/sources/`: modular source adapters (`discover`, `fetch`, `parse`, `normalize`, `validate`, `fingerprint`, `compare`, `produce_evidence`).
- `src/monitoring/engine.py`: scheduled monitoring, change detection, fallback handling, backoff, health output.
- `src/validation/`: data quality checks.
- `src/analysis/`: statistics, coverage, changelog, and report generation.
- `src/publication/`: privacy sanitizer and publication filter.
- `src/database/`: SQLite schema/migrations.

## Data flow

Sources -> observations/evidence -> validation -> review routing -> analysis -> reports/public export.

High-risk changes are review-gated.
