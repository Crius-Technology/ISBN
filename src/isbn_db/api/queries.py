"""SQL builders for the search API — parameterized, read-only.

Filters map to the existing btree indexes on ``editions`` (country_iso2, publish_year, source,
quality_score) plus the pg_trgm GIN indexes on title/publisher for substring ``q`` matching.
Stats read from the materialized views (see :data:`isbn_db.db.AGGREGATE_VIEWS`).
"""

from __future__ import annotations

EDITION_COLS = (
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
    "quality_score",
    "quality_flags",
    "registration_area",
    "area_kind",
    "country_iso2",
    "updated_at",
)
_COLS_SQL = ", ".join(EDITION_COLS)

# Whitelisted sort orders (never interpolate user input into ORDER BY). Tie-break on the PK for
# stable pagination.
SORTS = {
    "quality": "quality_score DESC NULLS LAST, isbn13",
    "year": "publish_year DESC NULLS LAST, isbn13",
    "title": "title ASC NULLS LAST, isbn13",
    "isbn": "isbn13",
}
DEFAULT_SORT = "quality"

# Counting all matches on a 39M-row table is expensive; cap the exact count and fall back to an
# estimate beyond it (the UI shows "10,000+").
COUNT_CAP = 10_000


def build_filters(
    *,
    q: str | None = None,
    country: str | None = None,
    area_kind: str | None = None,
    language: str | None = None,
    publisher: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    source: str | None = None,
    min_quality: int | None = None,
) -> tuple[str, list]:
    """Return a ``WHERE`` clause (possibly empty) and its positional args."""
    where: list[str] = []
    args: list = []
    if q:
        where.append("(title ILIKE %s OR publisher ILIKE %s)")
        like = f"%{q}%"
        args += [like, like]
    if country:
        where.append("country_iso2 = %s")
        args.append(country.upper())
    if area_kind:
        where.append("area_kind = %s")
        args.append(area_kind)
    if language:
        where.append("languages @> ARRAY[%s]::text[]")
        args.append(language)
    if publisher:
        where.append("publisher ILIKE %s")
        args.append(f"%{publisher}%")
    if year_from is not None:
        where.append("publish_year >= %s")
        args.append(year_from)
    if year_to is not None:
        where.append("publish_year <= %s")
        args.append(year_to)
    if source:
        where.append("source = %s")
        args.append(source)
    if min_quality is not None:
        where.append("quality_score >= %s")
        args.append(min_quality)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    return clause, args


def search_sql(clause: str, sort: str) -> str:
    order = SORTS.get(sort, SORTS[DEFAULT_SORT])
    return f"SELECT {_COLS_SQL} FROM editions{clause} ORDER BY {order} LIMIT %s OFFSET %s"


def bounded_count_sql(clause: str) -> str:
    """Exact count up to COUNT_CAP+1 rows; the caller treats an over-cap result as an estimate."""
    return f"SELECT count(*) AS c FROM (SELECT 1 FROM editions{clause} LIMIT {COUNT_CAP + 1}) t"


# Planner estimate of total table size — instant, used when no filters are applied.
ESTIMATE_TOTAL_SQL = "SELECT reltuples::bigint AS total FROM pg_class WHERE relname = 'editions'"

SINGLE_SQL = f"SELECT {_COLS_SQL} FROM editions WHERE isbn13 = %s"

# Stats — read straight from the materialized views.
STATS_COUNTRIES_SQL = (
    "SELECT country_iso2, registration_area, n FROM mv_country_counts ORDER BY n DESC LIMIT %s"
)
STATS_YEARS_SQL = "SELECT year, n FROM mv_year_counts WHERE year BETWEEN %s AND %s ORDER BY year"
STATS_AREAS_SQL = "SELECT area_kind, n FROM mv_areakind_counts ORDER BY n DESC"
STATS_PUBLISHERS_SQL = "SELECT publisher, country_iso2, n FROM mv_publisher_counts {where} ORDER BY n DESC LIMIT %s"
STATS_SOURCES_SQL = "SELECT source, n FROM mv_source_counts ORDER BY n DESC"

AREAS_SQL = (
    "SELECT registration_area, area_kind, country_iso2 FROM isbn_area_meta ORDER BY registration_area"
)
FACET_SOURCES_SQL = "SELECT source FROM mv_source_counts ORDER BY n DESC"
FACET_AREAKINDS_SQL = "SELECT area_kind FROM mv_areakind_counts WHERE area_kind IS NOT NULL ORDER BY n DESC"
FACET_LANGUAGES_SQL = "SELECT lang FROM mv_language_counts ORDER BY n DESC LIMIT %s"
