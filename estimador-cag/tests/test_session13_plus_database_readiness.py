"""Deployment database URL contracts for async SQLAlchemy and LangGraph."""

from __future__ import annotations

import pytest

from app.generation.graph.runtime import postgres_saver_conninfo
from app.persistence.database import normalize_async_database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "postgresql://user:password@db:5432/lidr",
            "postgresql+asyncpg://user:password@db:5432/lidr",
        ),
        (
            "postgres://user:password@db:5432/lidr",
            "postgresql+asyncpg://user:password@db:5432/lidr",
        ),
        (
            "postgresql+asyncpg://user:password@db:5432/lidr",
            "postgresql+asyncpg://user:password@db:5432/lidr",
        ),
        (
            "postgresql+psycopg://user:password@db:5432/lidr",
            "postgresql+psycopg://user:password@db:5432/lidr",
        ),
    ],
)
def test_normalize_async_database_url(raw: str, expected: str) -> None:
    assert normalize_async_database_url(raw) == expected


def test_normalized_sqlalchemy_url_remains_compatible_with_langgraph_saver() -> None:
    sqlalchemy_url = normalize_async_database_url(
        "postgresql://user:password@db:5432/lidr"
    )
    assert postgres_saver_conninfo(sqlalchemy_url) == (
        "postgresql://user:password@db:5432/lidr"
    )


@pytest.mark.parametrize("raw", ["", "   ", "sqlite:///tmp/app.db", "mysql://db/app"])
def test_unsupported_database_url_fails_before_engine_creation(raw: str) -> None:
    with pytest.raises(ValueError, match="database_url|PostgreSQL"):
        normalize_async_database_url(raw)
