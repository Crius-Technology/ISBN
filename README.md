# repo-template

Repository template with documentation automation workflows and comprehensive Claude Code defaults.

## What's included

### Workflows (`.github/workflows/`)

| Workflow | Trigger | Description |
|----------|---------|-------------|
| `doc-code-consistency.yml` | PR to develop | Claude Code CLI checks doc-code consistency via MCP tools |
| `doc-sync.yml` | Push to develop | Syncs docs to external Docusaurus repository |

### Scripts (`.github/scripts/`)

| Script | Purpose |
|--------|---------|
| `config_loader.py` | Loads `.doc-config.yml` with defaults |
| `doc_sync.py` | Doc sync to external repository |
| `github_pr.py` | Post/update PR comments |

### Claude Code (`.claude/`)

| File | Purpose |
|------|---------|
| `.claude/settings.json` | Permissions (allow/ask/deny) |
| `.claude/commands/generate-docs.md` | Custom `/generate-docs` command for documentation generation |
| `.claude/agents/code-reviewer.md` | Code review agent — quality, security, architecture, performance, dependencies |
| `.claude/agents/security-auditor.md` | Security audit agent — vulnerability assessment, compliance (read-only) |
| `.claude/agents/debugger.md` | Debugging agent — root cause analysis, systematic debugging |
| `.claude/agents/refactoring-specialist.md` | Refactoring agent — safe code transformation |
| `.claude/agents/python-backend-engineer.md` | Python/FastAPI/Django/Flask backend development with uv tooling |
| `.claude/agents/frontend-developer.md` | React/Next.js/TypeScript frontend development |
| `.claude/agents/test-engineer.md` | Tests across backend (pytest) and frontend (Jest/Playwright) |
| `.claude/agents/documentation-engineer.md` | API docs, README, ADRs, runbooks, technical writing |
| `.claude/agents/performance-optimizer.md` | Profiling, query optimization, caching, bundle size |
| `.claude/agents/spring-boot-engineer.md` | Spring Boot 3+ microservices, reactive APIs, Spring Cloud |
| `.claude/agents/api-designer.md` | REST/GraphQL API design, OpenAPI specs, versioning |
| `.claude/agents/java-architect.md` | Enterprise Java architecture, DDD, Clean Architecture |
| `.claude/agents/cloud-architect.md` | AWS cloud infrastructure, migration, cost optimization |
| `.claude/agents/devops-engineer.md` | CI/CD pipelines, container orchestration, monitoring |
| `.claude/agents/terraform-engineer.md` | Terraform IaC, module development, state management |
| `.claude/agents/powershell-7-expert.md` | PowerShell 7+ automation, Azure, Graph API, InDesign |
| `.claude/agents/business-analyst.md` | Business process analysis, requirements, stakeholder management |
| `.claude/agents/product-manager.md` | Product strategy, feature prioritization, roadmap planning |
| `.claude/agents/technical-writer.md` | API references, user guides, SDK docs, getting-started guides |
| `.claude/agents/scrum-master.md` | Agile facilitation, sprint planning, retrospectives, impediment removal |
| `.claude/agents/competitive-analyst.md` | Competitor analysis, benchmarking, market positioning |
| `.claude/agents/market-researcher.md` | Market sizing, consumer behavior, competitive landscapes |
| `.claude/agents/context-manager.md` | Shared state management, information retrieval, data synchronization |

All agents include an **Internal Standards** section with inlined rules from the organization's ADRs (secrets management, RFC 7807 errors, layered architecture, OCI labels, etc.), scoped to each agent's role.

### Configuration

| File | Purpose |
|------|---------|
| `.mcp.json` | MCP server configuration with env var auth (`${LITELLM_API_KEY}`) |
| `.doc-config.yml` | Project-specific documentation config |
| `CLAUDE.md` | Project-level instructions for Claude Code |
| `.github/mcp-config.json` | MCP config template for Claude Code CLI (CI) |
| `.github/prompts/doc-code-consistency.md` | Prompt template for consistency checks |

## MCP Servers

Four MCP servers are configured for both local usage and CI:

| Server | Description |
|--------|-------------|
| `doc-templates` | Documentation template management — list, get, and evaluate templates |
| `alice-docs` | Alice documentation lookup |
| `xproc-agent` | XProc pipeline assistance |
| `redmine` | Redmine project management integration |

### doc-templates Tools

- **`list_templates`** - List available templates. Accepts optional `category` filter (`"specification"` or `"repository"`)
- **`get_template`** - Get full markdown content of a template by type
- **`evaluate_doc`** - Evaluate a document against its template (structural checks)

## Agents

Twenty-three reusable agents are available in `.claude/agents/`, each with an **Internal Standards** section containing inlined ADR rules relevant to their role:

| Agent | Description | Model |
|-------|-------------|-------|
| `code-reviewer` | Comprehensive code reviews — quality, security, architecture, performance, dependencies | sonnet |
| `security-auditor` | Security audits and compliance assessments (read-only) | sonnet |
| `debugger` | Bug diagnosis, root cause analysis, systematic debugging | sonnet |
| `refactoring-specialist` | Safe code transformation preserving existing behavior | sonnet |
| `python-backend-engineer` | Python/FastAPI/Django/Flask backend development with uv tooling | sonnet |
| `frontend-developer` | React/Next.js/TypeScript frontend development | sonnet |
| `test-engineer` | Tests across backend (pytest) and frontend (Jest/Playwright) | sonnet |
| `documentation-engineer` | API docs, README, ADRs, runbooks, technical writing | sonnet |
| `performance-optimizer` | Profiling, query optimization, caching, bundle size | sonnet |
| `spring-boot-engineer` | Spring Boot 3+ microservices, reactive APIs, Spring Cloud | sonnet |
| `api-designer` | REST/GraphQL API design, OpenAPI specs, versioning | sonnet |
| `java-architect` | Enterprise Java architecture, DDD, Clean Architecture | sonnet |
| `cloud-architect` | AWS cloud infrastructure, migration, cost optimization | sonnet |
| `devops-engineer` | CI/CD pipelines, container orchestration, monitoring | sonnet |
| `terraform-engineer` | Terraform IaC, module development, state management | sonnet |
| `powershell-7-expert` | PowerShell 7+ automation, Azure, Graph API, InDesign | sonnet |
| `business-analyst` | Business process analysis, requirements, stakeholder management | sonnet |
| `product-manager` | Product strategy, feature prioritization, roadmap planning | sonnet |
| `technical-writer` | API references, user guides, SDK docs, getting-started guides | sonnet |
| `scrum-master` | Agile facilitation, sprint planning, retrospectives, impediment removal | sonnet |
| `competitive-analyst` | Competitor analysis, benchmarking, market positioning | sonnet |
| `market-researcher` | Market sizing, consumer behavior, competitive landscapes | sonnet |
| `context-manager` | Shared state management, information retrieval, data synchronization | sonnet |

## Permissions

The template configures three permission tiers in `.claude/settings.json`:

- **Allow**: Read-only git, file inspection, text processing, version/help flags — safe for any project
- **Ask**: Destructive-but-useful operations (git push, rm -r, docker cleanup, GitHub CLI actions)
- **Deny**: Filesystem destruction, pipe-to-shell, reverse shells, credential exfiltration, force-push to protected branches, reading secrets/env files

## Template Categories

The docs-agent organizes templates into two categories:

- **Specification templates** (`category: specification`): Templates for `docs/` directory files (ADRs, API contracts, meeting summaries, runbooks, etc.)
- **Repository templates** (`category: repository`): Templates for root-level files (README.md, etc.)

Templates can be used multiple times (e.g. multiple `api-contract-rest` docs for different APIs).

## Setup

1. Set `LITELLM_API_KEY` in your shell profile (e.g. `~/.zshrc`): `export LITELLM_API_KEY="your-key"`
2. Copy `.doc-config.yml` to your repository root
3. Fill in `project_name` (required) and other fields
4. Copy `.github/` directory to your repository
5. Copy `.claude/` directory and `.mcp.json` for local Claude Code usage (settings, agents, commands, MCP config)
6. Copy `CLAUDE.md` for project-level instructions
7. Update the `paths` filter in `doc-sync.yml` to match your `docs_dir`
8. **Secrets** — the following are available as **organization secrets** and are automatically inherited by all repos under the `Crius-Technology` org (no manual setup needed):
   - `LITELLM_API_KEY` — LLM gateway API key (used by doc-code consistency checks and doc-sync)
   - `DOCS_APP_PRIVATE_KEY` — GitHub App private key (used by doc-sync)

   If you are using this template outside the organization, set these as repository secrets manually.


## Template sync

A [Jenkins job](https://jenkins.epublishment.com/view/5.%20Varia/job/Sync%20Repo%20Template/) is available to sync the necessary files after the repository has been set up.
This will sync the .github and .claude folders to the destination repositories. Other files are currently not synced as they only need to be set up once and configured per repo.

This job need to be run manually.

To configure to which repo's it should sync, you can adjust it in the REPO_CONFIGS variable in [this file](https://github.com/Crius-Technology/jenkins-pipelines/blob/master/vars/pipelineSyncRepoTemplate.groovy)

## Claude Code Usage

With the `.claude/` directory configured, you can use Claude Code locally:

```bash
# Generate/validate all documentation
claude /generate-docs
```

This will:
1. Fetch all templates (specification + repository) from the docs-agent MCP server
2. Scan existing docs and evaluate them against templates
3. Generate missing documentation by reading your codebase
4. Fix issues in existing documents
5. Report orphan documents that don't match any template
