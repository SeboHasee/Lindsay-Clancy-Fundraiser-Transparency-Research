from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


class _HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title = ""
        self.meta: dict[str, str] = {}
        self.link_canonical = ""
        self.h1_count = 0
        self.links: list[str] = []
        self.json_ld: list[str] = []
        self._in_json_ld = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k: (v or "") for k, v in attrs}
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            if "name" in data:
                self.meta[data["name"]] = data.get("content", "")
            if "property" in data:
                self.meta[data["property"]] = data.get("content", "")
        if tag == "link" and data.get("rel") == "canonical":
            self.link_canonical = data.get("href", "")
        if tag == "h1":
            self.h1_count += 1
        if tag == "a":
            self.links.append(data.get("href", ""))
        if tag == "script" and data.get("type") == "application/ld+json":
            self._in_json_ld = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag == "script":
            self._in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data
        if self._in_json_ld:
            self.json_ld.append(data)


def validate_seo_outputs(reports_dir: Path, site_url: str) -> list[str]:
    errors: list[str] = []
    required_pages = [
        "index.html",
        "about.html",
        "research.html",
        "data.html",
        "methodology.html",
        "sources.html",
        "timeline.html",
        "statistics.html",
        "updates.html",
        "status.html",
        "community.html",
        "reports.html",
        "404.html",
    ]

    titles: set[str] = set()
    descriptions: set[str] = set()

    for page in required_pages:
        path = reports_dir / page
        if not path.exists():
            errors.append(f"missing_page:{page}")
            continue

        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            errors.append(f"empty_page:{page}")
            continue
        if "localhost" in raw:
            errors.append(f"localhost_reference:{page}")
        if "noindex" in raw.lower():
            errors.append(f"unexpected_noindex:{page}")

        parser = _HeadParser()
        parser.feed(raw)

        title = parser.title.strip()
        if not title:
            errors.append(f"missing_title:{page}")
        elif title in titles:
            errors.append(f"duplicate_title:{page}")
        else:
            titles.add(title)

        desc = parser.meta.get("description", "").strip()
        if not desc:
            errors.append(f"missing_description:{page}")
        elif desc in descriptions:
            errors.append(f"duplicate_description:{page}")
        else:
            descriptions.add(desc)

        canonical = parser.link_canonical.strip()
        if not canonical:
            errors.append(f"missing_canonical:{page}")
        elif not canonical.startswith(site_url):
            errors.append(f"invalid_canonical:{page}")

        if parser.h1_count == 0:
            errors.append(f"missing_h1:{page}")

        for tag in ["og:title", "og:description", "og:url", "og:image", "twitter:title", "twitter:description", "twitter:image"]:
            if not parser.meta.get(tag):
                errors.append(f"missing_meta:{page}:{tag}")

        for block in parser.json_ld:
            try:
                payload = json.loads(block)
                if "@context" not in payload or "@type" not in payload:
                    errors.append(f"invalid_jsonld:{page}")
            except json.JSONDecodeError:
                errors.append(f"malformed_jsonld:{page}")

        for href in parser.links:
            if not href or href.startswith("#"):
                continue
            if href.startswith("http://"):
                errors.append(f"insecure_link:{page}:{href}")
            if href.startswith("https://"):
                continue
            if href.startswith("mailto:"):
                continue
            target = reports_dir / href
            if not target.exists():
                errors.append(f"broken_internal_link:{page}:{href}")

    robots = reports_dir / "robots.txt"
    if not robots.exists():
        errors.append("missing_robots")
    else:
        txt = robots.read_text(encoding="utf-8")
        if f"Sitemap: {site_url}sitemap.xml" not in txt:
            errors.append("robots_missing_sitemap")

    sitemap = reports_dir / "sitemap.xml"
    if not sitemap.exists():
        errors.append("missing_sitemap")
    else:
        try:
            root = ET.parse(sitemap).getroot()
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            locs = [el.text or "" for el in root.findall("sm:url/sm:loc", ns)]
            if len(locs) != len(set(locs)):
                errors.append("sitemap_duplicate_urls")
            for url in locs:
                if not url.startswith(site_url):
                    errors.append(f"sitemap_invalid_url:{url}")
        except ET.ParseError:
            errors.append("malformed_sitemap")

    status_path = reports_dir.parent / "status" / "system-status.json"
    if not status_path.exists():
        errors.append("missing_system_status_json")
    else:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") not in {"HEALTHY", "DEGRADED", "STALE", "FAILED"}:
            errors.append("invalid_system_status_value")

    return errors


def validate_github_pages_links(reports_dir: Path) -> list[str]:
    errors: list[str] = []
    for html in reports_dir.glob("*.html"):
        txt = html.read_text(encoding="utf-8")
        if re.search(r"https?://127\.0\.0\.1|https?://localhost", txt):
            errors.append(f"localhost_url:{html.name}")
    return errors
