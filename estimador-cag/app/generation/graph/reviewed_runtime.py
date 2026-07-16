"""PostgreSQL-backed composition for the Session 13 Plus reviewed graph."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.config import settings
from app.generation.graph.adapters import build_graph_node_dependencies
from app.generation.graph.observability import GraphTracer, get_logfire_graph_tracer
from app.generation.graph.reviewed_build import build_reviewed_estimation_graph
from app.generation.graph.runtime import open_postgres_checkpointer
from app.services.litellm_agent_model import LiteLLMAgentModel
from app.services.reviewed_graph_estimation import ReviewedGraphEstimationService
from app.services.selective_recovery import SelectiveRecoveryService


@asynccontextmanager
async def open_reviewed_graph_estimation_service(
    database_url: str | None = None,
    *,
    tracer: GraphTracer | None = None,
) -> AsyncIterator[ReviewedGraphEstimationService]:
    """Compose the reviewed graph for one application lifetime."""

    resolved_tracer = tracer if tracer is not None else get_logfire_graph_tracer()
    dependencies = build_graph_node_dependencies()
    recovery_application = SelectiveRecoveryService(
        model_port=LiteLLMAgentModel(tier=settings.llm_tier),
        budget_searcher=dependencies.budget_searcher,
    )
    async with open_postgres_checkpointer(database_url) as checkpointer:
        graph = build_reviewed_estimation_graph(
            dependencies,
            checkpointer=checkpointer,
            recovery_application=recovery_application,
            tracer=resolved_tracer,
        )
        yield ReviewedGraphEstimationService(graph=graph)
