---
title: "ISBN Metadata Database -- Operations Guide"
type: operations-guide
status: draft
author: "Crius Technology"
sidebar_label: Operations Guide
sidebar_position: 2
tags:
  - isbn
  - operations
---

# ISBN Metadata Database -- Operations Guide

## 1. Project Overview

A batch pipeline and analytical database that aggregates book metadata from multiple bibliographic
sources into a single PostgreSQL table keyed by canonical ISBN-13, then deduplicates, quality-scores,
and country-tags each record for publisher and market analysis.

| Property | Value |
|---|---|
| **Repository** | `github.com/Crius-Technology/ISBN` |
| **Language / Runtime** | Python 3.13+ |
| **Framework** | CLI (`argparse`) + `psycopg` 3 |
| **Database** | PostgreSQL 16 |
| **Message Broker** | N/A |
| **Package Manager** | `uv` |
| **Container Runtime** | Docker 24+ (for PostgreSQL and the SonarQube scanner) |

## 2. Prerequisites

| Tool | Minimum Version | Verify Command |
|---|---|---|
| Python | 3.13 | `python3 --version` |
| uv | 0.9+ | `uv --version` |
| Docker | 24.x | `docker --version` |
| ruff | 0.14+ | `uv run ruff --version` |

Network access to the source providers is required for ingest: `openlibrary.org` / `archive.org`,
`data.dnb.de`, and `libris.kb.se`. Paid ONIX feeds (Nielsen/VLB) are delivered out-of-band as files.

## 3. Local Development Setup

### 3.1 Clone the Repository

```bash
git clone git@github.com:Crius-Technology/ISBN.git
cd ISBN
```

### 3.2 Install Dependencies

```bash
uv sync --extra dev
```

### 3.3 Configure Environment

Configuration is via environment variables (no `.env` file is required; defaults work for local use).

| Variable | Description | Example Value |
|---|---|---|
| `ISBN_DB_DSN` | PostgreSQL connection string | `postgresql://isbn:isbn@localhost:5433/isbn` |
| `ISBN_DATA_DIR` | Where dumps/logs are written | `./data` |

> See the [Configuration Reference](./configuration-reference.md) for the full list of parameters.

### 3.4 Set Up Local Services (Database)

```bash
docker run -d --name isbn-postgres \
  -e POSTGRES_USER=isbn -e POSTGRES_PASSWORD=isbn -e POSTGRES_DB=isbn \
  -p 5433:5432 -v isbn_pgdata:/var/lib/postgresql/data \
  --restart unless-stopped postgres:16-alpine

uv run isbn-db init-db
```

### 3.5 Start the Application

This is a CLI, not a long-running service. Verify the install and database connection:

```bash
uv run isbn-db stats
```

**Expected output:**

```
editions total: 0
by source:
ingest_state:
```

> **Checkpoint:** `init-db` created the `editions` and `ingest_state` tables and `stats` connected
> successfully. You are ready to ingest.

## 4. Running the Application

### Development Mode

Run individual pipeline stages via the CLI:

```bash
uv run isbn-db ingest-libris        # harvest Swedish national bibliography (slow, resumable)
uv run isbn-db score                # compute quality scores
uv run isbn-db quality              # inspect the score distribution
```

### Production Build

No build step. The full ingest is driven by a script that downloads and ingests Open Library + DNB:

```bash
./scripts/run_full_ingest.sh
```

### Watch / Hot-Reload

Not applicable (batch CLI). Long jobs are resumable: re-running a command continues from the last
checkpoint in `ingest_state`. The full-ingest script verifies downloads against `Content-Length`
before ingesting, and resumes partial downloads with `curl -C -`.

## 5. Testing

### Unit Tests

```bash
uv run pytest
```

Parsers are unit-tested against real sample records (MARC, MARCXML, ONIX, Open Library TSV/JSON).

### Integration Tests

```bash
uv run pytest -m integration
```

Integration-style checks that touch PostgreSQL require the `isbn-postgres` container (section 3.4)
to be running.

### End-to-End Tests

A lightweight end-to-end check is to ingest a small slice and verify counts:

```bash
uv run isbn-db ingest-openlibrary data/ol_dump_editions_latest.txt.gz --limit 5000
uv run isbn-db stats
```

### Test Coverage

```bash
uv run pytest -q
```

| Metric | Target |
|---|---|
| Core modules (isbn, parsers, quality, geo) | Covered by unit tests |
| Branch coverage | Best-effort; parser edge cases prioritized |

### Writing New Tests

- Unit tests: `tests/` as `test_*.py`
- Integration tests: mark with `@pytest.mark.integration`
- Naming convention: one test module per source/feature (e.g. `test_dnb.py`, `test_quality.py`)

## 6. Deployment

### Environment Overview

| Environment | URL | Branch / Trigger | Purpose |
|---|---|---|---|
| Local | N/A | `develop` | Run the pipeline and query the database directly |

This is an internal exploration project: there is no hosted deployment. The "deployment" is a local
PostgreSQL instance populated by the CLI. If promoted to a shared environment, the same container and
CLI run against a managed PostgreSQL.

### Deployment Procedure

1. Provision a PostgreSQL 16 instance and set `ISBN_DB_DSN`.
2. Run `uv run isbn-db init-db`.
3. Run `./scripts/run_full_ingest.sh`, then `uv run isbn-db score` and `derive-areas`.

### Manual Deployment (if applicable)

```bash
ISBN_DB_DSN=postgresql://user:pass@host:5432/isbn uv run isbn-db init-db
```

## 7. CI/CD Pipeline

| Property | Value |
|---|---|
| **CI/CD Platform** | None configured yet |
| **Config File** | N/A |
| **Trigger** | N/A |

There is currently no CI/CD pipeline for this repository (the template's doc-sync workflows were
removed). Quality gates are run locally before committing.

### Pipeline Stages

1. **Lint** -- `uv run ruff check .`
2. **Format check** -- `uv run ruff format --check .`
3. **Test** -- `uv run pytest`
4. **Security/Quality Scan** -- SonarQube (`sonar-scan.sh`)

### Triggering a Pipeline Manually

Run the gates locally:

```bash
uv run ruff check . && uv run pytest && ../../sonar-scan.sh "$(pwd)" --token "$SONAR_TOKEN"
```

### Common CI Failures

| Failure | Cause | Fix |
|---|---|---|
| Lint failure | Unformatted/long lines | `uv run ruff format .` then re-check |
| Sonar: properties missing | No `sonar-project.properties` | Already present at repo root |
| Test import error | Missing dev deps | `uv sync --extra dev` |

## 8. Common Tasks

### Database Schema / Migrations

The schema is created idempotently; there is no migration tool. `init-db` adds any missing columns:

```bash
uv run isbn-db init-db
```

### Re-running Enrichment

```bash
uv run isbn-db score          # only scores rows with a NULL quality_score
uv run isbn-db score --rescore   # recompute all scores (after a formula change)
uv run isbn-db derive-areas   # populate registration_area for new rows
```

### Refreshing the ISBN Range Table

```bash
curl -s https://www.isbn-international.org/export_rangemessage.xml -o data/RangeMessage.xml
uv run python scripts/build_isbn_groups.py
uv run isbn-db derive-areas --redo
```

### Linting and Formatting

```bash
uv run ruff check .
uv run ruff format .
```

## 9. Troubleshooting

| Symptom | Cause | Solution |
|---|---|---|
| `connection refused` on `init-db`/`stats` | Postgres container not running | `docker start isbn-postgres` (or recreate per 3.4) |
| Ingest crashes with `EOFError` on a `.gz` | Truncated/incomplete download | Re-run `run_full_ingest.sh`; it verifies size and resumes |
| `index row size ... exceeds btree maximum` | Oversized field value | Already handled — text fields are length-capped in `db.Edition.as_row()` |
| Scorer `DeadlockDetected` | Ran during an active ingest | Handled via `FOR UPDATE SKIP LOCKED` + retry; just re-run `score` |
| LIBRIS harvest very slow | OAI endpoint ~5-6 records/sec | Expected; it is chunked and resumable — leave it running in the background |

---

| Version | Date       | Author            | Changes        |
|---------|------------|-------------------|----------------|
| 0.1     | 2026-06-19 | Crius Technology  | Initial draft  |
