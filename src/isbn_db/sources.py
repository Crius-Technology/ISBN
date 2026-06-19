"""Registry of ISBN / book-metadata sources.

Captures the research from docs/SOURCES.md as structured data so ingest code, cost planning
and licensing checks can reference a single source of truth. ``source_priority`` drives the
cross-source merge ranking (higher wins on field conflicts): registrar > national library >
trade aggregator > crowd-sourced.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Tier(IntEnum):
    """Merge priority — higher value wins when two sources disagree on a field."""

    CROWD = 1  # volunteer-edited (Open Library)
    AGGREGATOR = 2  # scraped/compiled (ISBNdb, Anna's Archive)
    NATIONAL = 3  # national library catalogues
    REGISTRAR = 4  # official ISBN agencies / publisher-submitted trade feeds


@dataclass(frozen=True)
class Source:
    key: str
    name: str
    markets: tuple[str, ...]  # ISO country codes this source is authoritative for
    tier: Tier
    paid: bool
    redistributable: bool  # may the data live in a shared/redistributed product?
    one_off: bool  # available as a one-time load (vs subscription-only)
    fmt: str  # primary bulk format
    url: str
    notes: str = ""


SOURCES: tuple[Source, ...] = (
    # --- Free authoritative backbone -------------------------------------------------
    Source(
        "dnb",
        "Deutsche Nationalbibliothek",
        ("DE",),
        Tier.NATIONAL,
        paid=False,
        redistributable=True,
        one_off=True,
        fmt="MARC21/RDF/CSV",
        url="https://d-nb.info/datasets/dnb-all",
        notes="CC0. OAI-PMH + bulk download. German backbone.",
    ),
    Source(
        "openlibrary",
        "Open Library data dumps",
        ("*",),
        Tier.CROWD,
        paid=False,
        redistributable=True,
        one_off=True,
        fmt="JSON/TSV (.txt.gz)",
        url="https://openlibrary.org/developers/dumps",
        notes="Public domain. Global backbone, ~93% English ISBN coverage.",
    ),
    Source(
        "loc",
        "Library of Congress (MDSConnect / Selected Datasets)",
        ("US",),
        Tier.NATIONAL,
        paid=False,
        redistributable=True,
        one_off=True,
        fmt="MARC21/XML",
        url="https://www.loc.gov/cds/products/marcDist.php",
        notes="~25M+ authoritative MARC records.",
    ),
    Source(
        "libris",
        "LIBRIS — National Library of Sweden",
        ("SE",),
        Tier.NATIONAL,
        paid=False,
        redistributable=True,
        one_off=True,
        fmt="MARC/RDF",
        url="https://www.kb.se/eng/loans-and-services/search-services/data.kb.se.html",
        notes="Open raw-data download via data.kb.se.",
    ),
    Source(
        "bl_bnb",
        "British Library / British National Bibliography",
        ("GB",),
        Tier.NATIONAL,
        paid=False,
        redistributable=True,
        one_off=True,
        fmt="RDF/linked data",
        url="https://www.bl.uk/collection-metadata/downloads",
        notes="Free authoritative UK supplement.",
    ),
    Source(
        "nb_no",
        "Nasjonalbiblioteket (National Library of Norway)",
        ("NO",),
        Tier.NATIONAL,
        paid=False,
        redistributable=True,
        one_off=True,
        fmt="API/MARC",
        url="https://github.com/NationalLibraryOfNorway",
        notes="Free open infrastructure + DHLAB APIs.",
    ),
    # --- Paid trade feeds (one-off where possible) -----------------------------------
    Source(
        "nielsen",
        "NielsenIQ BookData",
        ("GB",),
        Tier.REGISTRAR,
        paid=True,
        redistributable=True,
        one_off=True,
        fmt="ONIX/custom",
        url="https://nielseniq.com/global/en/landing-page/nielseniq-bookdata-metadata/",
        notes="UK ISBN agency, 51M+ records. One-off load available. Quote required.",
    ),
    Source(
        "vlb",
        "VLB / MVB (Verzeichnis lieferbarer Bücher)",
        ("DE", "AT", "CH"),
        Tier.REGISTRAR,
        paid=True,
        redistributable=True,
        one_off=True,
        fmt="ONIX",
        url="https://vlb.de/en/about-us/ueber-uns",
        notes="German Books-in-Print, ~2.5M in-print + 3.6M archived. Quote required.",
    ),
    Source(
        "bowker",
        "Bowker Books In Print",
        ("US", "AU"),
        Tier.REGISTRAR,
        paid=True,
        redistributable=True,
        one_off=False,
        fmt="ONIX/custom",
        url="https://www.bowker.com/books-in-print",
        notes="US/AU ISBN agency, 40M+ titles. Enterprise pricing.",
    ),
    Source(
        "bokbasen",
        "Bokbasen",
        ("NO",),
        Tier.REGISTRAR,
        paid=True,
        redistributable=True,
        one_off=False,
        fmt="ONIX",
        url="https://metadatablogg.bokbasen.no/",
        notes="Primary Norwegian commercial book-metadata vendor.",
    ),
    # --- Cheap aggregator gap-fill ---------------------------------------------------
    Source(
        "isbndb",
        "ISBNdb",
        ("*",),
        Tier.AGGREGATOR,
        paid=True,
        redistributable=True,
        one_off=True,
        fmt="JSON (API / bulk export)",
        url="https://isbndb.com/isbn-database",
        notes="~110M titles, 19 fields incl. retail prices. Cheap gap-fill.",
    ),
    # --- Reference-only (do NOT redistribute) ----------------------------------------
    Source(
        "annas",
        "Anna's Archive — all ISBNs dataset",
        ("*",),
        Tier.AGGREGATOR,
        paid=False,
        redistributable=False,
        one_off=True,
        fmt="benc.zst torrents",
        url="https://annas-archive.se/datasets",
        notes="Largest open list of all known ISBNs. Gap analysis only; licensing grey area.",
    ),
    Source(
        "googlebooks",
        "Google Books API",
        ("*",),
        Tier.AGGREGATOR,
        paid=False,
        redistributable=False,
        one_off=False,
        fmt="JSON (REST)",
        url="https://developers.google.com/books/docs/v1/reference/volumes",
        notes="Rich descriptive fields; ~36% error rate in studies. Enrichment only, no redistribution.",
    ),
)


def by_key(key: str) -> Source:
    for source in SOURCES:
        if source.key == key:
            return source
    raise KeyError(key)


def for_market(market: str) -> list[Source]:
    """Sources authoritative for ``market`` (plus global ``*`` sources), best tier first."""
    matches = [s for s in SOURCES if market in s.markets or "*" in s.markets]
    return sorted(matches, key=lambda s: s.tier, reverse=True)
