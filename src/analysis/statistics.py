from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd


def summarize_donations(records: list[dict], output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(records)
    amounts = frame.get("normalized_amount", pd.Series(dtype=float)).dropna().astype(float)

    if amounts.empty:
        summary = {
            "observed_record_count": int(len(frame.index)),
            "anonymous_count": int(frame.get("anonymous_indicator", pd.Series(dtype=bool)).fillna(False).sum()) if not frame.empty else 0,
            "displayed_name_count": int(frame.get("displayed_donor_name", pd.Series(dtype=object)).notna().sum()) if not frame.empty else 0,
            "observed_sum": 0,
            "mean": 0,
            "median": 0,
            "min": 0,
            "max": 0,
            "p25": 0,
            "p50": 0,
            "p75": 0,
            "p90": 0,
            "p95": 0,
            "p99": 0,
            "std_dev": 0,
            "iqr": 0,
        }
    else:
        p = np.percentile(amounts, [25, 50, 75, 90, 95, 99])
        summary = {
            "observed_record_count": int(len(frame.index)),
            "anonymous_count": int(frame.get("anonymous_indicator", pd.Series(dtype=bool)).fillna(False).sum()),
            "displayed_name_count": int(frame.get("displayed_donor_name", pd.Series(dtype=object)).notna().sum()),
            "observed_sum": float(amounts.sum()),
            "mean": float(amounts.mean()),
            "median": float(amounts.median()),
            "min": float(amounts.min()),
            "max": float(amounts.max()),
            "p25": float(p[0]),
            "p50": float(p[1]),
            "p75": float(p[2]),
            "p90": float(p[3]),
            "p95": float(p[4]),
            "p99": float(p[5]),
            "std_dev": float(amounts.std(ddof=0)),
            "iqr": float(p[2] - p[0]),
        }

    payload = {
        "generation_timestamp": pd.Timestamp.utcnow().isoformat(),
        "dataset_version": "v0.1.0",
        "methodology_version": "v0.1.0",
        "source_coverage": "Partially observable dataset",
        "limitations": "Publicly observable data is not necessarily the complete donation ledger.",
        "metrics": summary,
    }
    (output_dir / "statistical_summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame([summary]).to_csv(output_dir / "statistical_summary.csv", index=False)
    return payload
