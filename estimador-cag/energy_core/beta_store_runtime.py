"""Runtime selection for EACODE beta authority persistence."""

from __future__ import annotations

import os
from pathlib import Path

from energy_core.beta_store import SQLiteBetaDemoStore
from energy_core.postgres_beta_store import PostgresBetaDemoStore


def build_beta_demo_store(*, require_durable: bool = False):
    """Select PostgreSQL in production and SQLite only for compatibility/testing."""

    database_url = os.getenv("EACODE_DATABASE_URL", "").strip()
    if database_url:
        return PostgresBetaDemoStore(database_url)
    if require_durable:
        raise RuntimeError(
            "EACODE_DATABASE_URL is required for the production authority store."
        )
    database_path = os.getenv(
        "EACODE_DEMO_DB_PATH",
        str(Path(".eacode") / "eacode-demo.sqlite3"),
    )
    return SQLiteBetaDemoStore(database_path)
