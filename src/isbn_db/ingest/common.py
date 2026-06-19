"""Shared ingest plumbing: streaming readers, batching and resumable checkpoints.

Dumps are read by streaming-decompressing the ``.gz`` on the fly — the uncompressed data
(100GB+ for Open Library) is never written to disk.
"""

from __future__ import annotations

import gzip
import time
from collections.abc import Iterator

import psycopg

from ..db import Edition, connect, upsert_batch

BATCH_SIZE = 2000
CHECKPOINT_EVERY = 50_000  # lines between progress writes


def open_gzip_text(path: str) -> Iterator[str]:
    """Yield decoded lines from a gzipped text file without fully decompressing it."""
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        yield from fh


def _get_checkpoint(conn: psycopg.Connection, source: str, dump_file: str) -> tuple[str, int]:
    row = conn.execute(
        "SELECT status, lines_read FROM ingest_state WHERE source=%s AND dump_file=%s",
        (source, dump_file),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO ingest_state (source, dump_file, status) VALUES (%s, %s, 'running')",
            (source, dump_file),
        )
        conn.commit()
        return ("running", 0)
    return (row[0], row[1])


def _save_checkpoint(
    conn: psycopg.Connection,
    source: str,
    dump_file: str,
    lines: int,
    valid: int,
    upserted: int,
    status: str = "running",
) -> None:
    conn.execute(
        "UPDATE ingest_state SET lines_read=%s, records_valid=%s, records_upserted=%s, "
        "status=%s, updated_at=now() WHERE source=%s AND dump_file=%s",
        (lines, valid, upserted, status, source, dump_file),
    )
    conn.commit()


def run_ingest(
    source: str,
    dump_file: str,
    records: Iterator[Edition | None],
    *,
    limit: int | None = None,
    resume: bool = True,
    log=print,
) -> dict[str, int]:
    """Drive an ingest: consume parsed records, batch-upsert, checkpoint, and report.

    ``records`` is a generator yielding one :class:`Edition` per input line (or ``None`` for
    lines with no valid ISBN). Position in ``records`` is assumed to track input lines 1:1, so a
    resumed run skips ``lines_read`` already-processed records.
    """
    conn = connect()
    status, already = _get_checkpoint(conn, source, dump_file)
    if status == "completed" and resume:
        log(f"[{source}] {dump_file} already completed — skipping")
        conn.close()
        return {"lines": already, "valid": 0, "upserted": 0, "skipped": already}

    skip = already if (resume and already) else 0
    if skip:
        log(f"[{source}] resuming {dump_file}, skipping {skip:,} processed lines")

    lines = 0
    valid = 0
    upserted = 0
    batch: list[tuple] = []
    started = time.monotonic()

    try:
        for rec in records:
            lines += 1
            if lines <= skip:
                continue
            if rec is not None:
                batch.append(rec.as_row())
                valid += 1
            if len(batch) >= BATCH_SIZE:
                upsert_batch(conn, batch)
                upserted += len(batch)
                batch.clear()
            if lines % CHECKPOINT_EVERY == 0:
                if batch:
                    upsert_batch(conn, batch)
                    upserted += len(batch)
                    batch.clear()
                _save_checkpoint(conn, source, dump_file, lines, valid, upserted)
                rate = lines / max(time.monotonic() - started, 1e-9)
                log(f"[{source}] {lines:,} lines | {valid:,} valid | {upserted:,} upserted | {rate:,.0f} l/s")
            if limit is not None and valid >= limit:
                log(f"[{source}] reached --limit {limit}")
                break

        if batch:
            upsert_batch(conn, batch)
            upserted += len(batch)
        final_status = "completed" if limit is None else "partial"
        _save_checkpoint(conn, source, dump_file, lines, valid, upserted, status=final_status)
        log(f"[{source}] DONE {dump_file}: {lines:,} lines, {valid:,} valid, {upserted:,} upserted")
    finally:
        conn.close()

    return {"lines": lines, "valid": valid, "upserted": upserted, "skipped": skip}
