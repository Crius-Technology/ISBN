"""Central configuration loader for documentation automation.

Loads `.doc-config.yml` from the repository root and provides accessor
functions with sensible defaults.
"""

import os
import sys
from pathlib import Path
from typing import Any

import yaml

_config: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    """Load and cache the .doc-config.yml file."""
    global _config
    if _config is not None:
        return _config

    config_path = Path(".doc-config.yml")
    if not config_path.exists():
        print("::error::Missing .doc-config.yml in repository root")
        sys.exit(1)

    with open(config_path) as f:
        _config = yaml.safe_load(f) or {}
    return _config


def get_project_name() -> str:
    """Get the project name (required)."""
    config = _load_config()
    name = config.get("project_name", "")
    if not name:
        # Fallback to GITHUB_REPOSITORY repo name
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        if "/" in repo:
            name = repo.split("/")[-1]
    if not name:
        print("::error::project_name is required in .doc-config.yml")
        sys.exit(1)
    return name


def get_docs_dir() -> str:
    """Get the documentation directory."""
    return _load_config().get("docs_dir", "docs")


def get_sync_exclude() -> list[str]:
    """Get list of file patterns to exclude from sync."""
    return _load_config().get("doc_sync", {}).get("sync_exclude", [])


def get_doc_sync_config() -> dict[str, Any]:
    """Get documentation sync configuration."""
    return _load_config().get("doc_sync", {})
