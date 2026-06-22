"""Database schema and write path.

Single canonical table ``editions`` keyed by ISBN-13. Records from multiple sources are merged
on conflict using ``source_tier`` (see :mod:`isbn_db.sources`): a higher-or-equal tier source wins,
so an official registrar / national library overwrites crowd-sourced data but not vice versa.

``ingest_state`` tracks per-file progress so a run can resume after interruption.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import psycopg

from .config import DB_DSN

SCHEMA = """
CREATE TABLE IF NOT EXISTS editions (
    isbn13           TEXT PRIMARY KEY,
    isbn10           TEXT,
    title            TEXT,
    subtitle         TEXT,
    authors          TEXT[],
    publisher        TEXT,
    publish_date     TEXT,
    publish_year     INT,
    languages        TEXT[],
    subjects         TEXT[],
    num_pages        INT,
    physical_format  TEXT,
    source           TEXT NOT NULL,
    source_tier      SMALLINT NOT NULL,
    source_record_id TEXT,
    markets          TEXT[],
    quality_score    SMALLINT,
    quality_flags    TEXT[],
    registration_area TEXT,
    area_kind        TEXT,
    country_iso2     TEXT,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- For databases created before these columns existed.
ALTER TABLE editions ADD COLUMN IF NOT EXISTS quality_score SMALLINT;
ALTER TABLE editions ADD COLUMN IF NOT EXISTS quality_flags TEXT[];
ALTER TABLE editions ADD COLUMN IF NOT EXISTS registration_area TEXT;
ALTER TABLE editions ADD COLUMN IF NOT EXISTS area_kind TEXT;
ALTER TABLE editions ADD COLUMN IF NOT EXISTS country_iso2 TEXT;

CREATE INDEX IF NOT EXISTS editions_source_idx        ON editions (source);
CREATE INDEX IF NOT EXISTS editions_publisher_idx     ON editions (publisher);
CREATE INDEX IF NOT EXISTS editions_publish_year_idx  ON editions (publish_year);
CREATE INDEX IF NOT EXISTS editions_quality_idx       ON editions (quality_score);
CREATE INDEX IF NOT EXISTS editions_area_idx          ON editions (registration_area);
CREATE INDEX IF NOT EXISTS editions_country_iso2_idx  ON editions (country_iso2);

CREATE TABLE IF NOT EXISTS ingest_state (
    source            TEXT NOT NULL,
    dump_file         TEXT NOT NULL,
    lines_read        BIGINT NOT NULL DEFAULT 0,
    records_valid     BIGINT NOT NULL DEFAULT 0,
    records_upserted  BIGINT NOT NULL DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'running',
    cursor            TEXT,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (source, dump_file)
);

-- For databases created before `cursor` existed (OAI-PMH resume token).
ALTER TABLE ingest_state ADD COLUMN IF NOT EXISTS cursor TEXT;
"""

# Column order used by every batch insert. ``isbn13`` first (conflict key).
COLUMNS = (
    "isbn13",
    "isbn10",
    "title",
    "subtitle",
    "authors",
    "publisher",
    "publish_date",
    "publish_year",
    "languages",
    "subjects",
    "num_pages",
    "physical_format",
    "source",
    "source_tier",
    "source_record_id",
    "markets",
)

# On conflict, overwrite only when the incoming source is at least as authoritative.
_UPDATE_COLS = [c for c in COLUMNS if c != "isbn13"]
_UPSERT_SQL = (
    f"INSERT INTO editions ({', '.join(COLUMNS)}) VALUES %s "
    "ON CONFLICT (isbn13) DO UPDATE SET "
    + ", ".join(f"{c} = EXCLUDED.{c}" for c in _UPDATE_COLS)
    # Reset quality on overwrite so the next `score` run recomputes the (now-changed) row.
    + ", quality_score = NULL, quality_flags = NULL, updated_at = now() "
    "WHERE EXCLUDED.source_tier >= editions.source_tier"
)


@dataclass
class Edition:
    """One parsed bibliographic record, ready to upsert."""

    isbn13: str
    source: str
    source_tier: int
    isbn10: str | None = None
    title: str | None = None
    subtitle: str | None = None
    authors: list[str] = field(default_factory=list)
    publisher: str | None = None
    publish_date: str | None = None
    publish_year: int | None = None
    languages: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    num_pages: int | None = None
    physical_format: str | None = None
    source_record_id: str | None = None
    markets: list[str] = field(default_factory=list)

    def as_row(self) -> tuple:
        # Cap text lengths: dumps contain occasional garbage values (e.g. multi-KB publisher
        # strings) that both pollute analysis and overflow the publisher B-tree index (2704-byte
        # limit). These caps are far above any legitimate value.
        return (
            self.isbn13,
            self.isbn10,
            _cap(self.title, 2000),
            _cap(self.subtitle, 1000),
            _cap_list(self.authors, 300, 20),
            _cap(self.publisher, 500),
            _cap(self.publish_date, 100),
            self.publish_year,
            _cap_list(self.languages, 50, 20),
            _cap_list(self.subjects, 300, 50),
            self.num_pages,
            _cap(self.physical_format, 200),
            self.source,
            self.source_tier,
            _cap(self.source_record_id, 200),
            self.markets or None,
        )


def _cap(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit]


def _cap_list(values: list[str], item_limit: int, count_limit: int) -> list[str] | None:
    if not values:
        return None
    return [v[:item_limit] for v in values[:count_limit]]


def connect() -> psycopg.Connection:
    return psycopg.connect(DB_DSN, autocommit=False)


def init_db() -> None:
    with connect() as conn:
        conn.execute(SCHEMA)
        conn.commit()


def upsert_batch(conn: psycopg.Connection, rows: list[tuple]) -> None:
    """Insert/merge a batch of edition rows in a single round-trip.

    Postgres forbids ``ON CONFLICT DO UPDATE`` touching the same key twice in one statement, and a
    dump can legitimately repeat an ISBN, so we collapse duplicates within the batch (last wins).
    """
    if not rows:
        return
    deduped = {row[0]: row for row in rows}  # keyed by isbn13 (first column)
    rows = list(deduped.values())
    ncols = len(COLUMNS)
    placeholder = "(" + ", ".join(["%s"] * ncols) + ")"
    values_sql = ", ".join([placeholder] * len(rows))
    sql = _UPSERT_SQL.replace("VALUES %s", f"VALUES {values_sql}")
    flat: list = []
    for row in rows:
        flat.extend(row)
    conn.execute(sql, flat)
