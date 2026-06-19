# Check Compliance

Check this codebase against applicable Architectural Decision Records (ADRs) using the doc-templates MCP server.

## Steps

1. **Read project configuration**
   - Read `.doc-config.yml` to determine `project_name` and any relevant `tags`
   - If `.doc-config.yml` does not exist, infer the project name from the repository directory name

2. **Discover all ADRs**
   - Call `mcp__doc-templates__list_documents(type="adr")` to retrieve all ADRs with their metadata (id, title, tags, status, domain)

3. **Filter to relevant ADRs**
   - Keep ADRs where:
     - `tags` or `domain` overlap with the project's domain (e.g. python, fastapi, api, backend, infrastructure) — or the ADR has no tags/domain restriction (applies globally)
   - Skip ADRs with `status` of `deprecated` or `archived`

4. **Fetch full ADR content**
   - For each relevant ADR, call `mcp__doc-templates__get_document(document_id=<id>)` to retrieve the full decision text, context, and requirements

5. **Assess codebase compliance**
   - For each fetched ADR, review the codebase against its stated requirements and consequences
   - Search for evidence of compliance or non-compliance (configuration files, source code, dependency declarations, CI/CD pipelines)
   - Classify each ADR as one of:
     - **Compliant** — codebase follows the decision
     - **Non-compliant** — codebase violates or ignores the decision (include specific file references and details)
     - **Not applicable** — decision does not apply to this project's scope

6. **Output compliance report**
   - Print a summary table:

     | ADR ID | Title | Status | Notes |
     |--------|-------|--------|-------|
     | ADR-XXX-001 | ... | Compliant | ... |
     | ADR-XXX-002 | ... | Non-compliant | See `src/foo.py:42` — ... |
     | ADR-XXX-003 | ... | Not applicable | Project does not use ... |

   - After the table, list each non-compliant ADR with:
     - Full ADR title and ID
     - What the decision requires
     - What was found in the codebase
     - Specific file paths and line references
     - Suggested remediation steps
