# Automation

## Workflows

- `ci.yml`: lint, typecheck, tests, build smoke, security checks for PR/push.
- `deploy.yml`: builds and deploys static reports/status to GitHub Pages.
- `scheduled-ingestion.yml`: daily ingestion/validation/analysis/report/export/status and automated update PR.
- `scheduled-maintenance.yml`: weekly review-queue and stale automation issue maintenance.
- `scheduled-integrity.yml`: weekly integrity/lint/type/test checks.

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
