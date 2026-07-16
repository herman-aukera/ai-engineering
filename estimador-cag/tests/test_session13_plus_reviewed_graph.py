from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.reviewed_build import build_reviewed_estimation_graph
from app.generation.graph.state import new_estimation_graph_state


class FakeRequirementExtractor:
    async def extract_requirements(self, *, transcript: str):
        assert transcript
        return [
            {"requirement_id": "req-1", "text": "Authenticate users with JWT."},
            {"requirement_id": "req-2", "text": "Persist accounts in PostgreSQL."},
        ]


class FakeComponentClassifier:
    async def classify_components(self, *, requirements):
        assert [item["requirement_id"] for item in requirements] == ["req-1", "req-2"]
        return [
            {
                "component_id": "cmp-auth",
                "name": "Authentication and account storage",
                "category": "backend",
                "requirement_ids": ["req-1", "req-2"],
            }
        ]


class FakeBudgetSearcher:
    async def search_budgets(self, *, component, k: int):
        assert component["component_id"] == "cmp-auth"
        assert k == 5
        return [
            {
                "component_id": "cmp-auth",
                "budget_id": "BUD-101",
                "reference_component_id": "REF-AUTH-1",
                "source_document_id": "DOC-10",
                "source_chunk_id": "CH-101",
                "recorded_hours": 40.0,
                "distance": 0.08,
                "score": 0.92,
                "retrieval_method": "deterministic_fake",
            },
            {
                "component_id": "cmp-auth",
                "budget_id": "BUD-202",
                "reference_component_id": "REF-AUTH-2",
                "source_document_id": "DOC-20",
                "source_chunk_id": "CH-202",
                "recorded_hours": 40.0,
                "distance": 0.1,
                "score": 0.9,
                "retrieval_method": "deterministic_fake",
            },
        ]


def _dependencies() -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor(),
        component_classifier=FakeComponentClassifier(),
        budget_searcher=FakeBudgetSearcher(),
    )


def _initial_state(*, review_mode: str):
    state = new_estimation_graph_state(
        transcript="Build a secure FastAPI onboarding platform with PostgreSQL.",
        estimation_id="11111111-1111-4111-8111-111111111111",
        graph_version="session13.plus.v1",
    )
    state["human_review_mode"] = review_mode
    state["structure_review_revision"] = 0
    state["execution_budgets"] = {
        "retry_count": 0,
        "retry_limit": 2,
        "fallback_count": 0,
        "fallback_limit": 1,
        "tool_call_count": 0,
        "tool_call_limit": 8,
        "elapsed_ms": 0,
        "latency_budget_ms": 120000,
        "estimated_cost_usd": 0.0,
        "cost_budget_usd": 1.0,
    }
    return state


@pytest.mark.asyncio
async def test_reviewed_graph_runs_three_composable_phases_without_human_gate() -> None:
    graph = build_reviewed_estimation_graph(
        _dependencies(),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "reviewed-disabled"}}

    result = await graph.ainvoke(
        _initial_state(review_mode="disabled"),
        config=config,
    )

    assert result["structure_review_status"] == "skipped"
    assert result["status"] == "validated"
    assert result["estimate"]["total_hours"] == 40.0
    assert result["critic_report"]["verdict"] == "accept"
    assert result["boss_decision"]["action"] == "accept"
    assert result["review_required"] is False

    trace_nodes = [event["node"] for event in result["trace_events"]]
    assert "structure_review" in trace_nodes
    assert "deterministic_critic" in trace_nodes
    assert "boss_policy" in trace_nodes


@pytest.mark.asyncio
async def test_required_structure_gate_pauses_and_resumes_same_thread() -> None:
    graph = build_reviewed_estimation_graph(
        _dependencies(),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "reviewed-required"}}

    interrupted = await graph.ainvoke(
        _initial_state(review_mode="required"),
        config=config,
    )

    interrupts = interrupted["__interrupt__"]
    assert len(interrupts) == 1
    payload = interrupts[0].value
    assert payload["gate"] == "structure_review"
    assert payload["revision"] == 0
    assert payload["components"][0]["component_id"] == "cmp-auth"

    resumed = await graph.ainvoke(
        Command(
            resume={
                "action": "approve",
                "expected_revision": 0,
            }
        ),
        config=config,
    )

    assert resumed["structure_review_status"] == "approved"
    assert resumed["structure_review_revision"] == 1
    assert resumed["status"] == "validated"
    assert resumed["boss_decision"]["action"] == "accept"
    assert resumed["estimate"]["total_hours"] == 40.0


@pytest.mark.asyncio
async def test_human_rejection_stops_before_retrieval_and_estimation() -> None:
    graph = build_reviewed_estimation_graph(
        _dependencies(),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "reviewed-rejected"}}

    interrupted = await graph.ainvoke(
        _initial_state(review_mode="required"),
        config=config,
    )
    assert interrupted["__interrupt__"]

    resumed = await graph.ainvoke(
        Command(
            resume={
                "action": "reject",
                "expected_revision": 0,
                "reason": "The structure omits a required approval workflow.",
            }
        ),
        config=config,
    )

    assert resumed["structure_review_status"] == "rejected"
    assert resumed["structure_route"] == "stop"
    assert resumed["status"] == "needs_review"
    assert resumed.get("budget_matches", []) == []
    assert resumed.get("component_estimates", []) == []
    assert "boss_decision" not in resumed
