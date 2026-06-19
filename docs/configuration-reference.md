---
title: "ISBN Metadata Database -- Configuration Reference"
type: configuration-reference
status: draft
author: "Crius Technology"
sidebar_label: Configuration Reference
sidebar_position: 3
tags:
  - isbn
  - configuration
---

# ISBN Metadata Database -- Configuration Reference

## Overview

The `isbn-db` CLI is configured almost entirely through environment variables, with sensible
defaults that work for local development out of the box. A small number of operational constants
(batch sizes, OAI endpoint) are defined in code.

| Property | Value |
|---|---|
| **Service / Application** | `isbn-db` CLI + PostgreSQL |
| **Version** | 0.1.0 |
| **Configuration Sources** | Environment variables; in-code constants |
| **Precedence Order** | Environment variables > in-code defaults |

## Configuration Parameters

### Database

| Key | Type | Default | Required | Description | Example | Validation |
|-----|------|---------|----------|-------------|---------|------------|
| `ISBN_DB_DSN` | string | `postgresql://isbn:isbn@localhost:5433/isbn` | No | PostgreSQL connection string used by every command. | `postgresql://isbn:isbn@db:5432/isbn` | Valid libpq DSN |

### Data / Filesystem

| Key | Type | Default | Required | Description | Example | Validation |
|-----|------|---------|----------|-------------|---------|------------|
| `ISBN_DATA_DIR` | path | `./data` (repo `data/`) | No | Directory for downloaded dumps and run logs. Git-ignored. | `/mnt/big/isbn-data` | Writable directory |

### SonarQube (development only)

| Key | Type | Default | Required | Description | Example | Validation |
|-----|------|---------|----------|-------------|---------|------------|
| `SONAR_TOKEN` | string | -- | No | Token used by `sonar-scan.sh` to authenticate the scan. | `sqp_...` | Non-empty string |
| `SONAR_URL` | string | `http://localhost:9001` | No | SonarQube server URL for the scan. | `http://localhost:9001` | Valid URL |

### In-code operational constants

These are not environment variables; they are defined in source and listed here for completeness.

| Key | Type | Default | Required | Description | Example | Validation |
|-----|------|---------|----------|-------------|---------|------------|
| `BATCH_SIZE` (`ingest/common.py`) | integer | `2000` | No | Rows per upsert batch for file-based ingest. | `2000` | Positive integer |
| `CHECKPOINT_EVERY` (`ingest/common.py`) | integer | `50000` | No | Lines between progress checkpoints. | `50000` | Positive integer |
| `BATCH_SIZE` (`ingest/libris.py`) | integer | `1000` | No | Rows per upsert batch for the OAI harvest. | `1000` | Positive integer |
| `OAI_BASE` (`ingest/libris.py`) | string | `https://libris.kb.se/api/oaipmh/` | No | LIBRIS OAI-PMH endpoint. | (default) | Valid URL |

## Feature Flags

The application has no runtime feature-flag system. Behavioral toggles are expressed as CLI flags on
individual commands rather than global flags:

| Flag | Default | Description | Lifecycle Stage |
|------|---------|-------------|-----------------|
| `--no-resume` (ingest commands) | off | Ignore the saved checkpoint and re-ingest from the start. | GA |
| `--rescore` (`score`) | off | Recompute quality scores for all rows, not just unscored ones. | GA |
| `--redo` (`derive-areas`) | off | Recompute `registration_area` for all rows. | GA |
| `--limit N` (ingest commands) | unset | Stop after N valid records (for testing). | GA |

## Environment-Specific Overrides

| Key | Development | Staging | Production | Notes |
|-----|-------------|---------|------------|-------|
| `ISBN_DB_DSN` | `...@localhost:5433/isbn` | N/A | managed Postgres DSN | Only local exists today |
| `ISBN_DATA_DIR` | `./data` | N/A | large-disk mount | Dumps are tens of GB |

## Secret Management

| Secret Parameter | Storage Method | Rotation Policy |
|------------------|---------------|-----------------|
| `ISBN_DB_DSN` (contains DB password) | Environment variable / local shell only; never committed | On DB credential change |
| `SONAR_TOKEN` | Developer shell profile (`~/.zshrc`) | Per SonarQube policy |

Secrets must never be committed. `.env`, `data/`, and `.claude/settings.local.json` are git-ignored.
For paid feeds (Nielsen/VLB), any delivered credentials are kept out of the repository.

## Startup Validation

The CLI performs minimal explicit validation and otherwise fails fast:

- **Missing database / bad DSN:** the first command that connects raises a `psycopg` connection
  error and exits non-zero with the underlying message.
- **Invalid value (e.g. malformed ISBN in input):** the record is skipped during ingest, not fatal.
- **Missing `sonar-project.properties` for a scan:** `sonar-scan.sh` exits with an explanatory error.
- **Deprecated parameter:** none currently defined.

## Deprecated Parameters

| Key | Deprecated Since | Removed In | Replacement | Notes |
|-----|-----------------|------------|-------------|-------|
| None | -- | -- | -- | No parameters are deprecated at version 0.1.0. |

---

| Version | Date       | Author            | Changes        |
|---------|------------|-------------------|----------------|
| 0.1     | 2026-06-19 | Crius Technology  | Initial draft  |
