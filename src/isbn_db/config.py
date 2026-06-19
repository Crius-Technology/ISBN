"""Runtime configuration (database connection, data directory)."""

from __future__ import annotations

import os
from pathlib import Path

# Dedicated Postgres for this project (isolated from retro-tool's DB on 5432).
DB_DSN = os.environ.get(
    "ISBN_DB_DSN",
    "postgresql://isbn:isbn@localhost:5433/isbn",
)

# Where downloaded dumps live. Git-ignored; can be large.
DATA_DIR = Path(os.environ.get("ISBN_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
