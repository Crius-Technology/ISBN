# CLAUDE.md

Project-level guidance for Claude Code in this repository.

## What this project is

An ISBN / book-metadata database for **publisher and market analysis**. It ingests book metadata
from multiple sources (national libraries, open data, and optionally paid trade feeds), normalizes
everything to a canonical **ISBN-13** key in PostgreSQL, deduplicates by source authority, scores
each record's quality, and tags it with the issuing country/language area.

Priority markets: **UK & Germany**, then **US**, then **Norway & Sweden**.

## Architecture & key files

- `src/isbn_db/isbn.py` — ISBN-10/13 validation & normalization. **The canonical DB key is ISBN-13**;
  every ingested identifier passes through `isbn.normalize()`, and invalid check digits are rejected.
- `src/isbn_db/db.py` — `editions` schema + the source-priority merge upsert.
- `src/isbn_db/sources.py` — source registry (tier, cost, licensing, markets) driving the merge.
- `src/isbn_db/ingest/` — one streaming, resumable module per source format:
  `openlibrary.py` (TSV/JSON), `dnb.py` (binary MARC21), `libris.py` (OAI-PMH MARCXML),
  `onix.py` (ONIX 3.0 — Nielsen/VLB), and `marc.py` (shared MARC21 field extraction).
- `src/isbn_db/quality.py` — per-record quality score (completeness + source authority + plausibility).
- `src/isbn_db/geo.py` — `registration_area` from the ISBN prefix (source-independent), plus
  deterministic classification into `area_kind` + `country_iso2`. See `docs/ui-data-model.md`.
- `src/isbn_db/cli.py` — the `isbn-db` CLI.

## Data model

One row per ISBN-13 in `editions`. When the same ISBN comes from multiple sources, the upsert keeps
the **higher-tier** source (registrar 4 > national 3 > aggregator 2 > crowd 1); equal tier = last
writer wins. It is whole-record replacement, not field-level merge.

## Commands

```bash
uv sync --extra dev
uv run isbn-db init-db
./scripts/run_full_ingest.sh                                 # Open Library + DNB (resumable)
uv run isbn-db ingest-libris                                 # Swedish national bibliography
uv run isbn-db ingest-onix <file>.xml --source nielsen       # paid ONIX feed
uv run isbn-db score          # quality scores (run after each ingest)
uv run isbn-db derive-areas   # country/language area per ISBN
uv run isbn-db quality | areas | stats
```

Postgres runs in a dedicated container on **port 5433** (DSN env `ISBN_DB_DSN`, default
`postgresql://isbn:isbn@localhost:5433/isbn`) — isolated from other projects.

## Conventions

- **Python 3.13+, `uv`** for everything. Lint/format with `ruff` (line length 120); type-check with `mypy`.
- **Tests:** `pytest` (`uv run pytest`). Parsers are unit-tested against real sample records.
- **Before committing:** run `ruff check`, run the SonarQube scan (`sonar-project.properties` is set up;
  `../../sonar-scan.sh "$(pwd)" --token "$SONAR_TOKEN"`), and keep `README.md` + `docs/` current.
- Ingests are **streaming and resumable** (checkpoints in `ingest_state`); never load full dumps into
  memory and never commit the dumps (`data/` is git-ignored).

## Gotchas

- Text fields are length-capped in `db.Edition.as_row()` — some source records contain multi-KB
  garbage values that both pollute analysis and overflow the publisher B-tree index (2704-byte limit).
- A higher-tier overwrite resets `quality_score`/`quality_flags` to NULL so the next `score` run
  recomputes the changed row. Run `score` as the final step after each ingest.
- The LIBRIS OAI-PMH endpoint is slow (~5-6 records/sec); the harvest is chunked by datestamp and
  resumable, so it is meant to run in the background.

## Docs & MCP

Project docs live in `docs/` (`SOURCES.md`, `ANALYSIS.md`, `PROCUREMENT.md`). MCP servers (defined in
`.mcp.json`, auth via `LITELLM_API_KEY`) and the `.claude/` agents/commands are available; the
external doc-sync workflow is intentionally **not** enabled for this repo yet.
