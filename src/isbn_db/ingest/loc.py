"""Library of Congress (MDSConnect "Books All") MARC21 ingest.

Reads the free LoC 2016 retrospective book records (``BooksAll.2016.part*.utf8.gz``, MARC21 binary,
UTF-8) — ~25M authoritative US records. Field extraction (incl. Dewey, genre/form, country of
publication) is shared with DNB/LIBRIS via :mod:`isbn_db.ingest.marc`. LoC is the de-facto US
national catalogue (Tier.NATIONAL), so it outranks crowd data and surfaces the US trade market that
the ISBN's 979-8 (Amazon KDP) slice otherwise masks.
"""

from __future__ import annotations

import gzip
from collections.abc import Iterator

from pymarc import MARCReader, Record

from ..db import Edition
from ..sources import Tier
from .marc import marc_record_to_edition

SOURCE = "loc"
TIER = int(Tier.NATIONAL)
MARKETS = ["US"]


def record_to_edition(record: Record) -> Edition | None:
    return marc_record_to_edition(record, source=SOURCE, tier=TIER, markets=MARKETS)


def iter_editions(fileobj) -> Iterator[Edition | None]:
    """Yield one Edition (or None) per MARC record from a binary stream."""
    reader = MARCReader(fileobj, to_unicode=True, permissive=True)
    for record in reader:
        if record is None:  # unreadable record; keep position in sync
            yield None
            continue
        try:
            yield record_to_edition(record)
        except Exception:  # noqa: BLE001 - never let one bad record kill the run
            yield None


def iter_editions_from_path(path: str) -> Iterator[Edition | None]:
    # Archive.org serves raw .utf8 MARC; a local copy may be gzipped. Sniff the magic bytes.
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rb") as fh:
        yield from iter_editions(fh)
