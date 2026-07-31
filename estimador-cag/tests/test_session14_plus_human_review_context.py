from __future__ import annotations

import pytest
from langgraph.types import Command

from app.generation.graph.nodes.session14_plus_human_review import (
    build_context_aware_session14_plus_human_gate,
)
from app.generation.graph.session14_plus_state import (
    new_session14_plus_estimation_graph_state,
)


@pytest.mark.asyncio
async def test_context_aware_human_gate_refreshes_context_after_resume() -> None:
    async def approved_gate(_state):
        return Command(
            goto="finalize",
            update={
                "human_review_status": "approved",
                "human_review_revision": 2,
                "human_review_actions": [
                    {
                        "action_id": "action-1",
                        "idempotency_key": "approval-001",
                        "action": "approve",
                        "actor": "reviewer",
                        "reason": None,
                        "revision": 2,
                        "adjustments": [],
                    }
                ],
            },
        )

    state = new_session14_plus_estimation_graph_state(
        transcript="Build an auditable API.",
        estimation_id="EST-PLUS-HITL",
    )
    state.update(
        plus_context_source_revision=5,
        human_review_status="awaiting_human_review",
        human_review_revision=1,
        plus_routing_plan={
            "routes_by_stage": {
                "proposal": {
                    "provider": "deepseek",
                    "model": "deepseek-v4-flash",
                    "route_id": "route:test",
                    "mode": "instant",
                    "effort": "none",
                }
            }
        },
    )
    gate = build_context_aware_session14_plus_human_gate(
        approved_gate,
        default_context_detail="medium",
        repository_state={
            "branch": "gg-session-14/plus",
            "sha": "test-sha",
        },
    )

    command = await gate(state)

    assert command.goto == "finalize"
    assert command.update["plus_context_source_revision"] == 6
    assert command.update["plus_compacted_context"]["validation_state"][
        "human_review_status"
    ] == "approved"
    assert "human:approve:revision:2" in command.update[
        "plus_compacted_context"
    ]["accepted_decisions"]
    assert command.update["plus_context_compaction_events"][0][
        "event_id"
    ] == "EST-PLUS-HITL:context:6"
