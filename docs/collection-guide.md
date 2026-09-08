# Collection Guide

Use only authorized methods; no scraping circumvention or anti-bot evasion.

## Operating model

- Local authorized collector session captures artifacts (HTML snapshot, screenshots, optional export).
- Repository automation ingests capture packs and normalizes observations into canonical datasets.
- Keep every datum traceable to an artifact hash and capture timestamp.

## Capture-pack format

Drop one immutable pack into `data/captures/<capture_id>/`:

- `manifest.json` (required)
- `page.html` (optional)
- `screenshot-*.png/.jpg/.webp` (optional)
- `export.json` (optional)
- `metadata.json` (optional)

Manifest fields include:

- `capture_id`, `source`, `source_url`, `captured_at`, `collector_version`, `capture_type`
- `source_reliability` (`A`/`B`/`C`/`D`)
- `artifacts[]` with `path`, `sha256`, `media_type`

## Preferred open-source collector stack

- Archive capture/provenance: ArchiveBox, Browsertrix/Webrecorder, SingleFile
- Browser capture automation: Playwright
- Replay/provenance: pywb/ReplayWeb.page
- OCR fallback for image-only captures when direct structured facts are not available

## Ingestion contract

The ingestion pipeline supports evidence documents with:

- `capture_metadata`
- `observed_facts`
- `provenance`

These are normalized to:

- `data/research/capture_observations.normalized.json` (intermediate evidence queue)
- `data/raw/gofundme_manual_export.json` (canonical donor-level export)
- `data/research/fundraiser_observations.json` (aggregate fundraiser timeline)
