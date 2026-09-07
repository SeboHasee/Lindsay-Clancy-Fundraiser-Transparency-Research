from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analysis.changelog import append_changelog
from src.analysis.coverage import write_coverage_report
from src.analysis.reporting import generate_html_reports
from src.analysis.seo_validation import (
    validate_github_pages_links,
    validate_seo_outputs,
)
from src.analysis.statistics import summarize_donations
from src.community_workflow import process_submissions
from src.database.migrations import initialize_database
from src.monitoring.engine import compute_automation_status, run_monitoring_cycle
from src.publication.filtering import apply_publication_filter
from src.sources.registry import load_source_registry
from src.validation.data_quality import validate_donation_records

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
STATUS = ROOT / "status"


def _require(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Missing prerequisite: {label} ({path})")


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def cmd_source_check(_: argparse.Namespace) -> None:
    registry = DATA / "source_registry.json"
    _require(registry, "source registry")
    records = load_source_registry(registry)
    print(f"sources={len(records)} checked")


def cmd_source_inventory(_: argparse.Namespace) -> None:
    registry = DATA / "source_registry.json"
    _require(registry, "source registry")
    records = load_source_registry(registry)
    for item in records:
        print(f"{item.source_id}\t{item.source_type}\t{item.terms_status}\t{item.polling_frequency}")


def cmd_import(args: argparse.Namespace) -> None:
    src = Path(args.file)
    _require(src, "import file")
    dst = DATA / "raw" / src.name
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"imported {src} -> {dst}")


def cmd_monitor(_: argparse.Namespace) -> None:
    summary = run_monitoring_cycle(DATA, REPORTS)
    print(json.dumps(summary, indent=2))


def cmd_setup(_: argparse.Namespace) -> None:
    needed_dirs = [DATA / "raw", DATA / "research", DATA / "public", DATA / "review", DATA / "events", REPORTS, STATUS]
    for item in needed_dirs:
        item.mkdir(parents=True, exist_ok=True)
    defaults = DATA / "research" / "automation_config.json"
    if not defaults.exists():
        _save_json(
            defaults,
            {
                "timezone": "UTC",
                "stale_warning_hours": 36,
                "stale_critical_hours": 72,
                "scheduler_interval_hours": 24,
                "zero_drop_min_previous": 100,
                "near_zero_fraction": 0.05,
                "coverage_drop_alert_ratio": 0.5,
            },
        )
    _require(DATA / "source_registry.json", "source registry")
    print("setup complete")


def cmd_validate(_: argparse.Namespace) -> None:
    sample = DATA / "research" / "donations.json"
    records = _load_json(sample, [])
    issues = validate_donation_records(records)
    payload = {"status": "PASS" if not issues else "FAIL", "issues": issues}
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "data_quality_report.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (REPORTS / "data-quality-report.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(payload["status"])


def cmd_deduplicate(_: argparse.Namespace) -> None:
    print("Deduplication step is schema-driven; run validate first.")


def cmd_verify(_: argparse.Namespace) -> None:
    print("Verification queue requires human review for identity claims.")


def cmd_triage(_: argparse.Namespace) -> None:
    submissions = _load_json(DATA / "review" / "community_submissions.json", [])
    queue = _load_json(DATA / "review" / "queue.json", [])
    triaged, review_items = process_submissions(submissions)
    queue.extend(review_items)
    _save_json(DATA / "review" / "queue.json", queue)
    _save_json(DATA / "review" / "community_submissions_triaged.json", triaged)
    print(f"triaged={len(triaged)} review_items_added={len(review_items)}")


def cmd_analyze(_: argparse.Namespace) -> None:
    sample = DATA / "research" / "donations.json"
    records = _load_json(sample, [])
    source_count = len(_load_json(DATA / "source_registry.json", []))
    summary = summarize_donations(records, REPORTS, source_count=source_count)
    write_coverage_report(
        REPORTS / "source_coverage.csv",
        observed_count=summary["metrics"]["observed_record_count"],
        reported_count=None,
        observed_amount=float(summary["metrics"]["observed_sum"]),
        reported_amount=None,
    )
    print("analysis complete")


def cmd_report(_: argparse.Namespace) -> None:
    required = [
        REPORTS / "statistical_summary.json",
        REPORTS / "data_quality_report.json",
        REPORTS / "source_coverage.csv",
    ]
    for path in required:
        _require(path, path.name)
    generate_html_reports(REPORTS)
    print("report artifacts present")


def cmd_seo_validate(_: argparse.Namespace) -> None:
    site_cfg = _load_json(
        DATA / "research" / "site_config.json",
        {"site_url": "https://sebohasee.github.io/Lindsay-Clancy-Fundraiser-Transparency-Research/"},
    )
    site_url = str(site_cfg.get("site_url")).rstrip("/") + "/"
    issues = validate_seo_outputs(REPORTS, site_url)
    issues.extend(validate_github_pages_links(REPORTS))
    if issues:
        raise SystemExit("SEO validation failed: " + ", ".join(issues))
    print("seo validation passed")


def cmd_coverage(_: argparse.Namespace) -> None:
    coverage = REPORTS / "source_coverage.csv"
    _require(coverage, "source coverage report")
    print(coverage.read_text(encoding="utf-8").strip())


def cmd_export(args: argparse.Namespace) -> None:
    if not args.public and not args.default_public:
        raise SystemExit("Use --public for publication export")
    records = _load_json(DATA / "research" / "donations.json", [])
    filtered = apply_publication_filter(records, DATA / "schema" / "data_classification.json")
    _save_json(DATA / "public" / "donations.public.json", filtered)
    print(f"public records exported={len(filtered)}")


def cmd_changelog(_: argparse.Namespace) -> None:
    append_changelog(ROOT / "CHANGELOG.md", "v0.0.0", "v0.1.0", 0, 0, 0, 0)
    print("changelog updated")


def cmd_health(_: argparse.Namespace) -> None:
    _require(REPORTS / "system-health.json", "system health")
    print((REPORTS / "system-health.json").read_text(encoding="utf-8").strip())


def cmd_status(_: argparse.Namespace) -> None:
    cfg = _load_json(
        DATA / "research" / "automation_config.json",
        {"stale_warning_hours": 36, "stale_critical_hours": 72, "scheduler_interval_hours": 24},
    )
    live = _load_json(REPORTS / "live-data-status.json", {})
    status = compute_automation_status(live.get("last_successful_update"), cfg)
    payload = {
        "status": live.get("run_state", status["status"]),
        "automation_status": status["automation_status"],
        "last_successful_run": live.get("last_successful_update"),
        "last_attempted_ingestion": live.get("last_attempted_update"),
        "expected_next_run": status["expected_next_run"],
        "dataset_version": live.get("dataset_version", "v0.1.0"),
        "dataset_size": live.get("dataset_size", 0),
        "historical_observation_count": live.get("historical_observation_count", 0),
        "source_health": live.get("source_health", {}),
    }
    _save_json(STATUS / "system-status.json", payload)
    print(json.dumps(payload, indent=2))


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

    sub.add_parser("monitor").set_defaults(func=cmd_monitor)
    sub.add_parser("setup").set_defaults(func=cmd_setup)
    sub.add_parser("validate").set_defaults(func=cmd_validate)
    sub.add_parser("deduplicate").set_defaults(func=cmd_deduplicate)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    sub.add_parser("triage").set_defaults(func=cmd_triage)
    sub.add_parser("analyze").set_defaults(func=cmd_analyze)
    sub.add_parser("coverage").set_defaults(func=cmd_coverage)
    sub.add_parser("report").set_defaults(func=cmd_report)
    sub.add_parser("seo-validate").set_defaults(func=cmd_seo_validate)
    sub.add_parser("changelog").set_defaults(func=cmd_changelog)
    sub.add_parser("health").set_defaults(func=cmd_health)
    sub.add_parser("status").set_defaults(func=cmd_status)

    exp = sub.add_parser("export")
    exp.add_argument("--public", action="store_true")
    exp.set_defaults(default_public=True)
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
