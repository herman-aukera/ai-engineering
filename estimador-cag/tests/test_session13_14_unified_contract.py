from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.nodes.unified_supervisor import (
    build_unified_supervisor_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.unified_build import (
    UNIFIED_NODE_NAMES,
    build_unified_estimation_graph,
)
from app.generation.graph.unified_state import (
    UnifiedRouteEvent,
    merge_unified_route_events,
    new_unified_estimation_graph_state,
)
from app.schemas.session14_plus_policy import ModelCapabilityRecord
from app.services.session14_plus_policy import build_capability_registry


def _capability_registry():
    verified_at = datetime(2026, 8, 3, tzinfo=UTC)
    return build_capability_registry(
        [
            ModelCapabilityRecord(
                record_id="cap:deepseek:flash",
                provider="deepseek",
                provider_model_id="deepseek-v4-flash",
                display_name="DeepSeek V4 Flash",
                capability_tier="fast",
                context_window_tokens=1_000_000,
                max_output_tokens=20_000,
                modalities=["text"],
                supports_tools=True,
                supports_structured_output=True,
                reasoning_efforts=["none", "high"],
                speed_class="fast",
                cost_metadata_version="test-v1",
                lifecycle="contract_verified",
                verified_at=verified_at,
                calibration_status="baseline",
                enabled=True,
            ),
            ModelCapabilityRecord(
                record_id="cap:python:recovery",
                provider="python",
                provider_model_id="deterministic-recovery",
                display_name="Deterministic recovery",
                capability_tier="deterministic",
                context_window_tokens=1,
                max_output_tokens=0,
                modalities=["text"],
                supports_tools=False,
                supports_structured_output=True,
                reasoning_efforts=["none"],
                speed_class="deterministic",
                cost_metadata_version="test-v1",
                lifecycle="contract_verified",
                verified_at=verified_at,
                calibration_status="baseline",
                enabled=True,
            ),
        ],
        registry_version="unified-test-v1",
        generated_at=verified_at,
    )


def _state():
    return new_unified_estimation_graph_state(
        transcript="Build an auditable reporting API.",
        estimation_id="EST-UNIFIED-001",
    )


def test_unified_route_replay_is_idempotent_and_conflicts_fail_closed() -> None:
    event = UnifiedRouteEvent(
        event_id="EST-UNIFIED-001:route:1",
        sequence=1,
        destination="structure_phase",
        reason_code="structure_not_completed",
        summary="Run structure phase.",
    )

    assert merge_unified_route_events([event], [event]) == [event]

    conflicting = UnifiedRouteEvent(
        **{**event, "destination": "estimation_phase"}
    )
    with pytest.raises(ValueError, match="conflicting unified route"):
        merge_unified_route_events([event], [conflicting])


@pytest.mark.asyncio
async def test_unified_supervisor_preserves_single_authority_sequence() -> None:
    state = _state()
    supervisor = build_unified_supervisor_node()

    command = await supervisor(state)
    assert command.goto == "structure_phase"
    assert command.update["routing_steps"] == 1

    state.update(command.update)
    state["unified_structure_completed"] = True
    command = await supervisor(state)
    assert command.goto == "estimation_phase"
    assert command.update["routing_steps"] == 2

    state.update(command.update)
    state["unified_estimation_completed"] = True
    command = await supervisor(state)
    assert command.goto == "candidate_competition"
    assert command.update["routing_steps"] == 3

    state.update(command.update)
    state["plus_competition_completed"] = True
    command = await supervisor(state)
    assert command.goto == "reliability_analyst"
    assert command.update["routing_steps"] == 4

    state.update(command.update)
    state["unified_reliability_completed"] = True
    command = await supervisor(state)
    assert command.goto == "review_policy_phase"

    state.update(command.update)
    state["unified_review_policy_completed"] = True
    command = await supervisor(state)
    assert command.goto == "boss_action"

    state.update(command.update)
    state["unified_boss_action_completed"] = True
    state["boss_route"] = "final_review"
    command = await supervisor(state)
    assert command.goto == "coherence_validator"

    state.update(command.update)
    state["unified_coherence_completed"] = True
    state["status"] = "validated"
    state["review_required"] = False
    state["validation"] = {
        "is_coherent": True,
        "status": "validated",
        "review_required": False,
    }
    command = await supervisor(state)
    assert command.goto == "proposal"

    state.update(command.update)
    state["unified_proposal_completed"] = True
    command = await supervisor(state)
    assert command.goto == "finalize"
    assert command.update["routing_steps"] == len(
        state["unified_route_events"]
    ) + 1


@pytest.mark.asyncio
async def test_recovery_budget_exhaustion_forces_human_authority() -> None:
    state = _state()
    state.update(
        unified_structure_completed=True,
        unified_estimation_completed=True,
        plus_competition_completed=True,
        unified_reliability_completed=True,
        unified_review_policy_completed=True,
        unified_boss_action_completed=True,
        boss_route="recover",
        unified_recovery_cycles=2,
        unified_max_recovery_cycles=2,
        unified_coherence_completed=False,
        status="validated",
        review_required=False,
    )

    command = await build_unified_supervisor_node()(state)

    assert command.goto == "coherence_validator"
    assert command.update["review_required"] is True
    assert command.update["status"] == "needs_review"
    assert command.update["routing_steps"] == 1


def test_unified_graph_compiles_with_all_canonical_nodes() -> None:
    dependencies = GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor([]),
        component_classifier=FakeComponentClassifier([]),
        budget_searcher=FakeBudgetSearcher({}),
    )

    async def human_gate(_state):
        raise AssertionError("compile-only test must not execute the human gate")

    graph = build_unified_estimation_graph(
        dependencies,
        capability_registry=_capability_registry(),
        human_review_gate=human_gate,
        repository_state={
            "branch": "gg-session-14/plus-consolidated",
            "sha": "test-sha",
            "base_branch": "gg-session-14/plus",
        },
        structure_review_mode="disabled",
        retrieval_mode="sequential",
    )

    assert set(UNIFIED_NODE_NAMES).issubset(graph.get_graph().nodes)
    assert graph.name == "session13_14_plus_unified_graph"
