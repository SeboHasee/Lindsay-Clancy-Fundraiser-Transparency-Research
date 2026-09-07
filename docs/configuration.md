# Configuration

## GitHub Secrets

| SECRET_NAME | Purpose | Required? | Where to obtain it | Where used |
|---|---|---|---|---|
| `GITHUB_TOKEN` | GitHub Actions auth for PR/issue operations | Provided automatically by GitHub Actions | GitHub runtime | Scheduled workflows (`scheduled-ingestion.yml`, `scheduled-maintenance.yml`) |

## Repository settings

- Enable GitHub Actions.
- Enable GitHub Pages (Source: GitHub Actions).
- Protect `main` with PR review for sensitive changes.

## Runtime config

`data/research/automation_config.json`:
- `timezone`
- `stale_warning_hours`
- `stale_critical_hours`
- `scheduler_interval_hours`

No secret values are stored in repository files.
