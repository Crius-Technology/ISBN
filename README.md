---
title: "ISBN Metadata Database"
type: project-readme
status: draft
author: "Crius Technology"
sidebar_label: Project README
tags:
  - isbn
  - data-pipeline
---

# ISBN Metadata Database

![Python](https://img.shields.io/badge/python-3.13%2B-blue) ![Database](https://img.shields.io/badge/postgres-16-blue) ![License](https://img.shields.io/badge/license-internal-lightgrey)

## Description

A batch pipeline and analytical database that aggregates book metadata from authoritative and trade
sources — national libraries (DNB, LIBRIS), open data (Open Library), and optionally paid trade feeds
(Nielsen, VLB) — into a single PostgreSQL table keyed by canonical ISBN-13. Records are deduplicated
and merged by source authority, validated, quality-scored, and tagged with the issuing
country/language area, so the corpus can be queried directly for **publisher and market analysis**.
Priority markets: UK & Germany, then US, then Norway & Sweden.

## Key Features

- **Multi-source ingest** — Open Library (TSV/JSON), DNB (binary MARC21), LIBRIS (OAI-PMH MARCXML),
  and ONIX 3.0 (Nielsen/VLB), each streaming and resumable.
- **Canonical identity** — every record is keyed by a check-digit-validated ISBN-13 (ISBN-10s
  normalized in); ~39 M editions ingested with zero invalid ISBNs.
- **Source-priority merge** — one row per ISBN, the more authoritative source winning
  (registrar > national library > aggregator > crowd).
- **Per-record quality scoring** — 0–100 score plus explainable flags (completeness + source
  authority + plausibility).
- **Source-independent country attribution** — `registration_area` derived from the ISBN prefix using
  the official International ISBN Agency range data.
- **Single command per stage** — `isbn-db` CLI for ingest, scoring, area derivation, and stats.

## Quick Start

```bash
# Clone the repository
git clone git@github.com:Crius-Technology/ISBN.git
cd ISBN

# Install dependencies
uv sync --extra dev

# Start PostgreSQL (isolated on port 5433)
docker run -d --name isbn-postgres \
  -e POSTGRES_USER=isbn -e POSTGRES_PASSWORD=isbn -e POSTGRES_DB=isbn \
  -p 5433:5432 -v isbn_pgdata:/var/lib/postgresql/data \
  --restart unless-stopped postgres:16-alpine

# Initialise the schema and check the connection
uv run isbn-db init-db
uv run isbn-db stats
```

> For full setup, ingest, testing, and operational tasks, see the [Operations Guide](docs/operations-guide.md).

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.13+ |
| **Runtime** | CPython, `uv`-managed virtualenv |
| **Framework** | `argparse` CLI + `psycopg` 3 |
| **Database** | PostgreSQL 16 |
| **Parsing** | `pymarc` (MARC/MARCXML), stdlib (JSON/XML/ONIX) |
| **Tooling** | `ruff`, `pytest`, SonarQube |
| **Container** | Docker 24+ (PostgreSQL, Sonar scanner) |
| **CI/CD** | None configured yet |

## Project Structure

```
ISBN/
├── src/isbn_db/          # Application package
│   ├── isbn.py           # ISBN-10/13 validation & normalization
│   ├── sources.py        # Source registry (tier/cost/licensing)
│   ├── db.py             # Schema + source-priority merge upsert
│   ├── quality.py        # Per-record quality scoring
│   ├── geo.py            # registration_area derivation
│   ├── ingest/           # One module per source format (+ shared MARC)
│   └── cli.py            # `isbn-db` entry point
├── tests/                # pytest unit tests
├── scripts/              # run_full_ingest.sh, build_report.py, build_isbn_groups.py
├── docs/                 # Project documentation
├── sonar-project.properties
└── README.md             # This file
```

## Documentation

| Document | Description |
|---|---|
| [Operations Guide](docs/operations-guide.md) | Setup, running, testing, common tasks, troubleshooting |
| [Software Design](docs/software-design.md) | Architecture, data model, merge and scoring design |
| [Configuration Reference](docs/configuration-reference.md) | Environment variables and settings |
| [Sources](docs/SOURCES.md) | Where the data comes from (paid/free, quality, licensing) |
| [Analysis](docs/ANALYSIS.md) | Example analytical queries |
| [Procurement](docs/PROCUREMENT.md) | How to procure the paid trade feeds (Nielsen, VLB) |

## Contributing

1. Create a feature branch from `develop`
2. Make your changes following the conventions in [CLAUDE.md](CLAUDE.md)
3. Ensure all tests pass: `uv run pytest`
4. Ensure linting passes: `uv run ruff check .`
5. Run the SonarQube scan before committing (see the Operations Guide)
6. Open a Pull Request into `develop` with a clear description

## License

Internal project of Crius Technology. Not licensed for external distribution. Note that ingested
source data carries its own licences (e.g. CC0, public domain, or commercial) — see
[docs/SOURCES.md](docs/SOURCES.md) for per-source terms before redistributing any derived data.
