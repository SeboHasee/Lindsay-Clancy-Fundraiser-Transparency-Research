# Data Dictionary

## Status values

- verification: `PENDING`, `VERIFIED`, `REJECTED`, `DISPUTED`, `UNVERIFIED`
- review queue: `NEW`, `UNDER_REVIEW`, `ACCEPTED`, `REJECTED`, `DUPLICATE`, `NEEDS_MORE_EVIDENCE`
- risk levels: `LOW_RISK`, `MEDIUM_RISK`, `HIGH_RISK`

## Key files

- `data/research/donations.json`: normalized research donation records.
- `data/public/donations.public.json`: publication-filtered donation records.
- `data/events/events.jsonl`: append-only event stream.
- `data/review/community_submissions.json`: community claims.
- `data/review/queue.json`: maintainer review queue.
