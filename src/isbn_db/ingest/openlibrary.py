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
from . import countries

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


def _first_str(rec: dict, key: str) -> str | None:
    vals = rec.get(key)
    if isinstance(vals, list) and vals and isinstance(vals[0], str):
        return vals[0]
    return None


def _work_key(rec: dict) -> str | None:
    works = rec.get("works")
    if isinstance(works, list) and works and isinstance(works[0], dict):
        key = works[0].get("key")
        return key if isinstance(key, str) else None
    return None


def _identifiers(rec: dict) -> dict | None:
    ids: dict[str, list[str]] = {}
    for k, v in (rec.get("identifiers") or {}).items():
        if isinstance(v, list) and v:
            ids[k] = [str(x) for x in v[:5]]
    for native in ("oclc_numbers", "lccn"):
        v = rec.get(native)
        if isinstance(v, list) and v:
            ids[native.replace("_numbers", "")] = [str(x) for x in v[:5]]
    return ids or None


def _contributors(rec: dict) -> list[dict]:
    out: list[dict] = []
    for c in rec.get("contributions", [])[:30]:
        if isinstance(c, str):
            out.append({"name": c, "role": None})
    return out


def parse_record(rec: dict) -> Edition | None:
    isbn13 = _first_isbn13(rec)
    if not isbn13:
        return None
    publish_date = rec.get("publish_date")
    genres = [g.rstrip(". ") for g in rec.get("genres", []) if isinstance(g, str)][:20]
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
        dewey=_first_str(rec, "dewey_decimal_class"),
        genre_form=genres,
        pub_country=countries.to_iso2(rec.get("publish_country")),
        pub_city=_first_str(rec, "publish_places"),
        work_key=_work_key(rec),
        lc_class=_first_str(rec, "lc_classifications"),
        contributors=_contributors(rec),
        identifiers=_identifiers(rec),
        series=_first_str(rec, "series"),
        variant_titles=[t for t in rec.get("other_titles", []) if isinstance(t, str)][:20],
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
