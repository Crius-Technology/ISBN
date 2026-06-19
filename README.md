# isbn-db

Acquire, normalize and analyze ISBN / book metadata from authoritative and trade sources, for
**publisher / market analysis**. Priority markets: **UK & Germany**, then **US**, then
**Norway & Sweden**.

## Status

**Open Library + DNB fully ingested — 39.15 M editions in Postgres.**

| Source | Editions | Status | Notes |
|--------|----------|--------|-------|
| Open Library (global, public domain) | 31.64 M | ✅ done | crowd-sourced backbone |
| DNB (Germany, CC0) | 7.51 M | ✅ done | national-library authoritative |
| LIBRIS — Sweden national bibliography (CC0) | harvesting | 🔄 OAI-PMH | national library; slow (~5/s) but resumable |
| NielsenIQ BookData (UK) | — | ⏸ ready, needs file | ONIX ingester built/tested; paid one-off load — see `docs/PROCUREMENT.md` |
| **Total ingested so far** | **39.15 M+** | | 0 invalid ISBNs; ISBN-13 canonical key |

UK note: the free British Library / BNB linked-data dumps are currently offline (BL cyberattack), so
UK coverage goes via Nielsen (paid). Norway has no open bulk source. See `docs/SOURCES.md`.

Field coverage: title 100%, publisher 98.7%, year 98.3%, language 86.7%, authors 90.6%, pages 58.6%.

Implemented:
- `src/isbn_db/isbn.py` — ISBN-10/13 validation, normalization, conversion (canonical key = ISBN-13).
- `src/isbn_db/sources.py` — source registry (tier, cost, licensing) driving the cross-source merge.
- `src/isbn_db/db.py` — schema (`editions`, `ingest_state`) + source-priority merge upsert.
- `src/isbn_db/ingest/` — streaming, resumable ingest:
  - `openlibrary.py` (TSV/JSON dumps), `dnb.py` (binary MARC21)
  - `marc.py` — shared MARC21 field extraction (used by DNB + LIBRIS)
  - `libris.py` — LIBRIS OAI-PMH MARCXML harvester (Swedish national bibliography, datestamp-chunked)
  - `onix.py` — ONIX 3.0 ingester for paid feeds (Nielsen UK, VLB DE)
- `src/isbn_db/quality.py` — per-record quality scoring (0-100 + flags): completeness + source authority + plausibility.
- `src/isbn_db/geo.py` — `registration_area` derived from the ISBN (country/language area), source-independent; data from the International ISBN Agency RangeMessage.
- `src/isbn_db/cli.py` — `init-db`, `ingest-openlibrary`, `ingest-dnb`, `ingest-libris`, `ingest-onix`, `score`, `quality`, `derive-areas`, `areas`, `stats`.
- `scripts/run_full_ingest.sh` — verified-download + full ingest driver (resumable).
- `docs/SOURCES.md` — source research; `docs/ANALYSIS.md` — example queries; `docs/PROCUREMENT.md` — paid-feed procurement.

Planned next: finish LIBRIS harvest; ingest Nielsen UK once procured; per-record quality scoring;
analysis layer / notebooks.

## New-source commands

```bash
uv run isbn-db ingest-libris                       # Swedish national bibliography (OAI-PMH, resumable)
uv run isbn-db ingest-onix nielsen.onix.xml --source nielsen   # paid ONIX file (UK), once delivered
```

## Database

Dedicated Postgres (isolated from other projects):

```bash
docker run -d --name isbn-postgres -e POSTGRES_USER=isbn -e POSTGRES_PASSWORD=isbn \
  -e POSTGRES_DB=isbn -p 5433:5432 -v isbn_pgdata:/var/lib/postgresql/data \
  --restart unless-stopped postgres:16-alpine
```

Connection DSN (override with `ISBN_DB_DSN`): `postgresql://isbn:isbn@localhost:5433/isbn`

## Ingest

```bash
uv run isbn-db init-db
./scripts/run_full_ingest.sh          # download + ingest everything (resumable)
uv run isbn-db stats                   # row counts + per-file progress
```

## Development

```bash
uv sync --extra dev
uv run pytest            # unit tests
uv run ruff check .
uv run ruff format .
```

## Source strategy (summary)

Free authoritative backbone (DNB · Open Library · Library of Congress · LIBRIS · British Library ·
Nasjonalbiblioteket) → targeted paid one-offs for trade richness (Nielsen UK · VLB DE · ISBNdb) →
reference-only for gap analysis & enrichment (Anna's Archive · Google Books). Full detail and
licensing in [`docs/SOURCES.md`](docs/SOURCES.md).
