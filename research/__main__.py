from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analysis.statistics import summarize_donations
from src.database.migrations import initialize_database
from src.validation.data_quality import validate_donation_records

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"


def _require(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Missing prerequisite: {label} ({path})")


def cmd_source_check(_: argparse.Namespace) -> None:
    registry = DATA / "source_registry.json"
    _require(registry, "source registry")
    records = json.loads(registry.read_text(encoding="utf-8"))
    print(f"sources={len(records)} checked")


def cmd_source_inventory(_: argparse.Namespace) -> None:
    registry = DATA / "source_registry.json"
    _require(registry, "source registry")
    records = json.loads(registry.read_text(encoding="utf-8"))
    for item in records:
        print(f"{item['source_id']}	{item['source_type']}	{item['authorization_status']}")


def cmd_import(args: argparse.Namespace) -> None:
    src = Path(args.file)
    _require(src, "import file")
    dst = DATA / "raw" / src.name
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"imported {src} -> {dst}")


def cmd_validate(_: argparse.Namespace) -> None:
    sample = DATA / "research" / "donations.json"
    records = []
    if sample.exists():
        records = json.loads(sample.read_text(encoding="utf-8"))
    issues = validate_donation_records(records)
    payload = {"status": "PASS" if not issues else "FAIL", "issues": issues}
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "data_quality_report.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(payload["status"])


def cmd_deduplicate(_: argparse.Namespace) -> None:
    print("Deduplication step is schema-driven; run validate first.")


def cmd_verify(_: argparse.Namespace) -> None:
    print("Verification queue requires human review for identity claims.")


def cmd_analyze(_: argparse.Namespace) -> None:
    sample = DATA / "research" / "donations.json"
    records = []
    if sample.exists():
        records = json.loads(sample.read_text(encoding="utf-8"))
    summarize_donations(records, REPORTS)
    print("analysis complete")


def cmd_coverage(_: argparse.Namespace) -> None:
    coverage = REPORTS / "source_coverage.csv"
    _require(coverage, "source coverage report")
    print(coverage.read_text(encoding="utf-8").strip())


def cmd_report(_: argparse.Namespace) -> None:
    required = [
        REPORTS / "statistical_summary.json",
        REPORTS / "data_quality_report.json",
        REPORTS / "source_coverage.csv",
    ]
    for path in required:
        _require(path, path.name)
    print("report artifacts present")


def cmd_export(args: argparse.Namespace) -> None:
    if not args.public:
        raise SystemExit("Use --public for publication export")
    print("public export requested; run publication sanitizer before publishing")


def cmd_audit(_: argparse.Namespace) -> None:
    print("Audit checklist: observed vs unavailable vs incomplete vs verified vs uncertain vs restrictions")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m research")
    sub = parser.add_subparsers(dest="command", required=True)

    source = sub.add_parser("source")
    source_sub = source.add_subparsers(dest="source_command", required=True)
    source_sub.add_parser("check").set_defaults(func=cmd_source_check)
    source_sub.add_parser("inventory").set_defaults(func=cmd_source_inventory)

    imp = sub.add_parser("import")
    imp.add_argument("file")
    imp.set_defaults(func=cmd_import)

    sub.add_parser("validate").set_defaults(func=cmd_validate)
    sub.add_parser("deduplicate").set_defaults(func=cmd_deduplicate)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    sub.add_parser("analyze").set_defaults(func=cmd_analyze)
    sub.add_parser("coverage").set_defaults(func=cmd_coverage)
    sub.add_parser("report").set_defaults(func=cmd_report)

    exp = sub.add_parser("export")
    exp.add_argument("--public", action="store_true")
    exp.set_defaults(func=cmd_export)

    sub.add_parser("audit").set_defaults(func=cmd_audit)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    initialize_database(DATA / "database" / "research.sqlite")
    args.func(args)


if __name__ == "__main__":
    main()
