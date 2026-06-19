---
name: knowledge-search
description: Search the Crius company knowledge hub (the crius-docs documentation — business docs, technical docs, ADRs, runbooks, decisions, configuration references, glossary) to answer a question with cited, fetched content. Use whenever the user asks about internal/company documentation, "where is X documented", "what does our ADR/runbook/spec say about Y", how a Crius system or process works, how two components/concepts relate, what depends on or is affected by something, or any question that should be grounded in Crius's own docs rather than general knowledge. Triggers on mentions of crius-docs, the docs hub, internal documentation, ADRs, runbooks, "our docs/spec/decision", or relational questions ("how are X and Y connected", "what relates to Z", impact analysis).
---

# Knowledge Search

Answer the user's question from the Crius knowledge hub (`crius-docs`) using **fetched, cited content** — never from memory, a snippet, or a node name alone.

The whole skill is one loop: **discover paths → fetch full files → answer & cite.** Three discovery channels feed the same fetch step — every channel's job is to hand you `file_path`s (and document ids). You then read the actual files and answer from them.

## Discovery channels

Run the channel(s) that fit the question; combine them for hard or broad questions. They are complementary, not alternatives.

### 1. Index exploration — the catalog (precise, cheapest)

`crius-docs` ships **`index.json`** at its root: a catalog of all docs. Each entry has `id, title, type, status, domain, author, source, tags, file_path, summary`.

- **Checked out locally (you are in crius-docs, or it's cloned)** → `Read` `index.json` and filter entries by `type` / `domain` / `tags` / keyword in `title`+`summary`. You get exact `file_path`s at zero search cost.
- **Remote** → `list_documents(type?, domain?, status?, tag?)` and `search_documents(query, type?, domain?, top_k?)` (doc-templates MCP) query the same index.
- **Best for:** nameable docs — "the ADR about X", "all runbooks", "the configuration reference for component Y".
- **Types and domains are data, not a frozen list** — read the values that actually appear in `index.json` (or via `list_documents`) rather than assuming a fixed set. The `type` vocabulary tracks the templates in crius-docs (`docs/methodology/templates/`) plus `reference`/`other`, and changes over time. High-volume types you'll commonly see include `adr`, `software-design`, `business-process`, `configuration-reference`, `operations-guide`, `runbook`, `persona`. **Domains** group by component, e.g. `technology/company-wide`, `technology/core-api`, `technology/crius-ai`, `technology/core-router`, `business-process/eBooks`. Filter on whatever values are present.

### 2. Semantic search — meaning (best for "how does X work")

`rag_search(query, repos=["crius_docs"], top_k?)` — similarity search over full document content. Each hit returns a chunk snippet plus `metadata.file_path` and `repo`. Use when the location/type is unknown or the question is conceptual. Exposed via the gateway alice-docs MCP server.

### 3. Graph traversal — relationships (what index & RAG can't do)

A Neo4j knowledge graph models docs and the concepts inside them as connected nodes (built by graphify over crius-docs). Use it for **relational** questions where the answer is a *set of connected things*, not a single document. **Every graph node carries a `source_file`** — feed those paths into the fetch step. Exposed via the `knowledge-graph` MCP server (`graph_mcp`).

- `graph_search(query, limit?)` — find entry nodes by keyword. **Start here**, then traverse.
- `find_related(concept, hops=1..3)` — neighbourhood / impact analysis: "what relates to / depends on / is affected by X". `hops=1` direct, `hops=2` second-degree.
- `find_path(from_concept, to_concept)` — "how are X and Y connected" — shortest relationship chain between two concepts.
- `get_entity(name)` — one node plus all its direct edges (the full local picture of a concept).
- `graph_stats()` — node/edge counts and top hub concepts; use to orient before a deep traversal.

## Procedure

1. **Pick channels by question shape.**
   - Nameable doc / type / domain / tag → **index** (1).
   - Conceptual, "how does it work", unknown location → **semantic** (2).
   - Relational — "what connects to / depends on X", "how do X and Y relate", impact analysis → **graph** (3).
   - Hard or broad → run several and merge candidates.
2. **Discover broadly.** Gather a candidate set of `file_path`s and `id`s across the channels you ran. Graph nodes → their `source_file`; RAG hits → their `metadata.file_path`; index entries → their `file_path`. **Do not answer from snippets or node names yet.**
3. **Select** the few files genuinely worth reading — not everything that matched.
4. **Fetch full content by path** (the shared step every channel feeds):
   - **Checked out locally** → `Read` the `file_path`. Fastest, no token cost.
   - **Otherwise** → `get_document(id)` if you have an index id, else `get_file(path)` with the hit's `file_path` / `source_file`.
   - **External / rendered page only** → WebFetch the GitHub `source_url` (prefer the repo URL over the Keycloak-gated docs site).
5. **Answer & cite.** Respond only from fetched content. Cite every claim with its source — `repo:path`, document id, or `source_url`. If nothing relevant was found, say so plainly instead of guessing.

## Rules

- Discovery finds **paths**; **answers come from fetched files** — never from a snippet, a graph node name, or memory.
- Graph nodes and RAG chunks are *pointers*: always resolve them to full files (step 4) before citing.
- Prefer fetching 1–3 highly relevant files in full over many shallow snippets.
- Always cite sources.
