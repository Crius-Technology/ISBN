"""Shared MARC21 field extraction.

Both the DNB (binary MARC) and LIBRIS (MARCXML via OAI-PMH) ingests use national-library MARC21
records with the same field semantics, so the mapping to :class:`Edition` lives here once.
"""

from __future__ import annotations

import re

from pymarc import Record

from .. import isbn
from ..db import Edition

# An ISBN candidate inside a noisy 020 $a like "978-3-16-148410-0 Pb. : EUR 24.00".
_ISBN_CANDIDATE = re.compile(r"97[89][\d-]{10,14}\d|\d[\d-]{8,12}[\dXx]")
_YEAR = re.compile(r"\b(1[4-9]\d\d|20\d\d)\b")
# Extent like "320 Seiten" (de), "234 s." (sv), "x, 99 pages" (en).
_PAGES = re.compile(r"(\d{1,5})\s*(?:S\.|Seiten|sidor|p\.|pages)", re.IGNORECASE)


def _subfield(record: Record, tag: str, code: str) -> str | None:
    for field in record.get_fields(tag):
        values = field.get_subfields(code)
        if values:
            return values[0]
    return None


def _control_field(record: Record, tag: str) -> str | None:
    fields = record.get_fields(tag)
    return fields[0].data if fields else None


def _all_subfields(record: Record, tag: str, code: str) -> list[str]:
    out: list[str] = []
    for field in record.get_fields(tag):
        out.extend(field.get_subfields(code))
    return out


def first_isbn(record: Record) -> str | None:
    for field in record.get_fields("020"):
        for raw in field.get_subfields("a"):
            m = _ISBN_CANDIDATE.search(raw)
            candidate = m.group(0) if m else raw
            canonical = isbn.normalize(candidate)
            if canonical:
                return canonical
    return None


def _year(record: Record) -> int | None:
    for tag, code in (("264", "c"), ("260", "c")):
        val = _subfield(record, tag, code)
        if val:
            m = _YEAR.search(val)
            if m:
                return int(m.group(1))
    # Fall back to the 008 fixed field (chars 7-10 = date1).
    f008 = record.get_fields("008")
    if f008 and f008[0].data:
        date1 = f008[0].data[7:11]
        if date1.isdigit():
            return int(date1)
    return None


def _language(record: Record) -> list[str]:
    langs = _all_subfields(record, "041", "a")
    if langs:
        return list(dict.fromkeys(langs))  # dedupe, preserve order (041 $a can repeat)
    f008 = record.get_fields("008")
    if f008 and f008[0].data and len(f008[0].data) >= 38:
        lang = f008[0].data[35:38].strip()
        if lang and lang != "|||":
            return [lang]
    return []


def _pages(record: Record) -> int | None:
    extent = _subfield(record, "300", "a")
    if extent:
        m = _PAGES.search(extent)
        if m:
            return int(m.group(1))
    return None


def marc_record_to_edition(record: Record, *, source: str, tier: int, markets: list[str]) -> Edition | None:
    """Map a MARC21 record to an :class:`Edition`, or ``None`` if it has no valid ISBN."""
    isbn13 = first_isbn(record)
    if not isbn13:
        return None
    title = _subfield(record, "245", "a")
    subtitle = _subfield(record, "245", "b")
    authors = _all_subfields(record, "100", "a") + _all_subfields(record, "700", "a")
    return Edition(
        isbn13=isbn13,
        source=source,
        source_tier=tier,
        isbn10=isbn.to_isbn10(isbn13),
        title=title.rstrip(" /:") if title else None,
        subtitle=subtitle.rstrip(" /:") if subtitle else None,
        authors=[a.rstrip(",. ") for a in authors][:20],
        publisher=_subfield(record, "264", "b") or _subfield(record, "260", "b"),
        publish_date=_subfield(record, "264", "c") or _subfield(record, "260", "c"),
        publish_year=_year(record),
        languages=_language(record),
        subjects=_all_subfields(record, "650", "a")[:50],
        num_pages=_pages(record),
        physical_format=_subfield(record, "338", "a"),
        source_record_id=_control_field(record, "001"),
        markets=markets,
    )
