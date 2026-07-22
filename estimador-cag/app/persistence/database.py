"""
LAYER: persistence database
RESPONSIBILITY: Build async SQLAlchemy engine and session factory.
WHY IT EXISTS: Session 08 moves embeddings from in-memory responses to
               PostgreSQL plus pgvector persistence.
"""

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DEFAULT_DATABASE_URL = "postgresql+asyncpg://estimator:estimator@localhost:5432/estimator"
_ASYNC_DATABASE_PREFIXES = (
    "postgresql+asyncpg://",
    "postgresql+psycopg://",
    "postgresql+psycopg_async://",
)


def get_database_url() -> str:
    """Return the runtime database URL.

    Docker can provide DATABASE_URL for service-to-service networking, while local
    development defaults to localhost.
    """
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def normalize_async_database_url(database_url: str) -> str:
    """Return an explicit async SQLAlchemy URL for common deployment DSNs."""

    normalized = database_url.strip()
    if not normalized:
        raise ValueError("database_url must not be blank")
    if normalized.startswith(_ASYNC_DATABASE_PREFIXES):
        return normalized
    if normalized.startswith("postgresql://"):
        return "postgresql+asyncpg://" + normalized[len("postgresql://") :]
    if normalized.startswith("postgres://"):
        return "postgresql+asyncpg://" + normalized[len("postgres://") :]
    raise ValueError("database_url must use a supported PostgreSQL scheme")


def build_async_engine(database_url: str | None = None) -> AsyncEngine:
    """Build an async SQLAlchemy engine without opening a connection."""
    return create_async_engine(
        normalize_async_database_url(database_url or get_database_url()),
        pool_pre_ping=True,
    )


engine = build_async_engine()
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield one database session for FastAPI dependencies."""
    async with AsyncSessionLocal() as session:
        yield session
