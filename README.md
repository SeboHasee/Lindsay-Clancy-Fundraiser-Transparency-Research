# Lindsay Clancy / Musgrove Family Fundraiser — Public Transparency Research

[![CI](https://github.com/SeboHasee/Lindsay-Clancy-Fundraiser-Transparency-Research/actions/workflows/ci.yml/badge.svg)](https://github.com/SeboHasee/Lindsay-Clancy-Fundraiser-Transparency-Research/actions/workflows/ci.yml)
[![Deploy Pages](https://github.com/SeboHasee/Lindsay-Clancy-Fundraiser-Transparency-Research/actions/workflows/deploy.yml/badge.svg)](https://github.com/SeboHasee/Lindsay-Clancy-Fundraiser-Transparency-Research/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Live website: https://sebohasee.github.io/Lindsay-Clancy-Fundraiser-Transparency-Research/

This repository is a living, evidence-first public research platform for documenting **publicly observable** fundraiser information while preserving provenance, reproducibility, and privacy boundaries.

## What this project does

- Monitors configured legitimate sources.
- Preserves historical observations and provenance.
- Validates, analyzes, and reports observable data.
- Tracks coverage and uncertainty explicitly.
- Routes community submissions into review workflows.
- Applies privacy filters before public export.

## What first-time visitors should know

1. The project documents publicly observable fundraiser information.
2. Source restrictions and terms are respected.
3. Dataset completeness is not assumed.
4. Automation health and freshness are published.
5. Community submissions are review-gated before canonical updates.

## What this project does not do

- No deanonymization of anonymous donors.
- No scraping circumvention or access-control bypass.
- No unsupported identity claims.
- No publication of prohibited personal data.

## Core command flow

```bash
python -m research setup
python -m research source check
python -m research monitor
python -m research validate
python -m research analyze
python -m research report
python -m research export --public
python -m research health
python -m research status
python -m research seo-validate
python -m research audit
```

## Current status

- Dataset version: `v0.1.0`
- Data status: partially observable
- Coverage status: reported in `reports/source_coverage.csv`
- Last successful update: shown in `reports/live-data-status.json`
- System health: `reports/system-health.json`
- Automation freshness + website-facing status: `status/system-status.json`

## Public research pages

- Overview: `reports/index.html`
- Dataset: `reports/data.html`
- Methodology: `reports/methodology.html`
- Sources & provenance: `reports/sources.html`
- Statistics: `reports/statistics.html`
- Timeline: `reports/timeline.html`
- Updates: `reports/updates.html`
- Operational status: `reports/status.html`
- Community contribution guide: `reports/community.html`

## Key artifacts

- Source registry: `data/source_registry.json`
- Source terms assessment: `data/source_assessment.json`
- Donation schema: `data/schema/donation.schema.json`
- Data classification policy map: `data/schema/data_classification.json`
- Event stream: `data/events/events.jsonl`
- Review queue: `data/review/queue.json`

## Community input

Use issue templates under `.github/ISSUE_TEMPLATE/` to submit:
- data corrections,
- new sources,
- privacy concerns,
- methodology suggestions,
- verification evidence.

All submissions are treated as **UNVERIFIED** until review.

## Transparency warning

**Publicly observable data is not necessarily the complete donation ledger.**

If automation becomes stale, the system should report:

**AUTOMATION STATUS: STALE**

## Search and indexing support

- `reports/robots.txt`
- `reports/sitemap.xml`
- Canonical URLs, Open Graph/Twitter metadata, and JSON-LD structured data are generated with report pages.

## Reproducibility and contribution

- Methodology: `METHODOLOGY.md`
- Sources: `SOURCES.md`
- Configuration: `docs/configuration.md`
- Automation: `docs/automation.md`
- Maintainer handover: `docs/maintainer-guide.md`
- First deployment: `FIRST_DEPLOYMENT.md`
