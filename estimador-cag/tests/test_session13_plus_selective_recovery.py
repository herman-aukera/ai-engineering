from __future__ import annotations

from collections.abc import Sequence

import pytest

from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.reviewed_build import build_reviewed_estimation_graph
from app.generation.graph.state import new_estimation_graph_state
from app.schemas.agent_runtime import AgentModelTurn, AgentToolCall
from app.services.selective_recovery import SelectiveRecoveryService


class ScriptedRecoveryModel:
    def __init__(self, turns: Sequence[AgentModelTurn]) -> None:
        self.turns = list(turns)

    async def complete_turn(self, *, messages, tools) -> AgentModelTurn:
        if not self.turns:
            raise RuntimeError("scripted recovery model exhausted")
        return self.turns.pop(0)


class StagedBudgetSearcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    async def search_budgets(self, *, component, k: int):
        self.calls.append((component["name"], k))
        if k == 5:
            return []
        return [
            {
                "component_id": component["component_id"],
                "budget_id": "BUD-REC-1",
                "reference_component_id": "REF-1",
                "source_document_id": "DOC-1",
                "source_chunk_id": "CH-1",
                "recorded_hours": 36.0,
                "distance": 0.1,
                "score": 0.91,
                "retrieval_method": "recovery_fake",
            },
            {
                "component_id": component["component_id"],
                "budget_id": "BUD-REC-2",
                "reference_component_id": "REF-2",
                "source_document_id": "DOC-2",
                "source_chunk_id": "CH-2",
                "recorded_hours": 44.0,
                "distance": 0.12,
                "score": 0.89,
                "retrieval_method": "recovery_fake",
            },
        ]


class FakeRequirementExtractor:
    async def extract_requirements(self, *, transcript: str):
        return [{"requirement_id": "req-1", "text": "Implement JWT authentication."}]


class FakeComponentClassifier:
    async def classify_components(self, *, requirements):
        return [
            {
                "component_id": "cmp-auth",
                "name": "Authentication",
                "category": "backend",
                "requirement_ids": ["req-1"],
            }
        ]


def _turn(
    *,
    content: str | None = None,
    call_id: str | None = None,
    name: str | None = None,
    arguments: dict | None = None,
) -> AgentModelTurn:
    calls = []
    if call_id and name:
        calls.append(
            AgentToolCall(
                call_id=call_id,
                name=name,
                arguments=arguments or {},
            )
        )
    return AgentModelTurn(
        content=content,
        tool_calls=calls,
        provider="fake",
        model="fake-recovery-v1",
        input_tokens=5,
        output_tokens=3,
        cost_usd=0.0,
    )


def _successful_model() -> ScriptedRecoveryModel:
    return ScriptedRecoveryModel(
        [
            _turn(
                call_id="search-1",
                name="search_recovery_evidence",
                arguments={
                    "component_id": "cmp-auth",
                    "query": "JWT identity authentication backend",
                },
            ),
            _turn(
                call_id="select-1",
                name="select_recovery_evidence",
                arguments={
                    "component_id": "cmp-auth",
                    "search_id": "cmp-auth:search:1",
                },
            ),
            _turn(
                call_id="validate-1",
                name="validate_recovery",
                arguments={"component_ids": ["cmp-auth"]},
            ),
            _turn(content="Recovery evidence selected and validated."),
        ]
    )


def _dependencies(searcher: StagedBudgetSearcher) -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor(),
        component_classifier=FakeComponentClassifier(),
        budget_searcher=searcher,
    )


def _initial_state():
    state = new_estimation_graph_state(
        transcript="Build a secure FastAPI service with JWT authentication.",
        estimation_id="11111111-1111-4111-8111-111111111111",
        graph_version="session13.plus.v1",
    )
    state["human_review_mode"] = "disabled"
    state["structure_review_revision"] = 0
    state["execution_budgets"] = {}
    return state


@pytest.mark.asyncio
async def test_selective_recovery_accepts_only_server_owned_search_result() -> None:
    searcher = StagedBudgetSearcher()
    service = SelectiveRecoveryService(
        model_port=_successful_model(),
        budget_searcher=searcher,
    )
    component = {
        "component_id": "cmp-auth",
        "name": "Authentication",
        "category": "backend",
        "requirement_ids": ["req-1"],
    }

    result = await service.recover(
        components=[component],
        existing_matches=[],
    )

    assert result.recovered_component_ids == ["cmp-auth"]
    assert result.unresolved_component_ids == []
    assert [match["recorded_hours"] for match in result.recovered_matches] == [36.0, 44.0]
    assert result.runtime.status == "completed"
    select_observation = next(
        observation
        for observation in result.runtime.observations
        if observation.tool_name == "select_recovery_evidence"
    )
    assert select_observation.output["deterministic_median_hours"] == 40.0
    assert searcher.calls == [("JWT identity authentication backend", 8)]


@pytest.mark.asyncio
async def test_reviewed_graph_recalculates_after_successful_recovery() -> None:
    searcher = StagedBudgetSearcher()
    recovery = SelectiveRecoveryService(
        model_port=_successful_model(),
        budget_searcher=searcher,
    )
    graph = build_reviewed_estimation_graph(
        _dependencies(searcher),
        recovery_application=recovery,
    )

    result = await graph.ainvoke(_initial_state())

    assert result["recovery_status"] == "completed"
    assert result["recovery_recovered_component_ids"] == ["cmp-auth"]
    assert result["component_estimates"][0]["hours"] == 40.0
    assert result["component_estimates"][0]["grounding_status"] == "grounded"
    assert result["estimate"]["total_hours"] == 40.0
    assert result["critic_report"]["verdict"] == "accept"
    assert result["boss_decision"]["action"] == "accept"
    assert result["review_required"] is False
    assert [call[1] for call in searcher.calls] == [5, 8]


@pytest.mark.asyncio
async def test_exhausted_recovery_routes_to_human_review() -> None:
    searcher = StagedBudgetSearcher()
    recovery = SelectiveRecoveryService(
        model_port=ScriptedRecoveryModel(
            [_turn(content="No suitable historical analog was found.")]
        ),
        budget_searcher=searcher,
    )
    graph = build_reviewed_estimation_graph(
        _dependencies(searcher),
        recovery_application=recovery,
    )

    result = await graph.ainvoke(_initial_state())

    assert result["recovery_status"] == "failed"
    assert result["recovery_unresolved_component_ids"] == ["cmp-auth"]
    assert result["component_estimates"][0]["grounding_status"] == "no_data"
    assert result["critic_report"]["verdict"] == "human_required"
    assert result["boss_decision"]["action"] == "human_review"
    assert result["status"] == "needs_review"
    assert result["review_required"] is True
