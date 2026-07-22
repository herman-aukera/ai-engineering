"""PostgreSQL-backed composition for the Session 14 supervisor graph."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from langgraph.types import Command

from app.generation.graph.adapters import build_graph_node_dependencies
from app.generation.graph.observability import (
    GraphTracer,
    get_logfire_graph_tracer,
)
from app.generation.graph.review_state import (
    Session14EstimationGraphState,
    new_session14_estimation_graph_state,
)
from app.generation.graph.runtime import open_postgres_checkpointer
from app.generation.graph.session14_build import (
    SESSION14_GRAPH_NAME,
    build_session14_estimation_graph,
)
from app.services.graph_estimation import GraphEstimationService

SESSION14_GRAPH_VERSION = "session14.v1"


async def _level1_human_review_gate(
    state: Session14EstimationGraphState,
) -> Command[Literal["finalize"]]:
    """Preserve the pre-HITL needs-review result during Level 1 rollout."""

    return Command(
        goto="finalize",
        update=Session14EstimationGraphState(
            status="needs_review",
            review_required=True,
            trace_events=[
                {
                    "event_type": "session14_human_review_deferred",
                    "node": "human_review_gate",
                    "summary": (
                        "Human review is required; persistent pause and "
                        "resume are introduced in the next mandatory slice."
                    ),
                    "evidence_refs": [],
                    "state_delta_keys": [
                        "status",
                        "review_required",
                        "trace_events",
                    ],
                }
            ],
        ),
    )


@asynccontextmanager
async def open_session14_graph_estimation_service(
    database_url: str | None = None,
    *,
    tracer: GraphTracer | None = None,
) -> AsyncIterator[GraphEstimationService]:
    """Compose the Session 14 Level 1 graph for one app lifetime."""

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
            human_review_gate=_level1_human_review_gate,
            checkpointer=checkpointer,
        )

        yield GraphEstimationService(
            graph=graph,
            tracer=resolved_tracer,
            graph_version=SESSION14_GRAPH_VERSION,
            graph_name=SESSION14_GRAPH_NAME,
            state_factory=new_session14_estimation_graph_state,
        )
