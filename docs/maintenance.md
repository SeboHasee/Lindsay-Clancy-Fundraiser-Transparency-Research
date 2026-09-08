# Maintenance and Handover

## Monitoring
- Source monitoring runs via `python -m research monitor`.
- Source metadata is stored in `data/source_registry.json`.

## Adding sources
- Add source metadata with terms/access status.
- Implement or map a source adapter under `src/sources/`.

## Parser repairs
- If source structure changes, monitoring records review items and events.
- Fix parser in source adapter and add regression tests.

## Review and releases
- Triage community submissions with `python -m research triage`.
- Run `validate`, `analyze`, `report`, and `export --public` after approvals.

## Failure diagnosis
- Check `reports/system-health.json`, `reports/live-data-status.json`, and `data/review/queue.json`.

## Database and migrations
- Database initializes from `src/database/migrations.py`.

## GitHub Actions
- Workflows in `.github/workflows/` orchestrate monitor, validate, analyze, report, security, and release steps.
