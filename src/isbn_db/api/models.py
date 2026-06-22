"""Pydantic response models for the search API.

``Edition`` mirrors the ``editions`` table columns (see :mod:`isbn_db.db`). The stats models back
the dashboard and read from the materialized views in :data:`isbn_db.db.AGGREGATE_VIEWS`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Edition(BaseModel):
    isbn13: str
    isbn10: str | None = None
    title: str | None = None
    subtitle: str | None = None
    authors: list[str] | None = None
    publisher: str | None = None
    publish_date: str | None = None
    publish_year: int | None = None
    languages: list[str] | None = None
    subjects: list[str] | None = None
    num_pages: int | None = None
    physical_format: str | None = None
    source: str
    source_tier: int
    source_record_id: str | None = None
    markets: list[str] | None = None
    quality_score: int | None = None
    quality_flags: list[str] | None = None
    registration_area: str | None = None
    area_kind: str | None = None
    country_iso2: str | None = None
    updated_at: datetime | None = None


class SearchResponse(BaseModel):
    results: list[Edition]
    total: int
    total_is_estimate: bool
    limit: int
    offset: int


class CountryCount(BaseModel):
    country_iso2: str | None
    registration_area: str | None
    count: int


class AreaKindCount(BaseModel):
    area_kind: str | None
    count: int


class YearCount(BaseModel):
    year: int
    count: int


class PublisherCount(BaseModel):
    publisher: str | None
    country_iso2: str | None
    count: int


class AreaMeta(BaseModel):
    registration_area: str
    area_kind: str | None
    country_iso2: str | None


class Facets(BaseModel):
    sources: list[str]
    area_kinds: list[str]
    languages: list[str]


class Health(BaseModel):
    status: str
    editions: int | None = None
