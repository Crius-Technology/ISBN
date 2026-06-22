---
title: "ISBN Database -- UI Data Model & Segregation"
type: reference
status: draft
author: "Crius Technology"
sidebar_label: UI Data Model
sidebar_position: 7
tags:
  - isbn
  - ui
  - data-model
---

# ISBN Database -- UI Data Model & Segregation

Design notes for a UI built on top of the `editions` table. The goal is to define how the data should
be **segregated** (sliced) so views are correct and not misleading — especially around geography.

## Fact table and dimensions

`editions` is the fact table (one row per ISBN-13). Useful slicing dimensions already present:

| Dimension | Column(s) | Use in UI |
|-----------|-----------|-----------|
| Geography | `country_iso2`, `registration_area`, `area_kind` | Map / per-country views (see below) |
| Provenance & trust | `source`, `source_tier`, `quality_score`, `quality_flags` | Filter to authoritative/complete records |
| Time | `publish_year` | Trends, time sliders |
| Language | `languages[]` | Language facet |
| Publisher | `publisher` | Top publishers, concentration |
| Subject | `subjects[]` | Topic facets |

A small dimension table, `isbn_area_meta(registration_area, area_kind, country_iso2)`, backs the
geography fields and can be exposed directly to the UI as a lookup.

## Geography: the key segregation decision

`registration_area` is the ISBN agency label and is **not always a single country**. Each area is
classified deterministically (`src/isbn_db/geo.py`) into `area_kind`:

| `area_kind` | Meaning | `country_iso2` | UI treatment |
|-------------|---------|----------------|--------------|
| `country` | A single country/territory | set (e.g. `SE`, `US`) | Plot on a map; per-country view; show flag |
| `language_area` | Spans many countries (English/German/French) | NULL | **Do not** plot as one country; show as a labelled multi-country bucket |
| `region` | Multi-country agency (Caribbean Community, South Pacific) | NULL | Group view, not a single point |
| `historical` | Superseded state (former U.S.S.R / Czechoslovakia / Yugoslavia) | NULL | Optional "historical" bucket |
| `administrative` | Reserved / supranational (Reserved Agency, NGO/EU, Federated Panel) | NULL | Usually excluded from geography views |

**Rules for the UI:**

- **Per-country / choropleth map:** use only `area_kind = 'country'` with a non-null `country_iso2`.
  Everything else has no single location and must be excluded from the map or shown in a separate list.
- **Language areas are first-class but not countries.** ~14 M "English language" + ~4.6 M "German
  language" + ~0.66 M "French language" records dominate the corpus; surface them as their own
  segment, never as a country pin.
- ⚠️ **The UK cannot be isolated from the ISBN.** 978-0 / 978-1 are both "English language" (US, UK,
  AU, …). Only 979-8 = "United States" gives single-country granularity. A true **per-country UK view
  requires a UK-scoped source** (`source='nielsen'`, `markets @> '{GB}'`) — see
  [Procurement](./PROCUREMENT.md). Until then, "UK" is at best "English language minus US".

```sql
-- Map-ready: editions per country with an ISO code
SELECT country_iso2, registration_area, count(*)
FROM editions WHERE area_kind = 'country' AND country_iso2 IS NOT NULL
GROUP BY 1,2 ORDER BY 3 DESC;

-- Non-country buckets to render separately
SELECT area_kind, registration_area, count(*)
FROM editions WHERE area_kind <> 'country' GROUP BY 1,2 ORDER BY 3 DESC;
```

## Publisher geo-location

The data has **no publisher coordinates**. Options, cheapest first:

1. **Registration country as proxy** (available now): attribute a publisher to the `country_iso2` of
   its books' ISBNs. Good for choropleths; imperfect (a publisher may register in multiple groups).
2. **Publisher dimension table** (next step): extract distinct publishers, attach a country and
   (optionally) a geocoded address. Trade feeds (Nielsen/VLB ONIX) carry publisher address fields
   that can be geocoded; open data alone does not. This enables true publisher pins on a map.
3. **External geocoding** of publisher name/city via a gazetteer — only worthwhile once a clean
   publisher list exists.

Recommended: build a `publishers` dimension (id, name, primary country, optional lat/long) populated
first from registration country, later enriched from trade feeds.

## Serving / performance

`editions` is ~39 M rows; interactive UI aggregates should not scan it live per request.

- Precompute **materialized views** for common cuts: counts by `country_iso2 × publish_year`,
  top publishers per country, language distribution, quality-band counts. Refresh after each ingest.
- Keep the existing indexes (`country_iso2`, `registration_area`, `publish_year`, `publisher`,
  `quality_score`, `source`); add composite indexes to match the materialized-view group keys.
- Expose `isbn_area_meta` and (future) `publishers` as small dimension tables the UI can join cheaply.

## Caveats to surface in the UI

- **Coverage is source-skewed.** Counts reflect which sources are loaded; Open Library inflates
  English/self-publishing (e.g. "Independently Published"). Always allow filtering by `source` and
  `quality_score`, and prefer authoritative sources per market (DNB for DE, LIBRIS for SE, Nielsen for GB).
- **Registration area = where the ISBN was issued**, a strong but imperfect proxy for where a book was
  published or sold.
- **In-print vs out-of-print** is unknown without a trade feed; do not imply availability.
