"""ONIX for Books 3.0 ingest (reference tags).

ONIX is the publishing industry's metadata exchange format; **NielsenIQ BookData (UK)** and
**VLB/MVB (DE)** both deliver as ONIX. This parser is the ingest path for those paid feeds: point
it at the delivered ONIX file once procured (see docs/PROCUREMENT.md).

Streaming-parsed over <Product> elements, namespace-agnostic (handles the reference-tag namespace
or none). One :class:`Edition` per product, keyed by its ISBN-13 (ProductIDType 15, falling back to
EAN-13/ISBN-10). Tier/markets come from the source's registry entry, so a Nielsen product wins over
crowd/national data on merge where appropriate.
"""

from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from collections.abc import Iterator

from .. import isbn
from ..db import Edition
from ..sources import by_key


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_text(el: ET.Element, name: str) -> str | None:
    for child in el.iter():
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return None


def _find_all(el: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in el.iter() if _local(child.tag) == name]


def _onix_isbn(product: ET.Element) -> str | None:
    by_type: dict[str, str] = {}
    for pid in _find_all(product, "ProductIdentifier"):
        idtype = _find_text(pid, "ProductIDType")
        idval = _find_text(pid, "IDValue")
        if idtype and idval:
            by_type.setdefault(idtype, idval)
    for idtype in ("15", "03", "02"):  # ISBN-13, then EAN-13, then ISBN-10
        if idtype in by_type:
            canonical = isbn.normalize(by_type[idtype])
            if canonical:
                return canonical
    return None


def _title_and_subtitle(product: ET.Element) -> tuple[str | None, str | None]:
    for td in _find_all(product, "TitleDetail"):
        title = _find_text(td, "TitleText")
        if title:
            return title, _find_text(td, "Subtitle")
    return None, None


def _year(product: ET.Element) -> tuple[str | None, int | None]:
    for pd in _find_all(product, "PublishingDate"):
        if _find_text(pd, "PublishingDateRole") == "01":
            date = _find_text(pd, "Date")
            if date and len(date) >= 4 and date[:4].isdigit():
                return date, int(date[:4])
    return None, None


def _pages(product: ET.Element) -> int | None:
    for ext in _find_all(product, "Extent"):
        if _find_text(ext, "ExtentType") in ("00", "05", "07", "11"):
            val = _find_text(ext, "ExtentValue")
            if val and val.isdigit():
                return int(val)
    return None


def product_to_edition(product: ET.Element, *, source: str, tier: int, markets: list[str]) -> Edition | None:
    isbn13 = _onix_isbn(product)
    if not isbn13:
        return None
    title, subtitle = _title_and_subtitle(product)
    publish_date, year = _year(product)
    authors = [n for c in _find_all(product, "Contributor") if (n := _find_text(c, "PersonName"))]
    languages = [lc for lang in _find_all(product, "Language") if (lc := _find_text(lang, "LanguageCode"))]
    subjects = [s for subj in _find_all(product, "Subject") if (s := _find_text(subj, "SubjectHeadingText"))]
    return Edition(
        isbn13=isbn13,
        source=source,
        source_tier=tier,
        isbn10=isbn.to_isbn10(isbn13),
        title=title,
        subtitle=subtitle,
        authors=authors[:20],
        publisher=_find_text(product, "PublisherName"),
        publish_date=publish_date,
        publish_year=year,
        languages=list(dict.fromkeys(languages)),
        subjects=subjects[:50],
        num_pages=_pages(product),
        physical_format=_find_text(product, "ProductFormDescription"),
        source_record_id=_find_text(product, "RecordReference"),
        markets=markets,
    )


def _open(path: str):
    return gzip.open(path, "rb") if path.endswith(".gz") else open(path, "rb")  # noqa: SIM115


def iter_editions_from_path(path: str, *, source: str) -> Iterator[Edition | None]:
    src = by_key(source)
    tier, markets = int(src.tier), list(src.markets)
    with _open(path) as fh:
        for _event, el in ET.iterparse(fh, events=("end",)):
            if _local(el.tag) == "Product":
                try:
                    yield product_to_edition(el, source=source, tier=tier, markets=markets)
                except Exception:  # noqa: BLE001 - one bad product must not kill the run
                    yield None
                el.clear()
