# CLAUDE.md

Project-level instructions for Claude Code in repositories using this template.

## Documentation Structure

This project uses a three-category template system:

- **Specification templates** (`docs/` directory): Technical documentation like ADRs, API contracts, runbooks, meeting summaries. Each doc must have YAML frontmatter with `title`, `type`, and `status` fields.
- **Cross-cutting templates** (`docs/` directory): Project-wide documents like glossaries that span across specifications. Placed alongside specification docs with the same frontmatter requirements.
- **Repository templates** (root-level files): Files like `README.md` that live at the repository root.

## Template Convention

All documentation files in `docs/` must have YAML frontmatter:

```yaml
---
title: "Document Title"
type: template-type-id
status: draft|in-review|approved|deprecated|archived
---
```

The `type` field must match a known template type from the docs-agent, the catch-all `other`, or `reference`. Templates can be used multiple times (e.g. multiple `api-contract-rest` documents for different APIs).

## Available MCP Servers

MCP server auth is configured via the `LITELLM_API_KEY` environment variable. Servers are defined in `.mcp.json`.

| Server | Description |
|--------|-------------|
| `doc-templates` | Documentation template management + document discovery/fetch over crius-docs (list, get, search, get_file) |
| `alice-docs` | Alice documentation lookup + company knowledge-base semantic search (`rag_search`) over the indexed docs incl. crius-docs (multi-repo RAG backend). |
| `knowledge-graph` | Neo4j knowledge-graph traversal over crius-docs (`graph_search`, `find_related`, `find_path`, `get_entity`, `graph_stats`). For relational questions — how concepts/docs connect, impact analysis. |
| `xproc-agent` | XProc pipeline assistance |
| `redmine` | Redmine project management integration |

### doc-templates Tools

- **`list_templates`** - List available templates. Accepts optional `category` filter (`"specification"`, `"repository"`, or `"cross-cutting"`).
- **`get_template`** - Get full markdown content of a template by `template_type`.
- **`evaluate_doc`** - Evaluate a document against its template (structural checks, frontmatter validation, placeholder detection).

### Document Discovery & Fetch Tools (via doc-templates MCP)
- **`list_documents`** — List docs with metadata. Filter by type (adr, runbook, software-design, business-process, etc.), domain, status, or tag.
- **`get_document`** — Get full content of a document by its ID (e.g., `ADR-API-005`).
- **`search_documents`** — Search documents by natural language keyword query.
- **`get_file`** — Get the full content of a file by its repository path (e.g. `docusaurus/technology/.../overview.md`). Use to expand a `rag_search` semantic hit (`metadata.file_path`) into the whole document.

### Knowledge Semantic Search (via alice-docs MCP)
- **`rag_search`** — Similarity search over full document content; pass `repos=["crius_docs"]` to scope to the company docs hub. Returns chunk snippets plus each hit's `metadata.file_path` for follow-up `get_file`.

### Knowledge Graph Traversal (via knowledge-graph MCP)
Relational discovery over a Neo4j graph built from crius-docs. Each node carries a `source_file` to feed into fetch. Use for questions index/semantic search handle poorly.
- **`graph_search`** — Find entry nodes by keyword (start here).
- **`find_related`** — Neighbourhood / impact analysis: what relates to or depends on X (`hops=1..3`).
- **`find_path`** — Shortest relationship chain between two concepts ("how are X and Y connected").
- **`get_entity`** — One node plus all its direct edges.
- **`graph_stats`** — Counts and top hub concepts; orient before deep traversal.

### Knowledge Search Skill
The **`knowledge-search`** skill (`.claude/skills/knowledge-search/`) is auto-invoked when you ask about company/internal documentation, ADRs, runbooks, "where is X documented", or relational questions ("how are X and Y connected", "what depends on Z"). It runs a **discover → fetch → cite** loop across three channels — index-catalog exploration (`index.json` / `list_documents`), semantic search (`rag_search`), and graph traversal (`graph_search` & friends) — collecting `file_path`s from each, then fetching the full files so answers are grounded in real docs.

## Available Agents

| Agent | Description | Tools |
|-------|-------------|-------|
| `code-reviewer` | Comprehensive code reviews — quality, security, architecture, performance, dependencies | Read, Write, Edit, Bash, Glob, Grep |
| `security-auditor` | Security audits and compliance assessments (read-only) | Read, Grep, Glob |
| `debugger` | Bug diagnosis, root cause analysis, and systematic debugging | Read, Write, Edit, Bash, Glob, Grep |
| `refactoring-specialist` | Safe code transformation preserving existing behavior | Read, Write, Edit, Bash, Glob, Grep |
| `python-backend-engineer` | Python/FastAPI/Django/Flask backend development with uv tooling | Read, Write, Edit, Bash, Glob, Grep |
| `frontend-developer` | React/Next.js/TypeScript frontend development with Tailwind CSS | Read, Write, Edit, Bash, Glob, Grep |
| `test-engineer` | Tests across backend (pytest) and frontend (Jest/Playwright) | Read, Write, Edit, Bash, Glob, Grep |
| `documentation-engineer` | API docs, README, ADRs, runbooks, technical writing | Read, Write, Edit, Bash, Glob, Grep |
| `performance-optimizer` | Profiling, query optimization, caching, bundle size | Read, Write, Edit, Bash, Glob, Grep |
| `spring-boot-engineer` | Spring Boot 3+ microservices, reactive APIs, Spring Cloud patterns | Read, Write, Edit, Bash, Glob, Grep |
| `api-designer` | REST/GraphQL API design, OpenAPI specs, versioning, developer experience | Read, Write, Edit, Bash, Glob, Grep |
| `java-architect` | Enterprise Java architecture, DDD, Clean Architecture, microservices patterns | Read, Write, Edit, Bash, Glob, Grep |
| `cloud-architect` | AWS cloud infrastructure, migration planning, cost optimization, security posture | Read, Write, Edit, Bash, Glob, Grep |
| `devops-engineer` | CI/CD pipelines, container orchestration, monitoring, infrastructure automation | Read, Write, Edit, Bash, Glob, Grep |
| `terraform-engineer` | Terraform IaC, module development, state management, multi-environment deployments | Read, Write, Edit, Bash, Glob, Grep |
| `powershell-7-expert` | PowerShell 7+ automation, Azure, Graph API, InDesign scripting | Read, Write, Edit, Bash, Glob, Grep |
| `business-analyst` | Business process analysis, requirements elicitation, stakeholder management | Read, Write, Edit, Glob, Grep, WebFetch, WebSearch |
| `product-manager` | Product strategy, feature prioritization, roadmap planning | Read, Write, Edit, Glob, Grep, WebFetch, WebSearch |
| `technical-writer` | API references, user guides, SDK docs, getting-started guides | Read, Write, Edit, Glob, Grep |
| `scrum-master` | Agile facilitation, sprint planning, retrospectives, impediment removal | Read, Write, Edit, Glob, Grep |
| `competitive-analyst` | Competitor analysis, benchmarking, market positioning (read-only + web) | Read, Grep, Glob, WebFetch, WebSearch |
| `market-researcher` | Market sizing, consumer behavior, competitive landscapes (read-only + web) | Read, Grep, Glob, WebFetch, WebSearch |
| `context-manager` | Shared state management, information retrieval, data synchronization | Read, Write, Edit, Glob, Grep |

## Agent Teams

Agent teams are enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json`. This allows Claude Code to natively spawn and coordinate multiple agents working in parallel on complex tasks.

- **Max parallel tasks:** 6 (configured via `CLAUDE_CODE_MAX_PARALLEL_TASKS`)
- Claude Code handles agent team orchestration automatically — no additional configuration needed
- Agents can be combined for workflows like: code review + security audit, or backend + frontend + tests in parallel

## Permissions Model

The project configures three permission tiers in `.claude/settings.json`:

- **Allow** (~47 rules): Read-only git commands, file inspection utilities, text processing tools, version/help flags
- **Ask** (~21 rules): Destructive-but-useful operations — git push, rm -r, docker cleanup, GitHub CLI actions affecting shared state
- **Deny** (~58 rules): Filesystem destruction, pipe-to-shell execution, reverse shells, credential exfiltration, system shutdown, log tampering, dangerous Docker mounts, force-push to protected branches, reading secrets/env files

## Custom Commands

- **`/generate-docs`** - Generate and validate all project documentation using templates from the MCP server. Works without any configuration — auto-detects the docs directory (checks `.doc-config.yml`, then scans for `docs/` or `00-docs/`). Scans existing docs, creates missing ones, evaluates and fixes existing ones.
- **`/check-compliance`** - Check codebase against applicable architectural decision records (ADRs). Discovers relevant ADRs via document tools and reports compliance status (compliant, non-compliant with file references, or not applicable).

## Configuration

`.doc-config.yml` is used by **CI workflows only** (doc-sync, quality gates) — not by `/generate-docs`:
- `project_name` - Project identifier (falls back to repo name from `GITHUB_REPOSITORY`)
- `docs_dir` - Documentation directory (default: `docs`)
- `doc_sync` - Target repo, base path, sidebar categories, and GitHub App config for doc-sync workflow
