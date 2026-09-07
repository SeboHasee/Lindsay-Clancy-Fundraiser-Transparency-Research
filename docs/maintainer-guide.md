# Maintainer Guide

## Architecture
- CLI entrypoint: `python -m research`
- Source adapters: `src/sources/`
- Monitoring/status: `src/monitoring/engine.py`
- Validation/analysis/publication: `src/validation`, `src/analysis`, `src/publication`

## Deployment
- Pages deploy workflow: `.github/workflows/deploy.yml`

## Scheduled workflows
- `scheduled-ingestion.yml`: daily pipeline
- `scheduled-maintenance.yml`: weekly queue/staleness maintenance
- `scheduled-integrity.yml`: weekly integrity checks

## Data model
- Canonical data: `data/research/donations.json`
- Historical observations: `data/research/donation_observations.jsonl`
- Events: `data/events/events.jsonl`
- Review queue: `data/review/queue.json`
- Public export: `data/public/donations.public.json`

## Issue handling
- Community submissions via issue templates
- High-risk items require review before canonical changes

## Releases
- Dataset changes are recorded in `CHANGELOG.md`; scheduled ingestion opens update PRs when files changed.

## Common failures
- Stale scheduler: check `status/system-status.json` for `automation_status: STALE`
- Source failures: inspect review queue and workflow logs
- Parser changes: update adapter + tests
- Coverage drops: review `COVERAGE_DROP_DETECTED` events and keep previous canonical data until reviewed

## Recovery
- Follow `docs/disaster-recovery.md`
