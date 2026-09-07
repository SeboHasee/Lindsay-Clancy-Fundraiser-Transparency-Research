# Lindsay-Clancy-Fundraiser-Transparency-Research

This repository provides an evidence-first, privacy-preserving, reproducible research system for documenting publicly observable information about the Lindsay Clancy / Musgrove Family Fundraiser.

## Core principles

- Accuracy over completeness
- Provenance over speculation
- Verification over inference
- Reproducibility over convenience
- Privacy over unnecessary collection

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m research source check
python -m research source inventory
python -m research validate
python -m research analyze
python -m research coverage
python -m research report
python -m research export --public
```

## Critical limitations

Publicly observable data is **not necessarily the complete donation ledger**. This project explicitly tracks source coverage and collection limitations.

## Compliance artifacts

- Source registry: `data/source_registry.json`
- Terms/access assessment: `data/source_assessment.json`
- Donation schema: `data/schema/donation.schema.json`
- Field classification: `data/schema/data_classification.json`
