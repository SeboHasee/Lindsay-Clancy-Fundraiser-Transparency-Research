from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _load_site_config(root: Path) -> dict[str, Any]:
    config_path = root / "data" / "research" / "site_config.json"
    default = {
        "site_name": "Lindsay Clancy / Musgrove Family Fundraiser Transparency Research",
        "site_url": "https://sebohasee.github.io/Lindsay-Clancy-Fundraiser-Transparency-Research/",
        "publisher_name": "Lindsay-Clancy-Fundraiser-Transparency-Research",
        "social_image": "social-preview.svg",
    }
    if not config_path.exists():
        return default
    loaded = _load_json(config_path, {})
    return {
        "site_name": loaded.get("site_name", default["site_name"]),
        "site_url": str(loaded.get("site_url", default["site_url"])).rstrip("/") + "/",
        "publisher_name": loaded.get("publisher_name", default["publisher_name"]),
        "social_image": loaded.get("social_image", default["social_image"]),
    }


def _slug_to_path(slug: str) -> str:
    return "index.html" if slug == "" else f"{slug}.html"


def _canonical(base_url: str, slug: str) -> str:
    return base_url if slug == "" else f"{base_url}{slug}.html"


def _social_preview(reports_dir: Path, site_name: str, generated_at: str) -> None:
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" role="img" aria-label="{site_name}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#1d4ed8" />
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#g)" />
  <text x="70" y="210" fill="#ffffff" font-size="46" font-family="Arial, sans-serif">Public Fundraiser Transparency Research</text>
  <text x="70" y="280" fill="#cbd5e1" font-size="30" font-family="Arial, sans-serif">Evidence-first | Privacy-preserving | Reproducible</text>
  <text x="70" y="360" fill="#e2e8f0" font-size="26" font-family="Arial, sans-serif">{site_name}</text>
  <text x="70" y="430" fill="#94a3b8" font-size="22" font-family="Arial, sans-serif">Generated {generated_at}</text>
</svg>
'''
    (reports_dir / "social-preview.svg").write_text(svg, encoding="utf-8")


def _json_ld(kind: str, payload: dict[str, Any]) -> str:
    body = {"@context": "https://schema.org", "@type": kind}
    body.update(payload)
    return json.dumps(body, ensure_ascii=False)


def _render_page(
    *,
    title: str,
    description: str,
    canonical_url: str,
    site_name: str,
    social_image_url: str,
    nav: list[tuple[str, str]],
    main_html: str,
    structured_data: list[str],
) -> str:
    nav_html = "".join([f'<li><a href="{href}">{label}</a></li>' for href, label in nav])
    json_ld_html = "\n".join([f'<script type="application/ld+json">{item}</script>' for item in structured_data])
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <meta name=\"description\" content=\"{description}\" />
  <link rel=\"canonical\" href=\"{canonical_url}\" />
  <meta property=\"og:type\" content=\"website\" />
  <meta property=\"og:title\" content=\"{title}\" />
  <meta property=\"og:description\" content=\"{description}\" />
  <meta property=\"og:url\" content=\"{canonical_url}\" />
  <meta property=\"og:image\" content=\"{social_image_url}\" />
  <meta name=\"twitter:card\" content=\"summary_large_image\" />
  <meta name=\"twitter:title\" content=\"{title}\" />
  <meta name=\"twitter:description\" content=\"{description}\" />
  <meta name=\"twitter:image\" content=\"{social_image_url}\" />
  {json_ld_html}
  <style>
    body {{ margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.6; color: #0f172a; background: #f8fafc; }}
    header, main, footer {{ max-width: 980px; margin: 0 auto; padding: 1rem; }}
    nav ul {{ display: flex; flex-wrap: wrap; gap: .75rem; list-style: none; padding: 0; margin: .5rem 0 1rem 0; }}
    a {{ color: #1d4ed8; }}
    .panel {{ background: #fff; border: 1px solid #e2e8f0; border-radius: .5rem; padding: 1rem; margin-bottom: 1rem; }}
    code, pre {{ background: #f1f5f9; padding: .2rem .3rem; border-radius: .2rem; }}
    pre {{ overflow-x: auto; padding: .75rem; }}
  </style>
</head>
<body>
  <header>
    <p><strong>{site_name}</strong></p>
    <nav aria-label=\"Primary\"><ul>{nav_html}</ul></nav>
  </header>
  <main>
    {main_html}
  </main>
  <footer>
    <p>Publicly observable data is not necessarily the complete donation ledger.</p>
  </footer>
</body>
</html>
"""


def _write_robots(reports_dir: Path, site_url: str) -> None:
    robots = f"User-agent: *\nAllow: /\n\nSitemap: {site_url}sitemap.xml\n"
    (reports_dir / "robots.txt").write_text(robots, encoding="utf-8")


def _write_sitemap(reports_dir: Path, site_url: str, pages: dict[str, dict[str, str]], lastmod: str) -> None:
    urlset = ET.Element("urlset", attrib={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"})
    for slug in pages:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = _canonical(site_url, slug)
        ET.SubElement(url, "lastmod").text = lastmod
    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    tree.write(reports_dir / "sitemap.xml", encoding="utf-8", xml_declaration=True)


def generate_html_reports(reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    root = reports_dir.parent
    stats = _load_json(reports_dir / "statistical_summary.json", {})
    system = _load_json(root / "status" / "system-status.json", {})
    source_registry = _load_json(root / "data" / "source_registry.json", [])
    source_assessment = _load_json(root / "data" / "source_assessment.json", [])
    config = _load_site_config(root)

    generated = datetime.now(UTC).isoformat()
    site_name = config["site_name"]
    site_url = config["site_url"]
    social_image = f"{site_url}{config['social_image']}"
    dataset_version = stats.get("dataset_version", system.get("dataset_version", "UNKNOWN"))

    nav = [
        ("index.html", "Overview"),
        ("research.html", "Research"),
        ("data.html", "Dataset"),
        ("statistics.html", "Statistics"),
        ("timeline.html", "Timeline"),
        ("sources.html", "Sources"),
        ("methodology.html", "Methodology"),
        ("updates.html", "Updates"),
        ("status.html", "Status"),
        ("community.html", "Community"),
        ("reports.html", "Report Index"),
    ]

    website_schema = _json_ld(
        "WebSite",
        {
            "name": site_name,
            "url": site_url,
            "description": "Evidence-first public research platform documenting publicly observable fundraiser information with provenance and privacy safeguards.",
            "publisher": {"@type": "Organization", "name": config["publisher_name"]},
        },
    )

    pages: dict[str, dict[str, Any]] = {
        "": {
            "title": "Lindsay Clancy Fundraiser Transparency Research — Public Research & Data",
            "description": "Public research project tracking observable fundraiser data, provenance, validation, coverage, and automation health.",
            "body": (
                f"<h1>Lindsay Clancy / Musgrove Family Fundraiser Transparency Research</h1>"
                f"<div class='panel'><p><strong>Status:</strong> {system.get('status', 'UNKNOWN')}</p>"
                f"<p><strong>Automation:</strong> {system.get('automation_status', 'UNKNOWN')}</p>"
                f"<p><strong>Last successful ingestion:</strong> {system.get('last_successful_run', 'UNKNOWN')}</p>"
                f"<p><strong>Dataset version:</strong> {dataset_version}</p>"
                f"<p><strong>Dataset size:</strong> {system.get('dataset_size', 'UNKNOWN')}</p></div>"
                "<div class='panel'><h2>What this project does</h2><p>Documents publicly observable fundraising information, preserves historical observations, validates records, and publishes privacy-filtered outputs.</p></div>"
                "<div class='panel'><h2>How to inspect the evidence</h2><ul>"
                "<li><a href='sources.html'>Source registry and provenance summary</a></li>"
                "<li><a href='methodology.html'>Collection, validation, and publication methodology</a></li>"
                "<li><a href='data.html'>Dataset scope, files, and limitations</a></li>"
                "<li><a href='status.html'>Operational health and freshness indicators</a></li>"
                "</ul></div>"
            ),
            "schema": [website_schema],
        },
        "about": {
            "title": "About This Project — Public Research & Data",
            "description": "Purpose, scope, and safeguards of this fundraiser transparency research project.",
            "body": "<h1>About this project</h1><p>This project exists to provide transparent, reproducible, and privacy-preserving research from legitimately observable sources.</p>",
            "schema": [_json_ld("WebPage", {"name": "About this project", "url": _canonical(site_url, "about")})],
        },
        "research": {
            "title": "Research Overview — Historical and Current Public Observations",
            "description": "Overview of research questions, evidence boundaries, and interpretive limits for fundraiser transparency analysis.",
            "body": "<h1>Research overview</h1><p>The system separates observed values, validated data, inferred interpretation, and unknowns to avoid false certainty.</p>",
            "schema": [_json_ld("WebPage", {"name": "Research overview", "url": _canonical(site_url, "research")})],
        },
        "data": {
            "title": "Dataset — Public Research Files and Coverage",
            "description": "Dataset contents, update process, machine-readable files, and limitations of publicly observable coverage.",
            "body": (
                "<h1>Dataset</h1>"
                "<div class='panel'><p><strong>Contains:</strong> canonical donation observations, status data, source metadata, event history, and public exports.</p>"
                "<p><strong>Does not contain:</strong> private donor data, deanonymization outputs, or prohibited personal information.</p></div>"
                "<div class='panel'><h2>Machine-readable files</h2><ul>"
                "<li><a href='https://github.com/SeboHasee/Lindsay-Clancy-Fundraiser-Transparency-Research/blob/main/data/public/donations.public.json'>Public donation export (JSON)</a></li>"
                "<li><a href='https://github.com/SeboHasee/Lindsay-Clancy-Fundraiser-Transparency-Research/blob/main/reports/statistical_summary.json'>Statistical summary (JSON)</a></li>"
                "<li><a href='https://github.com/SeboHasee/Lindsay-Clancy-Fundraiser-Transparency-Research/blob/main/reports/source_coverage.csv'>Coverage report (CSV)</a></li>"
                "</ul></div>"
            ),
            "schema": [
                _json_ld(
                    "Dataset",
                    {
                        "name": "Lindsay Clancy / Musgrove Family Fundraiser Public Transparency Dataset",
                        "description": "Privacy-filtered public research dataset derived from permitted source observations with provenance and validation metadata.",
                        "url": _canonical(site_url, "data"),
                        "license": "https://opensource.org/license/mit",
                        "creator": {"@type": "Organization", "name": config["publisher_name"]},
                        "isAccessibleForFree": True,
                        "dateModified": generated,
                        "keywords": ["fundraiser transparency", "public research", "provenance", "data quality"],
                        "distribution": [
                            {
                                "@type": "DataDownload",
                                "name": "Public donation export",
                                "encodingFormat": "application/json",
                                "contentUrl": "https://github.com/SeboHasee/Lindsay-Clancy-Fundraiser-Transparency-Research/blob/main/data/public/donations.public.json",
                            },
                            {
                                "@type": "DataDownload",
                                "name": "Statistical summary",
                                "encodingFormat": "application/json",
                                "contentUrl": "https://github.com/SeboHasee/Lindsay-Clancy-Fundraiser-Transparency-Research/blob/main/reports/statistical_summary.json",
                            },
                        ],
                    },
                )
            ],
        },
        "methodology": {
            "title": "Methodology & Transparency — Collection, Validation, Publication",
            "description": "How data is collected, validated, versioned, and filtered for privacy before publication.",
            "body": "<h1>Methodology and transparency</h1><p>Pipeline: source -> observation -> evidence -> validation -> analysis -> publication. Historical records are append-only and failures preserve last known-good outputs.</p>",
            "schema": [_json_ld("WebPage", {"name": "Methodology", "url": _canonical(site_url, "methodology")})],
        },
        "sources": {
            "title": "Sources & Provenance — Public Research Inputs",
            "description": "Source inventory, access methods, reliability classes, limitations, and terms-aware collection status.",
            "body": (
                "<h1>Sources and provenance</h1>"
                f"<div class='panel'><pre>{json.dumps(source_registry, indent=2)}</pre></div>"
                "<h2>Terms and access assessment</h2>"
                f"<div class='panel'><pre>{json.dumps(source_assessment, indent=2)}</pre></div>"
            ),
            "schema": [_json_ld("WebPage", {"name": "Sources and provenance", "url": _canonical(site_url, "sources")})],
        },
        "timeline": {
            "title": "Timeline — Historical Change Monitoring",
            "description": "Historical change and event tracking with confidence and review boundaries.",
            "body": "<h1>Timeline</h1><p>Timeline summaries are derived from immutable event logs and source-attributed observations.</p>",
            "schema": [_json_ld("WebPage", {"name": "Timeline", "url": _canonical(site_url, "timeline")})],
        },
        "statistics": {
            "title": "Donation Statistics — Publicly Observable Data",
            "description": "Statistical outputs generated from validated canonical data with explicit coverage limits.",
            "body": f"<h1>Donation statistics</h1><div class='panel'><pre>{json.dumps(stats, indent=2)}</pre></div>",
            "schema": [_json_ld("Report", {"name": "Donation statistics", "url": _canonical(site_url, "statistics"), "datePublished": generated})],
        },
        "updates": {
            "title": "Updates & Changelog — Dataset and Method Changes",
            "description": "Version history for dataset, methodology, and automated monitoring behavior.",
            "body": "<h1>Updates and changelog</h1><p>See repository CHANGELOG for versioned updates and impact summaries.</p>",
            "schema": [_json_ld("WebPage", {"name": "Updates", "url": _canonical(site_url, "updates")})],
        },
        "status": {
            "title": "Operational Status — Automation Health and Freshness",
            "description": "Live operational health signals including freshness, source health, pipeline state, and dataset status.",
            "body": f"<h1>Operational status</h1><div class='panel'><pre>{json.dumps(system, indent=2)}</pre></div>",
            "schema": [_json_ld("WebPage", {"name": "Operational status", "url": _canonical(site_url, "status")})],
        },
        "community": {
            "title": "Community Contributions — Corrections, Sources, and Review",
            "description": "How the public can submit evidence-backed corrections and sources through a review-first workflow.",
            "body": "<h1>Community contributions</h1><p>Community submissions are validated and reviewed before they can affect canonical research records.</p>",
            "schema": [_json_ld("WebPage", {"name": "Community contributions", "url": _canonical(site_url, "community")})],
        },
        "reports": {
            "title": "Report Index — Public Research Outputs",
            "description": "Index of generated public reports with links to overview, statistics, timeline, coverage, and quality reports.",
            "body": (
                "<h1>Report index</h1><ul>"
                "<li><a href='fundraiser-overview.html'>Fundraiser overview report</a></li>"
                "<li><a href='donation-statistics.html'>Donation statistics report</a></li>"
                "<li><a href='donation-timeline.html'>Donation timeline report</a></li>"
                "<li><a href='coverage.html'>Coverage report</a></li>"
                "<li><a href='data-quality.html'>Data quality report</a></li>"
                "</ul>"
            ),
            "schema": [_json_ld("WebPage", {"name": "Report index", "url": _canonical(site_url, "reports")})],
        },
    }

    for slug, cfg in pages.items():
        path = reports_dir / _slug_to_path(slug)
        schema: list[str] = list(cfg["schema"]) + [_json_ld("WebPage", {"name": cfg["title"], "url": _canonical(site_url, slug)})]
        html = _render_page(
            title=cfg["title"],
            description=cfg["description"],
            canonical_url=_canonical(site_url, slug),
            site_name=site_name,
            social_image_url=social_image,
            nav=nav,
            main_html=cfg["body"],
            structured_data=schema,
        )
        path.write_text(html, encoding="utf-8")

    # Keep compatibility aliases for existing links
    (reports_dir / "fundraiser-overview.html").write_text((reports_dir / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    (reports_dir / "donation-statistics.html").write_text((reports_dir / "statistics.html").read_text(encoding="utf-8"), encoding="utf-8")

    # Legacy pages retained with improved metadata
    (reports_dir / "donation-timeline.html").write_text((reports_dir / "timeline.html").read_text(encoding="utf-8"), encoding="utf-8")
    (reports_dir / "coverage.html").write_text((reports_dir / "status.html").read_text(encoding="utf-8"), encoding="utf-8")
    (reports_dir / "data-quality.html").write_text((reports_dir / "status.html").read_text(encoding="utf-8"), encoding="utf-8")
    (reports_dir / "sources.html").write_text((reports_dir / "sources.html").read_text(encoding="utf-8"), encoding="utf-8")
    (reports_dir / "changelog.html").write_text((reports_dir / "updates.html").read_text(encoding="utf-8"), encoding="utf-8")

    # 404 page
    missing = _render_page(
        title="Page Not Found — Fundraiser Transparency Research",
        description="The requested page could not be found. Use project navigation to access dataset, sources, methodology, and status pages.",
        canonical_url=f"{site_url}404.html",
        site_name=site_name,
        social_image_url=social_image,
        nav=nav,
        main_html="<h1>Page not found</h1><p>The URL may have moved. Use the navigation above to find current research pages.</p>",
        structured_data=[_json_ld("WebPage", {"name": "404", "url": f"{site_url}404.html"})],
    )
    (reports_dir / "404.html").write_text(missing, encoding="utf-8")

    _social_preview(reports_dir, site_name, generated)
    _write_robots(reports_dir, site_url)
    _write_sitemap(reports_dir, site_url, pages, generated)

    # Compatibility file for prior dashboard URL
    (reports_dir / "dashboard.html").write_text((reports_dir / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
