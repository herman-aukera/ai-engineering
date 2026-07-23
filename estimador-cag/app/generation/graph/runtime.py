"""PostgreSQL-backed runtime composition for the estimation graph."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.generation.graph.adapters import (
    build_graph_node_dependencies,
)
from app.generation.graph.build import build_estimation_graph
from app.generation.graph.observability import (
    GraphTracer,
    get_logfire_graph_tracer,
)
from app.persistence.database import get_database_url
from app.services.graph_estimation import (
    GraphEstimationService,
)

_SUPPORTED_SQLALCHEMY_PREFIXES = (
    "postgresql+asyncpg://",
    "postgresql+psycopg://",
    "postgresql+psycopg_async://",
)


def postgres_saver_conninfo(
    database_url: str | None = None,
) -> str:
    """Return the plain PostgreSQL DSN required by psycopg."""

    raw_url = (
        database_url
        if database_url is not None
        else get_database_url()
    )
    normalized = raw_url.strip()

    if not normalized:
        raise ValueError("database_url must not be blank")

    for prefix in _SUPPORTED_SQLALCHEMY_PREFIXES:
        if normalized.startswith(prefix):
            return (
                "postgresql://"
                + normalized[len(prefix) :]
            )

    if normalized.startswith("postgres://"):
        return (
            "postgresql://"
            + normalized[len("postgres://") :]
        )

    if normalized.startswith("postgresql://"):
        return normalized

    raise ValueError(
        "database_url must use a PostgreSQL scheme"
    )


@asynccontextmanager
async def open_postgres_checkpointer(
    database_url: str | None = None,
) -> AsyncIterator[AsyncPostgresSaver]:
    """Open, initialize, and cleanly close one checkpointer."""

    conninfo = postgres_saver_conninfo(database_url)

    async with AsyncPostgresSaver.from_conn_string(
        conninfo
    ) as checkpointer:
        await checkpointer.setup()
        yield checkpointer


@asynccontextmanager
async def open_graph_estimation_service(
    database_url: str | None = None,
    *,
    tracer: GraphTracer | None = None,
) -> AsyncIterator[GraphEstimationService]:
    """Compose the production graph for one application lifetime."""

    resolved_tracer = (
        tracer
        if tracer is not None
        else get_logfire_graph_tracer()
    )

    async with open_postgres_checkpointer(
        database_url
    ) as checkpointer:
        dependencies = build_graph_node_dependencies()
        graph = build_estimation_graph(
            dependencies,
            checkpointer=checkpointer,
            tracer=resolved_tracer,
        )

        yield GraphEstimationService(
            graph=graph,
            tracer=resolved_tracer,
        )
