---
title: "ISBN Database -- Analysis Examples"
type: reference
status: draft
author: "Crius Technology"
sidebar_label: Analysis
sidebar_position: 5
tags:
  - isbn
  - analysis
---

# Analysis Examples

The `editions` table (39.15 M rows) keyed by canonical ISBN-13. Connect:

```bash
docker exec -it isbn-postgres psql -U isbn -d isbn
```

## Data-quality snapshot (verified after ingest)

```sql
-- ISBN validity: every row passed check-digit validation on ingest
SELECT count(*) FILTER (WHERE isbn13 ~ '^(978|979)[0-9]{10}$') AS valid,
       count(*) FILTER (WHERE isbn13 !~ '^(978|979)[0-9]{10}$') AS invalid
FROM editions;            -- 39,150,344 valid / 0 invalid

-- Field coverage
SELECT round(100.0*count(title)/count(*),1)        AS pct_title,
       round(100.0*count(publisher)/count(*),1)    AS pct_publisher,
       round(100.0*count(publish_year)/count(*),1) AS pct_year
FROM editions;            -- title 100% / publisher 98.7% / year 98.3%
```

## Market & publisher analysis

```sql
-- Top publishers overall
SELECT publisher, count(*) n FROM editions
WHERE publisher IS NOT NULL GROUP BY publisher ORDER BY n DESC LIMIT 20;

-- German market (authoritative DNB records): top publishers
SELECT publisher, count(*) n FROM editions
WHERE source='dnb' AND publisher IS NOT NULL
GROUP BY publisher ORDER BY n DESC LIMIT 20;

-- Output growth by decade
SELECT (publish_year/10*10) AS decade, count(*) n FROM editions
WHERE publish_year BETWEEN 1950 AND 2026 GROUP BY 1 ORDER BY 1;

-- Language distribution
SELECT lang, count(*) n FROM editions, unnest(languages) lang
GROUP BY lang ORDER BY n DESC LIMIT 15;

-- A specific publisher's catalogue over time
SELECT publish_year, count(*) n FROM editions
WHERE publisher ILIKE '%Springer%' AND publish_year IS NOT NULL
GROUP BY 1 ORDER BY 1 DESC LIMIT 20;
```

## Quality scoring

Every edition has a `quality_score` (0-100) and `quality_flags` (see `src/isbn_db/quality.py`):
completeness (0-70, weighted field presence) + source authority (0-20, `source_tier`×5) +
plausibility (0-10). Recompute with `uv run isbn-db score`; summarise with `uv run isbn-db quality`.

```sql
-- Distribution
SELECT (quality_score/10*10) AS bucket, count(*) FROM editions
WHERE quality_score IS NOT NULL GROUP BY 1 ORDER BY 1 DESC;

-- Average quality by source (authority + completeness differences show here)
SELECT source, round(avg(quality_score),1) avg_q, count(*) FROM editions GROUP BY source ORDER BY 2 DESC;

-- High-confidence subset for analysis (e.g. authoritative + complete)
SELECT * FROM editions WHERE quality_score >= 80;

-- What's dragging a record down
SELECT f, count(*) FROM editions, unnest(quality_flags) f GROUP BY f ORDER BY 2 DESC;
```

*Cross-source agreement is not scored — the merged table keeps only the winning source's values.
Adding a raw per-source layer to enable agreement checks is future work.*

## Country / language area (de-skewing source bias)

`registration_area` is derived from the ISBN registration-group prefix (see `src/isbn_db/geo.py`,
data from the International ISBN Agency RangeMessage) — it reflects the country/language area that
**issued** the ISBN, independent of which source supplied the record. Populate with
`uv run isbn-db derive-areas`; view with `uv run isbn-db areas`.

```sql
-- True title distribution by issuing country/language area (not biased by source coverage)
SELECT registration_area, count(*) FROM editions GROUP BY 1 ORDER BY 2 DESC LIMIT 20;

-- German-language output over time, regardless of source
SELECT publish_year, count(*) FROM editions
WHERE registration_area = 'German language' AND publish_year BETWEEN 2000 AND 2025
GROUP BY 1 ORDER BY 1;

-- Compare a source's coverage vs the ISBN universe for an area
SELECT source, count(*) FROM editions WHERE registration_area = 'Sweden' GROUP BY 1 ORDER BY 2 DESC;
```

Note: areas like "English language" (978-0/978-1) and "German language" (978-3) are language areas
spanning several countries; others (Sweden 978-91, United States 979-8) are single countries. The
ISBN encodes the *registration* area, which is the publisher's agency — a strong but not perfect
proxy for where a book was published.

## Notes on merge semantics
- One row per ISBN-13. When the same ISBN appears in multiple sources, the higher-tier source wins
  (DNB national > Open Library crowd) — so German titles carry authoritative metadata where available.
- `source` column records which source won each row; filter on it to compare source coverage.
