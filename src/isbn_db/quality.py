"""Per-record quality scoring.

Each edition gets a ``quality_score`` (0-100) and a ``quality_flags`` array describing what's
missing or implausible. The score combines three dimensions:

* **Completeness (0-70)** — weighted presence of the fields that matter for analysis.
* **Source authority (0-20)** — ``source_tier`` × 5 (registrar 20 > national 15 > aggregator 10 >
  crowd 5), reflecting how trustworthy the originating source is.
* **Plausibility (0-10)** — full marks unless a value is obviously wrong (e.g. an impossible year).

Scoring runs as a batched SQL ``UPDATE`` (fast over tens of millions of rows). The pure-Python
:func:`score_record` is the readable reference and is unit-tested; the SQL expression below mirrors
it exactly — keep the two in sync.

Cross-source agreement (comparing what two sources say about the same ISBN) is intentionally not
part of the score: the merged ``editions`` table keeps only the winning source's values. That would
require a raw per-source layer and is noted as future work.
"""

from __future__ import annotations

import datetime

import psycopg

from .db import connect

# Field weights (completeness, sums to 70).
_WEIGHTS = {
    "title": 15,
    "publisher": 12,
    "publish_year": 12,
    "authors": 10,
    "languages": 8,
    "num_pages": 6,
    "subjects": 7,
}
_MIN_YEAR = 1450  # Gutenberg-ish floor; nothing older has an ISBN-bearing edition anyway
_PLAUSIBILITY_MAX = 10
_IMPLAUSIBLE_YEAR_PENALTY = 8


def _current_year() -> int:
    return datetime.datetime.now(tz=datetime.UTC).year


def score_record(
    *,
    title: str | None,
    publisher: str | None,
    publish_year: int | None,
    authors: list | None,
    languages: list | None,
    num_pages: int | None,
    subjects: list | None,
    source_tier: int,
    current_year: int | None = None,
) -> tuple[int, list[str]]:
    """Reference scorer. Returns (score 0-100, flags). Mirrors the SQL in :data:`UPDATE_SQL`."""
    current_year = current_year or _current_year()
    flags: list[str] = []

    has_title = bool(title) and len(title) >= 2
    completeness = _WEIGHTS["title"] if has_title else 0
    if not has_title:
        flags.append("no_title")
    for field, value in (
        ("publisher", publisher),
        ("publish_year", publish_year),
        ("authors", authors),
        ("languages", languages),
        ("num_pages", num_pages),
        ("subjects", subjects),
    ):
        if value is not None:
            completeness += _WEIGHTS[field]
        else:
            flags.append(f"no_{field}")

    authority = source_tier * 5

    plausibility = _PLAUSIBILITY_MAX
    if publish_year is not None and (publish_year < _MIN_YEAR or publish_year > current_year + 2):
        plausibility -= _IMPLAUSIBLE_YEAR_PENALTY
        flags.append("implausible_year")

    score = max(0, min(100, completeness + authority + plausibility))
    return score, flags


ADD_COLUMNS_SQL = """
ALTER TABLE editions ADD COLUMN IF NOT EXISTS quality_score SMALLINT;
ALTER TABLE editions ADD COLUMN IF NOT EXISTS quality_flags TEXT[];
"""

# Mirrors score_record(). %(cur)s is the current year (bound per run).
_SCORE_EXPR = """
  LEAST(100, GREATEST(0,
      (CASE WHEN title IS NOT NULL AND length(title) >= 2 THEN 15 ELSE 0 END)
    + (CASE WHEN publisher    IS NOT NULL THEN 12 ELSE 0 END)
    + (CASE WHEN publish_year IS NOT NULL THEN 12 ELSE 0 END)
    + (CASE WHEN authors      IS NOT NULL THEN 10 ELSE 0 END)
    + (CASE WHEN languages    IS NOT NULL THEN 8  ELSE 0 END)
    + (CASE WHEN num_pages    IS NOT NULL THEN 6  ELSE 0 END)
    + (CASE WHEN subjects     IS NOT NULL THEN 7  ELSE 0 END)
    + (source_tier * 5)
    + 10
    - (CASE WHEN publish_year IS NOT NULL AND (publish_year < 1450 OR publish_year > %(cur)s + 2) THEN 8 ELSE 0 END)
  ))
"""

_FLAGS_EXPR = """
  array_remove(ARRAY[
    CASE WHEN title IS NULL OR length(title) < 2 THEN 'no_title' END,
    CASE WHEN publisher    IS NULL THEN 'no_publisher' END,
    CASE WHEN publish_year IS NULL THEN 'no_publish_year' END,
    CASE WHEN authors      IS NULL THEN 'no_authors' END,
    CASE WHEN languages    IS NULL THEN 'no_languages' END,
    CASE WHEN num_pages    IS NULL THEN 'no_num_pages' END,
    CASE WHEN subjects     IS NULL THEN 'no_subjects' END,
    CASE WHEN publish_year IS NOT NULL AND (publish_year < 1450 OR publish_year > %(cur)s + 2)
         THEN 'implausible_year' END
  ], NULL)
"""

# ``FOR UPDATE SKIP LOCKED`` lets scoring run concurrently with an active ingest: rows another
# transaction is writing are skipped this batch (picked up later) instead of deadlocking.
UPDATE_SQL = f"""
UPDATE editions SET quality_score = {_SCORE_EXPR}, quality_flags = {_FLAGS_EXPR}
WHERE isbn13 IN (
    SELECT isbn13 FROM editions WHERE quality_score IS NULL {{extra}}
    LIMIT %(batch)s FOR UPDATE SKIP LOCKED
)
"""


def score_all(*, batch: int = 500_000, rescore: bool = False, log=print) -> int:
    """Score every unscored edition (or all, if ``rescore``) in batches. Returns rows scored."""
    cur_year = _current_year()
    total = 0
    with connect() as conn:
        conn.execute(ADD_COLUMNS_SQL)
        conn.commit()
        if rescore:
            conn.execute("UPDATE editions SET quality_score = NULL")
            conn.commit()
        sql = UPDATE_SQL.format(extra="")
        while True:
            n = _run_batch(conn, sql, cur_year, batch)
            if n == 0:
                break
            total += n
            log(f"[quality] scored {total:,} rows")
    return total


def _run_batch(conn: psycopg.Connection, sql: str, cur_year: int, batch: int) -> int:
    for attempt in range(5):
        try:
            cur = conn.execute(sql, {"cur": cur_year, "batch": batch})
            conn.commit()
            return cur.rowcount
        except psycopg.errors.DeadlockDetected:  # contention with a concurrent ingest
            conn.rollback()
            if attempt == 4:
                raise
    return 0
