"""Deutsche Nationalbibliothek (DNB) MARC21 ingest.

Reads ``dnb_all_dnbmarc.*.mrc.gz`` (MARC21 binary, UTF-8). One :class:`Edition` per MARC record,
keyed by the first valid ISBN found in any 020 field. Field extraction is shared with LIBRIS via
:mod:`isbn_db.ingest.marc`. DNB is a national library catalogue (Tier.NATIONAL).
"""

from __future__ import annotations

import gzip
from collections.abc import Iterator

from pymarc import MARCReader, Record

from ..db import Edition
from ..sources import Tier
from .marc import marc_record_to_edition

SOURCE = "dnb"
TIER = int(Tier.NATIONAL)
MARKETS = ["DE"]


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
    with gzip.open(path, "rb") as fh:
        yield from iter_editions(fh)
