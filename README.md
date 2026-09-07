# Lindsay-Clancy-Fundraiser-Transparency-Research

A living, evidence-first public research platform for transparently documenting **publicly observable** fundraiser information related to the Lindsay Clancy / Musgrove Family Fundraiser.

## What this project does

- Monitors configured legitimate sources.
- Preserves historical observations and provenance.
- Validates, analyzes, and reports observable data.
- Tracks coverage and uncertainty explicitly.
- Routes community submissions into review workflows.
- Applies privacy filters before public export.

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
python -m research audit
```

## Current status

- Dataset version: `v0.1.0`
- Data status: partially observable
- Coverage status: reported in `reports/source_coverage.csv`
- Last successful update: shown in `reports/live-data-status.json`
- System health: `reports/system-health.json`
- Automation freshness + website-facing status: `status/system-status.json`

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
