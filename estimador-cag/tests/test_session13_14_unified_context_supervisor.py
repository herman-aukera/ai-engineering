from __future__ import annotations

import pytest

from app.generation.graph.nodes.unified_context_supervisor import (
    build_context_aware_unified_supervisor_node,
)
from app.generation.graph.nodes.unified_policy import (
    build_unified_policy_bootstrap_node,
)
from app.generation.graph.unified_state import (
    new_unified_estimation_graph_state,
)
from app.services.unified_capability_registry import (
    build_unified_capability_registry,
    load_benchmark_snapshot,
)


@pytest.mark.asyncio
async def test_every_unified_route_refreshes_sanitized_context() -> None:
    repository_state = {
        "branch": "gg-session-14/plus-consolidated",
        "sha": "context-test",
        "base_branch": "gg-session-14/plus",
    }
    state = new_unified_estimation_graph_state(
        transcript="PRIVATE transcript must not enter compact context.",
        estimation_id="EST-UNIFIED-CONTEXT",
        context_detail="medium",
    )
    bootstrap = build_unified_policy_bootstrap_node(
        capability_registry=build_unified_capability_registry(
            load_benchmark_snapshot()
        ),
        execution_profile="balanced",
        context_detail="medium",
        repository_state=repository_state,
    )
    state.update(await bootstrap(state))
    first_fingerprint = state["plus_compacted_context"]["fingerprint"]

    supervisor = build_context_aware_unified_supervisor_node(
        context_detail="medium",
        repository_state=repository_state,
    )
    command = await supervisor(state)

    assert command.goto == "structure_phase"
    assert command.update["plus_context_source_revision"] == 2
    context = command.update["plus_compacted_context"]
    assert context["fingerprint"] != first_fingerprint
    assert "PRIVATE transcript" not in str(context)
    assert (
        "unified-route:structure_not_completed->structure_phase"
        in context["accepted_decisions"]
    )
    event = command.update["plus_context_compaction_events"][0]
    assert event["event_id"] == "EST-UNIFIED-CONTEXT:context:2"
    assert event["fingerprint"] == context["fingerprint"]
