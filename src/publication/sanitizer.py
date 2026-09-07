from __future__ import annotations

import re
from typing import Iterable

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}")
TOKEN = re.compile(r"(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+", re.IGNORECASE)


def find_sensitive_strings(values: Iterable[str]) -> list[str]:
    matches: list[str] = []
    for value in values:
        if EMAIL.search(value) or PHONE.search(value) or TOKEN.search(value):
            matches.append(value)
    return matches


def sanitize_or_fail(records: list[dict]) -> None:
    found: list[str] = []
    for record in records:
        for item in record.values():
            if isinstance(item, str):
                found.extend(find_sensitive_strings([item]))
    if found:
        raise ValueError("Suspicious content detected; manual review required")
