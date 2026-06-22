---
title: "ISBN Metadata Database -- Hosting & Operations Design"
type: reference
status: draft
author: "Crius Technology"
sidebar_label: Hosting & Operations
sidebar_position: 8
tags:
  - isbn
  - aws
  - hosting
  - operations
---

# ISBN Metadata Database -- Hosting & Operations Design

Planning document. No infrastructure is being provisioned yet. This describes how to move the
current local system (PostgreSQL container + CLI ingest) to a hosted AWS deployment and how weekly
data refresh would work once hosted.

---

## 1. Goal & overview

The database currently runs on a single developer machine: a PostgreSQL container holding ~39.2 M
rows, populated by manual CLI ingest. The target state is a hosted, queryable service that three
clients consume via one HTTP API:

- **Explorer UI** (`crius-projects/core-ui`, Next.js, ECS) — server-side fetch for search and
  dashboard views.
- **MCP server** (`crius-projects/llm-gateway`, ECS) — `httpx.AsyncClient` wrapper for tool calls
  from LLM agents.
- **Direct callers** — ad-hoc scripts and future integrations.

The FastAPI service (`isbn-db serve`, under `src/isbn_db/api/`) is the single entry point for all
three. No client talks to the database directly.

---

## 2. Database migration to AWS RDS

### Target

**AWS RDS for PostgreSQL 16**, `gp3` storage. The loaded database is tens of GB; provision at least
100 GB initially with autoscaling enabled. The dataset is read-heavy after ingest — a single
Multi-AZ RDS instance suffices. Add a read replica only if query concurrency from the UI and MCP
server warrants it.

**Aurora PostgreSQL** is the scale-up path if the instance reaches its I/O ceiling or if a
serverless burst profile is needed; the application connection string is the only thing that changes.

### Migration steps

```bash
# 1. Dump from the local container
docker exec isbn-postgres pg_dump -U isbn -d isbn -Fc -f /tmp/isbn.dump
docker cp isbn-postgres:/tmp/isbn.dump ./isbn.dump

# 2. Upload to S3 (keeps the dump off the developer machine)
aws s3 cp isbn.dump s3://<bucket>/isbn-db/isbn.dump

# 3. Restore into RDS (run from an EC2 instance or ECS task in the same VPC)
pg_restore --no-owner --no-acl -h <rds-endpoint> -U isbn -d isbn isbn.dump

# 4. Build expensive indexes AFTER bulk load (faster than building during restore)
psql -h <rds-endpoint> -U isbn -d isbn -c "
    CREATE INDEX CONCURRENTLY IF NOT EXISTS editions_title_trgm
        ON editions USING GIN (title gin_trgm_ops);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS editions_publisher_trgm
        ON editions USING GIN (publisher gin_trgm_ops);
"

# 5. Refresh materialized views (stats endpoints depend on these)
psql -h <rds-endpoint> -U isbn -d isbn -c "REFRESH MATERIALIZED VIEW CONCURRENTLY <view>;"
```

`CREATE INDEX CONCURRENTLY` is IO-heavy; run it during off-peak hours and monitor `pg_stat_progress_create_index`.

### Credentials

Store the RDS master password and application DSN in **AWS Secrets Manager**. The ECS task
definition references the secret ARN; the application reads `ISBN_DB_DSN` from the injected
environment. No credentials in code or environment files.

---

## 3. API hosting on ECS Fargate

### Container

Build a Docker image from `src/isbn_db/api/`:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync --no-dev
EXPOSE 8000
# `isbn-db serve` runs the FastAPI app (created by isbn_db.api.create_app) under uvicorn.
CMD ["uv", "run", "isbn-db", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

For multiple workers, swap the CMD for gunicorn with the uvicorn worker and the app factory
(`gunicorn "isbn_db.api:create_app()" -k uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:8000`).

Push to **ECR**. Tag with the git SHA; the ECS task definition references the SHA-tagged image.

### ECS Fargate service

Deploy behind an **Application Load Balancer** (ALB), matching the pattern already used in
`crius-projects/core-ui/terraform` and `crius-projects/llm-gateway/terraform`.

**Terraform resource sketch** (resource names, not full HCL):

| Resource | Notes |
|---|---|
| `aws_db_instance.isbn_rds` | PostgreSQL 16, gp3, multi-AZ |
| `aws_secretsmanager_secret.isbn_dsn` | holds `ISBN_DB_DSN` |
| `aws_secretsmanager_secret.isbn_api_key` | bearer token for external callers |
| `aws_ecr_repository.isbn_api` | Docker image registry |
| `aws_ecs_task_definition.isbn_api` | Fargate; reads secrets from Secrets Manager |
| `aws_ecs_service.isbn_api` | desired count 1–2; auto-scales on CPU |
| `aws_lb_target_group.isbn_api` | port 8000, health check `GET /health` |
| `aws_lb_listener_rule.isbn_api` | ALB path `/v1/*` and `/health` → target group |
| `aws_security_group.isbn_api` | allows ALB → task on 8000 |
| `aws_security_group.isbn_rds` | allows isbn_api SG → RDS on 5432 |

The API is **private to the VPC**; the ALB has no public listener. The UI fetches from the ALB DNS
name over the internal VPC network. External callers supply a bearer API key (validated in the
FastAPI middleware); that key lives in Secrets Manager.

---

## 4. Coupling architecture

```
                     VPC (private)
  ┌──────────────────────────────────────────────────┐
  │                                                  │
  │   Explorer UI (ECS) ──────────────────────────▶  │
  │                        ISBN API (ALB / ECS)      │
  │   MCP server  (llm-gateway ECS) ───────────────▶ │──▶ RDS PostgreSQL 16
  │                                                  │
  └──────────────────────────────────────────────────┘

  Direct callers (scripts, admin) ──bearer key──▶ ALB
```

**One API, three clients.** The connection URL is configured per environment:

| Environment | `ISBN_API_URL` |
|---|---|
| Local development | `http://localhost:8000` |
| Hosted (UI / MCP) | `http://<alb-internal-dns>` (VPC-internal) |

The UI sets `ISBN_API_URL` in its ECS task environment. The MCP server wraps every call in an
`httpx.AsyncClient` with `base_url=settings.isbn_api_url`.

---

## 5. Weekly data refresh — source support matrix

### Current status per source

| Source | Market | Incremental support | Status | Gap / required work |
|---|---|---|---|---|
| LIBRIS | SE | OAI-PMH datestamp windowing (from/until) | Ready with minor work | Add `--since <date>` flag so callers pass an arbitrary cutoff (e.g. `--since 8d`); today the harvester is parameterized by year/month |
| DNB | DE (priority) | None — full binary MARC21 dump only | Not ready | Build `ingest-dnb-oai` harvester using DNB's OAI-PMH endpoint, mirroring `libris.py`; most important gap given DE is a priority market |
| Open Library | Global | None — monthly full dump only | Not ready | Option A: harvest the Open Library recent-changes API for deltas. Option B: accept monthly full reloads on a larger schedule |
| ONIX (Nielsen UK / VLB DE) | UK, DE | Depends on subscription tier | Tooling ready | `src/isbn_db/ingest/onix.py` streams any delivered file; incremental feeds are a procurement matter, not a tooling gap |

### Scheduler

There is no scheduler today — all ingest is manual CLI. The recommended design:

**AWS EventBridge Scheduler** → weekly ECS `RunTask` (same task definition as the API, different
command override) running:

```bash
isbn-db ingest-libris --since 8d
# isbn-db ingest-dnb-oai --since 8d   # once built
isbn-db score
isbn-db derive-areas
isbn-db refresh-aggregates            # REFRESH MATERIALIZED VIEW on all stat views
```

The `ingest_state` table provides idempotency; re-running a completed window is a no-op.

### Conclusion

Weekly automated refresh is **partially achievable today**:

- LIBRIS (Sweden) is weekly-ready after adding the `--since` flag.
- DNB (Germany, priority market) requires a new OAI-PMH harvester before it can receive
  incremental updates — this is the highest-priority tooling gap.
- Open Library requires either a new delta harvester or acceptance of periodic full reloads.
- ONIX incremental delivery is a subscription/procurement decision, not a tooling issue.
- A scheduler (EventBridge → ECS RunTask) must be provisioned before any refresh is automated.

"Weekly automated refresh" is not complete until the DNB OAI harvester and the EventBridge
scheduler are built and deployed.

---

## 6. Operational notes

### Backups

RDS automated snapshots are enabled by default (retain 7 days minimum; extend to 14 for production).
The `isbn.dump` S3 copy produced during migration serves as the baseline restore point before RDS
snapshots begin.

### Materialized view refresh

The `/v1/stats/*` endpoints read from materialized views, which become stale after each ingest run,
so the weekly pipeline must always end with `isbn-db refresh-aggregates`. The current command issues
a plain `REFRESH MATERIALIZED VIEW`, which briefly locks each view (acceptable for an occasional
weekly refresh). For zero-downtime refreshes in production, add a `UNIQUE` index to each view and
switch the command to `REFRESH MATERIALIZED VIEW CONCURRENTLY`.

### Index build

The `pg_trgm` GIN indexes (`editions_title_trgm`, `editions_publisher_trgm`) power full-text search.
Always build them with `CREATE INDEX CONCURRENTLY`; the non-concurrent form takes an exclusive table
lock and will block the ingest pipeline and API for the entire build duration on a 39 M-row table.
Expect the build to take 20–40 minutes depending on RDS instance class.

### Quality score reset

A higher-tier source overwrite sets `quality_score` and `quality_flags` to NULL (by design in
`db.Edition.as_row()`). Always run `isbn-db score` after ingest to recompute scores on changed rows
before serving search results.
