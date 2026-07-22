"""PostgreSQL-backed composition for the Session 13 Plus reviewed graph."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.config import settings
from app.generation.graph.adapters import build_graph_node_dependencies
from app.generation.graph.observability import GraphTracer, get_logfire_graph_tracer
from app.generation.graph.reviewed_build import build_reviewed_estimation_graph
from app.generation.graph.runtime import open_postgres_checkpointer
from app.services.reviewed_graph_estimation import ReviewedGraphEstimationService
from app.services.selective_recovery import SelectiveRecoveryService
from app.services.stage_routing_runtime import (
    StageRoutedAgentModel,
    StageRoutedLiteLLMProvider,
)
from app.services.v3_semantic_classifier import LiveSemanticClassifier


@asynccontextmanager
async def open_reviewed_graph_estimation_service(
    database_url: str | None = None,
    *,
    tracer: GraphTracer | None = None,
) -> AsyncIterator[ReviewedGraphEstimationService]:
    """Compose one reviewed graph with a shared stage-routed provider boundary."""

    resolved_tracer = tracer if tracer is not None else get_logfire_graph_tracer()
    routed_provider = StageRoutedLiteLLMProvider()
    dependencies = build_graph_node_dependencies(
        provider=routed_provider,
        tier=settings.llm_tier,
    )
    recovery_application = SelectiveRecoveryService(
        model_port=StageRoutedAgentModel(
            provider=routed_provider,
            tier=settings.llm_tier,
        ),
        budget_searcher=dependencies.budget_searcher,
    )
    live_classifier = LiveSemanticClassifier(
        routed_provider,
        tier=settings.llm_tier,
    )
    async with open_postgres_checkpointer(database_url) as checkpointer:
        graph = build_reviewed_estimation_graph(
            dependencies,
            checkpointer=checkpointer,
            recovery_application=recovery_application,
            tracer=resolved_tracer,
            retrieval_mode=settings.graph_retrieval_mode,
            retrieval_max_concurrency=settings.graph_retrieval_max_concurrency,
            semantic_classifier=live_classifier,
        )
        yield ReviewedGraphEstimationService(graph=graph)
