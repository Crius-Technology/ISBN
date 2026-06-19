# Generate Documentation

Generate and validate project documentation using templates from the docs-agent MCP server.

This command works without any configuration file. It uses conventions:
- Documentation directory is auto-detected (checks `.doc-config.yml`, then scans for `docs/` or `00-docs/`)
- The entire project is scanned for code context
- Project name is not needed by this command

## Output Rules

- All diagrams generated in documentation **must use Mermaid syntax**.
- Do not use ASCII diagrams or other diagram formats.
- Prefer Mermaid diagram types where appropriate:
    - `flowchart` for process/flow diagrams
    - `sequenceDiagram` for interaction diagrams
    - `classDiagram` for architecture
    - `erDiagram` for data models
- All Mermaid diagrams must be inside fenced code blocks:

## Frontmatter Contract

Before writing any frontmatter, call `mcp__doc-templates__get_metadata_schema()` to fetch the authoritative contract, and follow it for every document you create or edit:

- **Required fields:** `title`, `type`, `status`.
- **`type`** must be one of the returned `type_values` — the template's type, or `reference` for hub-native reference pages, or `other` if no template fits. Never invent a type.
- **`status`** must be one of the returned `status_values` (new docs start as `draft`).
- **`tags`** are topical/component only (e.g. `terraform`, `keycloak`) — never an audience, a phase, or the document type.
- **Never emit** any field in `retired_fields` (e.g. `audience`, `owner`, `date`). The hub strips them, but don't generate them in the first place.

## Steps

1. **Fetch all templates**
   - Call `mcp__doc-templates__list_templates()` with **no category filter** to get every available template. Do not hardcode a category list — categories are discovered dynamically from the templates directory (`docs/methodology/templates/` in crius-docs) and include e.g. `specification`, `repository`, `cross-cutting`, `ui-design`, `decision`, `business-process`, `end-user-external`, `end-user-internal`, `commercial`, `support`. New categories appear automatically.
   - Note each template's `category`; you only need it to decide *where* the generated doc goes (see step 7): `repository` → root-level file, everything else → `DOCS_DIR`.

2. **Get full template content**
   - For each template returned, call `mcp__doc-templates__get_template(template_type=<id>)` to get the full markdown content

3. **Detect documentation directory**
   - If `.doc-config.yml` exists, read `docs_dir` from it
   - Otherwise, scan for common doc directories: `docs/`, `00-docs/`
   - Use whichever directory exists; fall back to `docs/` if none found
   - Store this as `DOCS_DIR` for subsequent steps

4. **Scan existing documentation**
   - Scan `DOCS_DIR` for existing documentation files
   - Scan root-level docs (e.g. `README.md`)
   - Identify each file's `type` from its YAML frontmatter
   - Track existing `sidebar_position` values to determine the next available position

5. **Process document templates** (every non-`repository` category → `DOCS_DIR`)
   - This covers all templates whose `category` is not `repository` (specifications, cross-cutting, ui-design, decision, business-process, end-user-*, commercial, support, and any future category). Project-wide docs like the glossary are handled here too.
   - For each such template:
     - Find existing docs matching that type (via frontmatter `type` field)
     - Templates can be used multiple times (e.g. multiple `api-contract-rest` docs for different APIs)
     - If **no docs exist** for a template type and the template is applicable to this project:
       - Read the relevant source code (and existing documentation) from the project
       - Generate a complete document from the template with real content (not just scaffolding)
       - Write it to `DOCS_DIR` with proper frontmatter including `type` field
       - Include `sidebar_position` (next available integer) and `sidebar_label` (short human-readable label) in the frontmatter for Docusaurus sidebar ordering
     - If **docs exist** for a template type:
       - Read each doc and evaluate it: `mcp__doc-templates__evaluate_doc(content=<content>)`
       - Fix any issues found (missing sections, unfilled placeholders, missing frontmatter fields)
       - Ensure `sidebar_position` and `sidebar_label` are present in the frontmatter; add them if missing (use next available position, derive label from the document title)
       - Update the file in place

6. **Process repository templates** (for root-level files)
   - For each template whose `category` is `repository` (e.g. README):
     - Check if the corresponding root-level file exists
     - If missing and applicable: generate from template with real project content
     - If present: evaluate and fix issues

7. **Flag orphan documents**
   - Identify any docs in `DOCS_DIR` that don't match any known template type
   - Report these for manual review (do not delete them); a genuinely template-less doc may use `type: other` rather than being left untyped

8. **Output summary**
   - List all created documents with their paths
   - List all updated documents with before/after quality scores
   - List any flagged orphan documents
   - Show overall documentation coverage
