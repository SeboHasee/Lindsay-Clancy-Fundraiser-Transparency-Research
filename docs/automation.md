# Automation

## Workflows

- `ci.yml`: lint, typecheck, tests, build smoke, security checks for PR/push.
- `deploy.yml`: builds and deploys static reports/status to GitHub Pages.
- `scheduled-ingestion.yml`: daily ingestion/validation/analysis/report/export/status and automated update PR.
- `capture-pack-ingestion.yml`: event-driven ingestion when capture packs or ingestion logic changes.
- `scheduled-maintenance.yml`: weekly review-queue and stale automation issue maintenance.
- `scheduled-integrity.yml`: weekly integrity/lint/type/test checks.

## Operational states

`status/system-status.json` exposes:
- `HEALTHY`
- `DEGRADED`
- `STALE`
- `FAILED`

These states are derived from ingestion success, source health, and stale-run thresholds.

## Scheduler freshness and GitHub 60-day behavior

Public repository scheduled workflows may be disabled after 60 days of inactivity.
The system reports freshness in `status/system-status.json` and should display:

`AUTOMATION STATUS: STALE`

when thresholds are exceeded.

Re-enable procedure:
1. Open GitHub Actions tab.
2. Re-enable disabled workflows.
3. Run `Scheduled Ingestion` manually once.

## Concurrency

Scheduled workflows use workflow-level `concurrency` to avoid simultaneous ingestion writers.

## Capture-pack automation

The ingestion engine reads `data/captures/**/manifest.json` and verifies each artifact hash before extraction.
Invalid packs are quarantined in `data/review/capture_quarantine.json` and do not update canonical data.
Validated observations are normalized into `data/raw/gofundme_manual_export.json`, aggregate history is appended to
`data/research/fundraiser_observations.json`, canonical contract observations are written to
`data/research/capture_observations.normalized.json`, and capture events are appended to `data/events/capture_events.jsonl`.

Automated quality controls include:
- duplicate observation detection,
- impossible regression detection for aggregate totals,
- negative/future value checks,
- cross-channel aggregate conflict routing,
- parser/source drift routing when packs contain no extractable facts.

Failure behavior:
- preserve last known good canonical datasets,
- quarantine invalid capture packs,
- route actionable review/issue items for remediation.
