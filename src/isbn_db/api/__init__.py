"""HTTP search API over the ``editions`` table.

A single FastAPI service is the one coupling point for every consumer of the dataset: the Explorer
UI (server-side fetch), a future MCP server in the LLM gateway (a thin httpx wrapper), and direct
callers. Run it with ``isbn-db serve``; the OpenAPI contract is served at ``/openapi.json``.
"""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
