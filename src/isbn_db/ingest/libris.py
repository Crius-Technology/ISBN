"""LIBRIS (National Library of Sweden) ingest via OAI-PMH.

Harvests the Swedish national bibliography (set ``nb``) as MARCXML and reuses the shared MARC21
extractor (:mod:`isbn_db.ingest.marc`). LIBRIS is a national library catalogue (Tier.NATIONAL),
CC0 licensed.

The OAI endpoint streams slowly (~5-6 records/sec) and does not always page with resumptionTokens,
so the harvest is chunked by record datestamp (month by month). Each chunk is a row in
``ingest_state`` (``dump_file = 'libris-nb-YYYY-MM'``); completed chunks are skipped on resume and a
mid-chunk resumptionToken is persisted in ``ingest_state.cursor``. Upserts are idempotent, so a
chunk that dies mid-stream is simply re-run.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from urllib.parse import urlencode

from pymarc import Field, Record, Subfield

from ..db import Edition, connect, upsert_batch
from ..sources import Tier
from .marc import marc_record_to_edition

SOURCE = "libris"
TIER = int(Tier.NATIONAL)
MARKETS = ["SE"]
SET = "nb"
OAI_BASE = "https://libris.kb.se/api/oaipmh/"

SLIM = "http://www.loc.gov/MARC21/slim"
OAI = "http://www.openarchives.org/OAI/2.0/"
_MARC_RECORD = f"{{{SLIM}}}record"
_RESUMPTION = f"{{{OAI}}}resumptionToken"

BATCH_SIZE = 1000
EARLIEST_YEAR = 2002  # OAI earliestDatestamp is 2002-01-21


def _el_to_record(el: ET.Element) -> Record:
    """Convert a MARCXML <record> element to a pymarc Record."""
    record = Record()
    for ctrl in el.findall(f"{{{SLIM}}}controlfield"):
        record.add_field(Field(tag=ctrl.get("tag", ""), data=ctrl.text or ""))
    for df in el.findall(f"{{{SLIM}}}datafield"):
        subs = [Subfield(code=sf.get("code", ""), value=sf.text or "") for sf in df.findall(f"{{{SLIM}}}subfield")]
        record.add_field(
            Field(tag=df.get("tag", ""), indicators=[df.get("ind1") or " ", df.get("ind2") or " "], subfields=subs)
        )
    return record


def record_to_edition(record: Record) -> Edition | None:
    return marc_record_to_edition(record, source=SOURCE, tier=TIER, markets=MARKETS)


def _open(url: str, retries: int = 5):
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "isbn-db/0.1 (+research)"})
            return urllib.request.urlopen(req, timeout=120)
        except (urllib.error.URLError, TimeoutError) as exc:  # transient network/server error
            last_err = exc
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"OAI request failed after {retries} attempts: {url}") from last_err


def iter_chunk(
    params: dict[str, str], *, resume_token: str | None = None
) -> Iterator[tuple[Edition | None, str | None]]:
    """Yield (edition, resumption_token) for an OAI chunk, following resumptionTokens.

    ``resumption_token`` accompanying each record is the token to resume the *next* page after the
    current page completes (None until the page boundary is reached). Streaming-parsed so memory
    stays flat regardless of chunk size.
    """
    if resume_token:
        url = OAI_BASE + "?" + urlencode({"verb": "ListRecords", "resumptionToken": resume_token})
    else:
        url = OAI_BASE + "?" + urlencode({"verb": "ListRecords", "metadataPrefix": "marcxml", **params})
    while url:
        resp = _open(url)
        token: str | None = None
        for _event, el in ET.iterparse(resp, events=("end",)):
            if el.tag == _MARC_RECORD:
                try:
                    yield (record_to_edition(_el_to_record(el)), None)
                except Exception:  # noqa: BLE001 - one bad record must not kill the harvest
                    yield (None, None)
                el.clear()
            elif el.tag == _RESUMPTION:
                token = (el.text or "").strip() or None
                el.clear()
        if token:
            # Signal the page boundary so the caller can checkpoint the token, then continue.
            yield (None, token)
            url = OAI_BASE + "?" + urlencode({"verb": "ListRecords", "resumptionToken": token})
        else:
            url = None


def _months(from_year: int, to_year: int) -> list[str]:
    return [f"{y:04d}-{m:02d}" for y in range(from_year, to_year + 1) for m in range(1, 13)]


def harvest(from_year: int = EARLIEST_YEAR, to_year: int = 2026, *, resume: bool = True, log=print) -> dict[str, int]:
    """Harvest set=nb month-by-month into the editions table. Resumable per chunk."""
    conn = connect()
    total_valid = 0
    total_chunks = 0
    try:
        for ym in _months(from_year, to_year):
            dump_file = f"libris-nb-{ym}"
            row = conn.execute(
                "SELECT status, cursor, records_valid FROM ingest_state WHERE source=%s AND dump_file=%s",
                (SOURCE, dump_file),
            ).fetchone()
            if row and row[0] == "completed" and resume:
                continue
            resume_token = row[1] if (row and resume) else None
            if not row:
                conn.execute(
                    "INSERT INTO ingest_state (source, dump_file, status) VALUES (%s,%s,'running')",
                    (SOURCE, dump_file),
                )
                conn.commit()

            year, month = ym.split("-")
            nxt_month = f"{int(month) % 12 + 1:02d}"
            nxt_year = str(int(year) + (1 if month == "12" else 0))
            params = {"set": SET, "from": f"{ym}-01T00:00:00Z", "until": f"{nxt_year}-{nxt_month}-01T00:00:00Z"}

            valid = 0
            batch: list[tuple] = []
            started = time.monotonic()
            for edition, token in iter_chunk(params, resume_token=resume_token):
                if edition is not None:
                    batch.append(edition.as_row())
                    valid += 1
                    if len(batch) >= BATCH_SIZE:
                        upsert_batch(conn, batch)
                        batch.clear()
                if token is not None:  # page boundary: flush + checkpoint the resume token
                    if batch:
                        upsert_batch(conn, batch)
                        batch.clear()
                    conn.execute(
                        "UPDATE ingest_state SET cursor=%s, records_valid=%s, updated_at=now() "
                        "WHERE source=%s AND dump_file=%s",
                        (token, valid, SOURCE, dump_file),
                    )
                    conn.commit()
            if batch:
                upsert_batch(conn, batch)
            conn.execute(
                "UPDATE ingest_state SET status='completed', cursor=NULL, records_valid=%s, updated_at=now() "
                "WHERE source=%s AND dump_file=%s",
                (valid, SOURCE, dump_file),
            )
            conn.commit()
            total_valid += valid
            total_chunks += 1
            if valid:
                rate = valid / max(time.monotonic() - started, 1e-9)
                log(f"[libris] {dump_file}: {valid:,} records ({rate:.1f}/s) | cumulative {total_valid:,}")
    finally:
        conn.close()
    return {"chunks": total_chunks, "valid": total_valid}
