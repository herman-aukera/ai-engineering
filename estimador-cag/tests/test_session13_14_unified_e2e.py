from __future__ import annotations

import pytest
from langgraph.types import Command

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.unified_build import build_unified_estimation_graph
from app.generation.graph.unified_state import (
    new_unified_estimation_graph_state,
)
from app.services.unified_capability_registry import (
    build_unified_capability_registry,
    load_benchmark_snapshot,
)


@pytest.mark.asyncio
async def test_unified_graph_executes_every_canonical_policy_layer() -> None:
    dependencies = GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor(
            [
                {
                    "requirement_id": "REQ-1",
                    "text": "Build an auditable reporting API.",
                }
            ]
        ),
        component_classifier=FakeComponentClassifier(
            [
                {
                    "component_id": "CMP-1",
                    "name": "Reporting API",
                    "category": "backend",
                    "requirement_ids": ["REQ-1"],
                }
            ]
        ),
        budget_searcher=FakeBudgetSearcher(
            {
                "CMP-1": [
                    {
                        "component_id": "CMP-1",
                        "budget_id": "BUD-1",
                        "reference_component_id": "REF-1",
                        "source_document_id": "DOC-1",
                        "source_chunk_id": "CH-1",
                        "recorded_hours": 40.0,
                        "distance": 0.05,
                        "score": 0.95,
                        "retrieval_method": "unified-e2e",
                    },
                    {
                        "component_id": "CMP-1",
                        "budget_id": "BUD-2",
                        "reference_component_id": "REF-2",
                        "source_document_id": "DOC-2",
                        "source_chunk_id": "CH-2",
                        "recorded_hours": 42.0,
                        "distance": 0.07,
                        "score": 0.93,
                        "retrieval_method": "unified-e2e",
                    },
                    {
                        "component_id": "CMP-1",
                        "budget_id": "BUD-3",
                        "reference_component_id": "REF-3",
                        "source_document_id": "DOC-3",
                        "source_chunk_id": "CH-3",
                        "recorded_hours": 41.0,
                        "distance": 0.06,
                        "score": 0.94,
                        "retrieval_method": "unified-e2e",
                    },
                ]
            }
        ),
    )
    gate_calls: list[str] = []

    async def authorized_human_gate(state):
        gate_calls.append(str(state.get("status")))
        return Command(
            goto="finalize",
            update={
                "status": "validated",
                "review_required": False,
                "human_review_status": "approved",
                "human_review_revision": 2,
                "human_review_actions": [
                    {
                        "action_id": "e2e-approval-action",
                        "idempotency_key": "e2e-approval-001",
                        "action": "approve",
                        "actor": "deterministic-e2e-reviewer",
                        "reason": (
                            "Authorize the synthesized candidate after the "
                            "independent median validator requested review."
                        ),
                        "revision": 2,
                        "adjustments": [],
                    }
                ],
            },
        )

    graph = build_unified_estimation_graph(
        dependencies,
        capability_registry=build_unified_capability_registry(
            load_benchmark_snapshot()
        ),
        human_review_gate=authorized_human_gate,
        repository_state={
            "branch": "gg-session-14/plus-consolidated",
            "sha": "e2e-test",
            "base_branch": "gg-session-14/plus",
        },
        structure_review_mode="disabled",
        retrieval_mode="sequential",
    )
    state = new_unified_estimation_graph_state(
        transcript="Build an auditable reporting API with stable requirements.",
        estimation_id="EST-UNIFIED-E2E",
    )

    result = await graph.ainvoke(state)

    assert gate_calls == ["needs_review"]
    assert result["unified_phase"] == "finalized"
    assert result["status"] == "validated"
    assert result["review_required"] is False
    assert result["human_review_status"] == "approved"
    assert result["human_review_revision"] == 2
    assert result["unified_structure_completed"] is True
    assert result["unified_estimation_completed"] is True
    assert result["plus_competition_completed"] is True
    assert len(result["plus_competition_candidates"]) == 4
    assert result["plus_competition_assessment"]["disposition"] == (
        "accept_synthesized"
    )
    assert result["unified_reliability_completed"] is True
    assert result["unified_review_policy_completed"] is True
    assert result["unified_boss_action_completed"] is True
    assert result["unified_coherence_completed"] is True
    assert result["unified_proposal_completed"] is True
    assert result["proposal"]
    assert result["critic_report"]
    assert result["boss_decision"]
    assert result["plus_competition_assessment"]["energy_snapshot"]
    assert len(result["plus_authorized_capabilities"]) >= 5

    destinations = [
        event["destination"]
        for event in result["unified_route_events"]
    ]
    assert destinations == [
        "structure_phase",
        "estimation_phase",
        "candidate_competition",
        "reliability_analyst",
        "review_policy_phase",
        "boss_action",
        "coherence_validator",
        "human_review_gate",
        "proposal",
        "finalize",
    ]
