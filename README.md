# ISBN

A database of ISBN / book metadata aggregated from authoritative and trade sources, built for
**publisher and market analysis**. Records from multiple national libraries, the open-data
ecosystem, and (optionally) paid trade feeds are normalized to a single canonical ISBN-13 key,
deduplicated by source authority, quality-scored, and tagged with the issuing country/language area.

Priority markets: **UK & Germany**, then **US**, then **Norway & Sweden**.

## What's in the database

One row per canonical ISBN-13 in PostgreSQL (`editions` table), merged across sources by authority
(registrar > national library > aggregator > crowd). Currently ingested:

| Source | Type | License | Editions |
|--------|------|---------|---------:|
| Open Library | global, crowd-sourced | public domain | ~31.6 M |
| DNB (Deutsche Nationalbibliothek) | German national library | CC0 | ~7.5 M |
| LIBRIS (National Library of Sweden) | Swedish national bibliography | CC0 | harvesting (OAI-PMH) |
| NielsenIQ BookData (UK) | UK ISBN agency, ONIX | paid | ingester ready — see `docs/PROCUREMENT.md` |

≈39 M editions, **0 invalid ISBNs** (all check-digit validated on ingest). Per-record completeness:
title 100%, publisher 98.7%, year 98.3%. See `docs/SOURCES.md` for the full source research and
`docs/ANALYSIS.md` for example queries.

## Architecture

```
ingest (per source) ──▶ normalize to ISBN-13 ──▶ editions (Postgres)
                                                   ├─ source-priority merge (dedupe)
                                                   ├─ quality_score + quality_flags
                                                   └─ registration_area (from ISBN)
```

- `src/isbn_db/isbn.py` — ISBN-10/13 validation, normalization, conversion (canonical key = ISBN-13).
- `src/isbn_db/sources.py` — source registry (tier, cost, licensing) driving the cross-source merge.
- `src/isbn_db/db.py` — schema + source-priority merge upsert.
- `src/isbn_db/ingest/` — streaming, resumable ingest:
  - `openlibrary.py` (TSV/JSON dumps), `dnb.py` (binary MARC21)
  - `marc.py` — shared MARC21 field extraction (DNB + LIBRIS)
  - `libris.py` — LIBRIS OAI-PMH MARCXML harvester (datestamp-chunked, resumable)
  - `onix.py` — ONIX 3.0 ingester for paid feeds (Nielsen UK, VLB DE)
- `src/isbn_db/quality.py` — per-record quality score (completeness + source authority + plausibility).
- `src/isbn_db/geo.py` — `registration_area` from the ISBN prefix (country/language area), source-independent.
- `src/isbn_db/cli.py` — the `isbn-db` command.

## Quick start

```bash
uv sync --extra dev

# Postgres (dedicated, isolated on port 5433)
docker run -d --name isbn-postgres -e POSTGRES_USER=isbn -e POSTGRES_PASSWORD=isbn \
  -e POSTGRES_DB=isbn -p 5433:5432 -v isbn_pgdata:/var/lib/postgresql/data \
  --restart unless-stopped postgres:16-alpine

uv run isbn-db init-db
```

Connection DSN (override with `ISBN_DB_DSN`): `postgresql://isbn:isbn@localhost:5433/isbn`

## Pipeline commands

```bash
# Ingest
./scripts/run_full_ingest.sh                                   # Open Library + DNB (download + ingest, resumable)
uv run isbn-db ingest-libris                                   # Swedish national bibliography (OAI-PMH)
uv run isbn-db ingest-onix nielsen.onix.xml --source nielsen   # paid ONIX file (UK), once delivered

# Enrich + analyze
uv run isbn-db score          # per-record quality scores (run after each ingest)
uv run isbn-db derive-areas   # country/language area from each ISBN
uv run isbn-db quality        # score distribution + flags
uv run isbn-db areas          # editions by registration area
uv run isbn-db stats          # row counts + ingest progress
```

## Development

```bash
uv run pytest                 # unit tests
uv run ruff check . && uv run ruff format .
./../../sonar-scan.sh "$(pwd)" --token "$SONAR_TOKEN"   # SonarQube scan
```

## Source strategy

Free authoritative backbone (DNB · Open Library · LIBRIS · Library of Congress) → targeted paid
one-offs for trade richness (Nielsen UK · VLB DE · ISBNdb) → reference-only for gap analysis &
enrichment (Anna's Archive · Google Books). Licensing and details in [`docs/SOURCES.md`](docs/SOURCES.md);
paid-feed procurement in [`docs/PROCUREMENT.md`](docs/PROCUREMENT.md).
