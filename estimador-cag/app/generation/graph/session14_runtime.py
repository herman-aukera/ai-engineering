"""PostgreSQL-backed composition for the Session 14 reviewed supervisor."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.config import settings
from app.generation.graph.adapters import build_graph_node_dependencies
from app.generation.graph.nodes.session14_human_review import (
    build_session14_human_review_gate,
)
from app.generation.graph.observability import (
    SESSION14_ROOT_SPAN_NAME,
    GraphTracer,
    get_logfire_graph_tracer,
)
from app.generation.graph.review_state import (
    new_session14_estimation_graph_state,
)
from app.generation.graph.runtime import open_postgres_checkpointer
from app.generation.graph.session14_build import (
    SESSION14_GRAPH_NAME,
    build_session14_estimation_graph,
)
from app.services.graph_estimation import GraphEstimationService

SESSION14_GRAPH_VERSION = "session14.v1"


_session14_human_review_gate = build_session14_human_review_gate(
    confidence_threshold=settings.session14_confidence_threshold,
)


@asynccontextmanager
async def open_session14_graph_estimation_service(
    database_url: str | None = None,
    *,
    tracer: GraphTracer | None = None,
) -> AsyncIterator[GraphEstimationService]:
    """Compose the Session 14 Level 2 graph for one app lifetime."""

    resolved_tracer = (
        tracer
        if tracer is not None
        else get_logfire_graph_tracer()
    )

    async with open_postgres_checkpointer(
        database_url
    ) as checkpointer:
        dependencies = build_graph_node_dependencies()
        graph = build_session14_estimation_graph(
            dependencies,
            human_review_gate=_session14_human_review_gate,
            checkpointer=checkpointer,
            tracer=resolved_tracer,
            confidence_threshold=(
                settings.session14_confidence_threshold
            ),
        )

        yield GraphEstimationService(
            graph=graph,
            tracer=resolved_tracer,
            root_span_name=SESSION14_ROOT_SPAN_NAME,
            graph_version=SESSION14_GRAPH_VERSION,
            graph_name=SESSION14_GRAPH_NAME,
            state_factory=new_session14_estimation_graph_state,
        )
