"""Read-only HTTP endpoints over the ``editions`` table.

Stats endpoints read the materialized views and tolerate an un-refreshed (empty) view by returning
an empty list, so the API stays up before the first ``isbn-db refresh-aggregates`` run.
"""

from __future__ import annotations

from typing import Annotated

import psycopg
from fastapi import APIRouter, HTTPException, Query, Request

from .. import isbn
from . import queries
from .models import (
    AreaKindCount,
    AreaMeta,
    CountryCount,
    Edition,
    Facets,
    Health,
    PublisherCount,
    SearchResponse,
    YearCount,
)

router = APIRouter()


def _conn(request: Request):
    return request.app.state.pool.connection()


def _rows(request: Request, sql: str, args: list | tuple = ()) -> list[dict]:
    """Run a read query, returning [] if it hits an un-refreshed materialized view."""
    try:
        with _conn(request) as conn:
            return conn.execute(sql, args).fetchall()
    except psycopg.errors.ObjectNotInPrerequisiteState:
        return []  # materialized view not yet populated — run `isbn-db refresh-aggregates`


@router.get("/health", response_model=Health, tags=["meta"])
def health(request: Request) -> Health:
    try:
        with _conn(request) as conn:
            row = conn.execute(queries.ESTIMATE_TOTAL_SQL).fetchone()
        return Health(status="ok", editions=int(row["total"]) if row else None)
    except Exception:
        return Health(status="degraded")


@router.get("/v1/editions/{isbn13}", response_model=Edition, tags=["editions"])
def get_edition(request: Request, isbn13: str) -> Edition:
    normalized = isbn.normalize(isbn13)
    if normalized is None:
        raise HTTPException(status_code=422, detail="invalid ISBN")
    with _conn(request) as conn:
        row = conn.execute(queries.SINGLE_SQL, (normalized,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="ISBN not found")
    return Edition(**row)


@router.get("/v1/search", response_model=SearchResponse, tags=["editions"])
def search(
    request: Request,
    q: Annotated[str | None, Query(description="substring match on title or publisher")] = None,
    country: Annotated[str | None, Query(description="ISO 3166-1 alpha-2, e.g. SE")] = None,
    area_kind: Annotated[
        str | None,
        Query(description="country | language_area | region | historical | administrative"),
    ] = None,
    language: Annotated[str | None, Query(description="language code present in languages[]")] = None,
    publisher: Annotated[str | None, Query(description="substring match on publisher")] = None,
    year_from: Annotated[int | None, Query(ge=0, le=2100)] = None,
    year_to: Annotated[int | None, Query(ge=0, le=2100)] = None,
    source: Annotated[str | None, Query(description="winning source key, e.g. dnb")] = None,
    min_quality: Annotated[int | None, Query(ge=0, le=100)] = None,
    sort: Annotated[str, Query()] = queries.DEFAULT_SORT,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SearchResponse:
    clause, args = queries.build_filters(
        q=q,
        country=country,
        area_kind=area_kind,
        language=language,
        publisher=publisher,
        year_from=year_from,
        year_to=year_to,
        source=source,
        min_quality=min_quality,
    )
    with _conn(request) as conn:
        rows = conn.execute(queries.search_sql(clause, sort), [*args, limit, offset]).fetchall()
        if clause:
            c = conn.execute(queries.bounded_count_sql(clause), args).fetchone()["c"]
            total, estimate = (queries.COUNT_CAP, True) if c > queries.COUNT_CAP else (c, False)
        else:
            row = conn.execute(queries.ESTIMATE_TOTAL_SQL).fetchone()
            total, estimate = (int(row["total"]) if row else 0), True
    return SearchResponse(
        results=[Edition(**r) for r in rows],
        total=total,
        total_is_estimate=estimate,
        limit=limit,
        offset=offset,
    )


@router.get("/v1/stats/countries", response_model=list[CountryCount], tags=["stats"])
def stats_countries(
    request: Request, limit: Annotated[int, Query(ge=1, le=500)] = 300
) -> list[CountryCount]:
    rows = _rows(request, queries.STATS_COUNTRIES_SQL, (limit,))
    return [
        CountryCount(country_iso2=r["country_iso2"], registration_area=r["registration_area"], count=r["n"])
        for r in rows
    ]


@router.get("/v1/stats/areas", response_model=list[AreaKindCount], tags=["stats"])
def stats_areas(request: Request) -> list[AreaKindCount]:
    rows = _rows(request, queries.STATS_AREAS_SQL)
    return [AreaKindCount(area_kind=r["area_kind"], count=r["n"]) for r in rows]


@router.get("/v1/stats/years", response_model=list[YearCount], tags=["stats"])
def stats_years(
    request: Request,
    year_from: Annotated[int, Query(ge=0, le=2100)] = 1900,
    year_to: Annotated[int, Query(ge=0, le=2100)] = 2026,
) -> list[YearCount]:
    rows = _rows(request, queries.STATS_YEARS_SQL, (year_from, year_to))
    return [YearCount(year=r["year"], count=r["n"]) for r in rows]


@router.get("/v1/stats/publishers", response_model=list[PublisherCount], tags=["stats"])
def stats_publishers(
    request: Request,
    country: Annotated[str | None, Query(description="ISO alpha-2 filter")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 25,
) -> list[PublisherCount]:
    where, args = ("WHERE country_iso2 = %s", [country.upper()]) if country else ("", [])
    sql = queries.STATS_PUBLISHERS_SQL.format(where=where)
    rows = _rows(request, sql, [*args, limit])
    return [PublisherCount(publisher=r["publisher"], country_iso2=r["country_iso2"], count=r["n"]) for r in rows]


@router.get("/v1/stats/sources", response_model=list[AreaKindCount], tags=["stats"])
def stats_sources(request: Request) -> list[AreaKindCount]:
    # Reuses the {label, count} shape; `area_kind` carries the source key.
    rows = _rows(request, queries.STATS_SOURCES_SQL)
    return [AreaKindCount(area_kind=r["source"], count=r["n"]) for r in rows]


@router.get("/v1/areas", response_model=list[AreaMeta], tags=["meta"])
def areas(request: Request) -> list[AreaMeta]:
    rows = _rows(request, queries.AREAS_SQL)
    return [
        AreaMeta(registration_area=r["registration_area"], area_kind=r["area_kind"], country_iso2=r["country_iso2"])
        for r in rows
    ]


@router.get("/v1/facets", response_model=Facets, tags=["meta"])
def facets(request: Request, languages_limit: Annotated[int, Query(ge=1, le=100)] = 25) -> Facets:
    return Facets(
        sources=[r["source"] for r in _rows(request, queries.FACET_SOURCES_SQL)],
        area_kinds=[r["area_kind"] for r in _rows(request, queries.FACET_AREAKINDS_SQL)],
        languages=[r["lang"] for r in _rows(request, queries.FACET_LANGUAGES_SQL, (languages_limit,))],
    )
