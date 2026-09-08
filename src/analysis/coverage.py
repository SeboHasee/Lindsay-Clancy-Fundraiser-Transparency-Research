from __future__ import annotations

import csv
from pathlib import Path


def write_coverage_report(path: Path, observed_count: int, reported_count: int | None, observed_amount: float, reported_amount: float | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    count_ratio = 0.0 if not reported_count else observed_count / reported_count
    amount_ratio = 0.0 if not reported_amount else observed_amount / reported_amount

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "observed_count",
                "reported_count",
                "coverage_ratio",
                "observed_amount",
                "reported_amount",
                "amount_coverage_ratio",
                "missing_periods",
                "known_limitations",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "observed_count": observed_count,
                "reported_count": reported_count if reported_count is not None else "NOT_AVAILABLE",
                "coverage_ratio": round(count_ratio, 6),
                "observed_amount": observed_amount,
                "reported_amount": reported_amount if reported_amount is not None else "NOT_AVAILABLE",
                "amount_coverage_ratio": round(amount_ratio, 6),
                "missing_periods": "UNKNOWN",
                "known_limitations": "Partially observable dataset",
            }
        )
