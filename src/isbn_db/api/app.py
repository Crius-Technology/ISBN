"""FastAPI application factory.

A synchronous :class:`psycopg_pool.ConnectionPool` is opened for the app's lifetime and shared by
all request handlers (FastAPI runs the sync endpoints in a threadpool). Connections yield ``dict``
rows so handlers map straight onto the response models.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from ..config import DB_DSN
from .routes import router

DESCRIPTION = (
    "Search and analytics over the ISBN-13 keyed `editions` corpus (~39M rows). "
    "This is the single API consumed by the Explorer UI and the LLM-gateway MCP tools."
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    pool = ConnectionPool(
        conninfo=DB_DSN,
        min_size=1,
        max_size=int(os.environ.get("ISBN_API_POOL_MAX", "10")),
        kwargs={"row_factory": dict_row},
        open=False,
    )
    pool.open(wait=True, timeout=10.0)
    app.state.pool = pool
    try:
        yield
    finally:
        pool.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ISBN Metadata API",
        version="0.1.0",
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    origins = [o.strip() for o in os.environ.get("ISBN_API_CORS_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app
