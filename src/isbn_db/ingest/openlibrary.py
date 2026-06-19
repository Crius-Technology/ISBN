"""Open Library editions dump ingest.

Dump format (``ol_dump_editions_*.txt.gz``): tab-separated lines, 5 columns where the 5th is the
edition record as JSON. One :class:`Edition` is emitted per line, keyed by its first valid ISBN-13
(an ISBN-10-only record is converted). Lines without a usable ISBN yield ``None``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator

from .. import isbn
from ..db import Edition
from ..sources import Tier

SOURCE = "openlibrary"
TIER = int(Tier.CROWD)
MARKETS = ["*"]

_YEAR = re.compile(r"\b(1[4-9]\d\d|20\d\d)\b")


def _year(publish_date: str | None) -> int | None:
    if not publish_date:
        return None
    m = _YEAR.search(publish_date)
    return int(m.group(1)) if m else None


def _first_isbn13(rec: dict) -> str | None:
    for raw in rec.get("isbn_13", []):
        canonical = isbn.normalize(raw)
        if canonical:
            return canonical
    for raw in rec.get("isbn_10", []):
        canonical = isbn.normalize(raw)
        if canonical:
            return canonical
    return None


def _strip_keys(items: list, prefix: str) -> list[str]:
    out = []
    for item in items:
        key = item.get("key") if isinstance(item, dict) else item
        if isinstance(key, str):
            out.append(key.removeprefix(prefix))
    return out


def parse_record(rec: dict) -> Edition | None:
    isbn13 = _first_isbn13(rec)
    if not isbn13:
        return None
    publish_date = rec.get("publish_date")
    return Edition(
        isbn13=isbn13,
        source=SOURCE,
        source_tier=TIER,
        isbn10=isbn.to_isbn10(isbn13),
        title=rec.get("title"),
        subtitle=rec.get("subtitle"),
        authors=_strip_keys(rec.get("authors", []), "/authors/"),
        publisher=(rec.get("publishers") or [None])[0],
        publish_date=publish_date,
        publish_year=_year(publish_date),
        languages=_strip_keys(rec.get("languages", []), "/languages/"),
        subjects=[s for s in rec.get("subjects", []) if isinstance(s, str)][:50],
        num_pages=rec.get("number_of_pages") if isinstance(rec.get("number_of_pages"), int) else None,
        physical_format=rec.get("physical_format"),
        source_record_id=rec.get("key"),
        markets=MARKETS,
    )


def parse_line(line: str) -> Edition | None:
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 5:
        return None
    try:
        rec = json.loads(parts[4])
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(rec, dict):
        return None
    return parse_record(rec)


def iter_editions(lines: Iterator[str]) -> Iterator[Edition | None]:
    for line in lines:
        yield parse_line(line)
