from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from langgraph.types import Command

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.nodes.session14_plus_policy import (
    build_session14_plus_policy_bootstrap_node,
    build_session14_plus_supervisor_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.session14_plus_build import (
    SESSION14_PLUS_NODE_NAMES,
    build_session14_plus_estimation_graph,
)
from app.generation.graph.session14_plus_state import (
    new_session14_plus_estimation_graph_state,
)
from app.schemas.session14_plus_policy import ModelCapabilityRecord
from app.services.session14_plus_policy import build_capability_registry


def _capability_registry():
    verified_at = datetime(2026, 7, 1, tzinfo=UTC)
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
        registry_version="session14-plus-test-v1",
        generated_at=verified_at,
    )


def _repository_state() -> dict[str, str]:
    return {
        "branch": "gg-session-14/plus",
        "sha": "607a5fcb",
        "base_branch": "session-14/pre-work",
    }


@pytest.mark.asyncio
async def test_policy_bootstrap_authorizes_routes_and_compacts_without_transcript() -> None:
    sensitive_transcript = "CLIENT-SECRET build a small reporting API."
    state = new_session14_plus_estimation_graph_state(
        transcript=sensitive_transcript,
        estimation_id="EST-PLUS-001",
        context_detail="minimal",
    )
    node = build_session14_plus_policy_bootstrap_node(
        capability_registry=_capability_registry(),
        execution_profile="balanced",
        context_detail="minimal",
        repository_state=_repository_state(),
    )

    update = await node(state)

    assert update["plus_complexity_assessment"]["level"] == "C1"
    assert set(update["plus_authorized_capabilities"]) == {
        "complexity",
        "structure",
        "recovery",
        "reliability",
        "proposal",
    }
    assert update["plus_context_source_revision"] == 1
    serialized_context = json.dumps(update["plus_compacted_context"])
    assert sensitive_transcript not in serialized_context
    assert "transcript" not in serialized_context
    assert update["plus_compacted_context"]["repository_state"]["branch"] == (
        "gg-session-14/plus"
    )


@pytest.mark.asyncio
async def test_plus_supervisor_refreshes_context_before_routing() -> None:
    state = new_session14_plus_estimation_graph_state(
        transcript="Build a small API.",
        estimation_id="EST-PLUS-002",
    )
    bootstrap = build_session14_plus_policy_bootstrap_node(
        capability_registry=_capability_registry(),
        repository_state=_repository_state(),
    )
    state.update(await bootstrap(state))
    supervisor = build_session14_plus_supervisor_node(
        context_detail="medium",
        repository_state=_repository_state(),
    )

    command = await supervisor(state)

    assert command.goto == "requirements_extractor"
    assert command.update["plus_context_source_revision"] == 2
    assert command.update["plus_compacted_context"]["next_action"] == (
        "Execute requirements_extractor."
    )
    events = command.update["plus_context_compaction_events"]
    assert events[0]["event_id"] == "EST-PLUS-002:context:2"


@pytest.mark.asyncio
async def test_plus_graph_runs_end_to_end_without_changing_mandatory_graph() -> None:
    dependencies = GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor(
            [{"requirement_id": "REQ-1", "text": "Build reporting API."}]
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
                        "distance": 0.10,
                        "score": 0.90,
                        "retrieval_method": "test",
                    },
                    {
                        "component_id": "CMP-1",
                        "budget_id": "BUD-2",
                        "reference_component_id": "REF-2",
                        "source_document_id": "DOC-2",
                        "source_chunk_id": "CH-2",
                        "recorded_hours": 44.0,
                        "distance": 0.12,
                        "score": 0.88,
                        "retrieval_method": "test",
                    },
                ]
            }
        ),
    )

    async def unused_human_gate(_state):
        return Command(goto="finalize", update={})

    graph = build_session14_plus_estimation_graph(
        dependencies,
        capability_registry=_capability_registry(),
        human_review_gate=unused_human_gate,
        repository_state=_repository_state(),
    )
    state = new_session14_plus_estimation_graph_state(
        transcript="Build a small reporting API.",
        estimation_id="EST-PLUS-003",
    )

    result = await graph.ainvoke(state)

    assert set(SESSION14_PLUS_NODE_NAMES).issubset(graph.get_graph().nodes)
    assert result["status"] == "validated"
    assert result["current_agent"] == "finalize"
    assert result["plus_authorized_capabilities"]["proposal"] == (
        "cap:deepseek:flash"
    )
    assert result["plus_context_source_revision"] >= 6
    assert len(result["plus_context_compaction_events"]) >= 6
    assert result["plus_compacted_context"]["checkpoint_state"]["thread_id"] == (
        "estimate:EST-PLUS-003"
    )
