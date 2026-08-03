"""PostgreSQL-backed composition root for the unified Plus graph."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.config import settings
from app.generation.graph.adapters import build_graph_node_dependencies
from app.generation.graph.nodes.session14_human_review import (
    build_session14_human_review_gate,
)
from app.generation.graph.observability import (
    UNIFIED_ROOT_SPAN_NAME,
    GraphTracer,
    get_logfire_graph_tracer,
)
from app.generation.graph.runtime import open_postgres_checkpointer
from app.generation.graph.unified_build import (
    UNIFIED_GRAPH_NAME,
    build_unified_estimation_graph,
)
from app.generation.graph.unified_state import (
    new_unified_estimation_graph_state,
)
from app.services.graph_estimation import GraphEstimationService
from app.services.selective_recovery import SelectiveRecoveryService
from app.services.stage_routing_runtime import (
    StageRoutedAgentModel,
    StageRoutedLiteLLMProvider,
)
from app.services.unified_capability_registry import (
    build_unified_capability_registry,
    load_benchmark_snapshot,
)
from app.services.v3_semantic_classifier import LiveSemanticClassifier

UNIFIED_GRAPH_VERSION = "session13_14_plus.unified.v1"


@asynccontextmanager
async def open_unified_graph_estimation_service(
    database_url: str | None = None,
    *,
    tracer: GraphTracer | None = None,
) -> AsyncIterator[GraphEstimationService]:
    """Compose the canonical graph from benchmark and server-owned policy."""

    resolved_tracer = tracer if tracer is not None else get_logfire_graph_tracer()
    snapshot = load_benchmark_snapshot(
        settings.provider_benchmark_snapshot_path or None
    )
    capability_registry = build_unified_capability_registry(snapshot)
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
    human_gate = build_session14_human_review_gate(
        confidence_threshold=settings.session14_confidence_threshold,
    )
    repository_state = {
        "branch": os.getenv(
            "GITHUB_REF_NAME",
            "gg-session-14/plus-consolidated",
        ),
        "sha": os.getenv("GITHUB_SHA", "runtime-unknown"),
        "base_branch": "gg-session-14/plus",
        "session13_plus_source": (
            "f87605cb8a8ee5ff2606c51e5490b6beb2ca7f7a"
        ),
        "session14_plus_source": (
            "34011bcd9442130e09ab776d9072c0d53a2d93c2"
        ),
    }

    async with open_postgres_checkpointer(database_url) as checkpointer:
        graph = build_unified_estimation_graph(
            dependencies,
            capability_registry=capability_registry,
            human_review_gate=human_gate,
            repository_state=repository_state,
            checkpointer=checkpointer,
            recovery_application=recovery_application,
            tracer=resolved_tracer,
            confidence_threshold=settings.session14_confidence_threshold,
            retrieval_mode=settings.graph_retrieval_mode,
            retrieval_max_concurrency=(
                settings.graph_retrieval_max_concurrency
            ),
            semantic_classifier=live_classifier,
        )
        yield GraphEstimationService(
            graph=graph,
            tracer=resolved_tracer,
            root_span_name=UNIFIED_ROOT_SPAN_NAME,
            graph_version=UNIFIED_GRAPH_VERSION,
            graph_name=UNIFIED_GRAPH_NAME,
            state_factory=new_unified_estimation_graph_state,
        )
