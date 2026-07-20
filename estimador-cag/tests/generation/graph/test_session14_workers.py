from __future__ import annotations

from copy import deepcopy

import pytest

import app.generation.graph.nodes.session14_workers as session14_workers
from app.generation.graph.review_state import (
    Session14EstimationGraphState,
)


def _state_with_components() -> Session14EstimationGraphState:
    return {
        "estimation_id": "estimate-14",
        "transcript": "CLIENT-SECRET: confidential acquisition",
        "components": [
            {
                "component_id": "component-1",
                "name": "Authentication",
                "category": "backend",
                "requirement_ids": ["requirement-1"],
            }
        ],
        "budget_matches": [],
        "routing_steps": 2,
    }


@pytest.mark.asyncio
async def test_budget_searcher_marks_completed_empty_search_without_leaking_state() -> None:
    received_states: list[Session14EstimationGraphState] = []

    async def search_budgets(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        received_states.append(deepcopy(state))
        return {"budget_matches": []}

    state = _state_with_components()
    before = deepcopy(state)
    agent = session14_workers.build_budget_searcher_agent(
        search_budgets
    )

    update = await agent(state)

    assert received_states == [
        {
            "components": before["components"],
            "budget_matches": [],
            "execution_metadata": {},
        }
    ]
    assert "transcript" not in received_states[0]
    assert state == before
    assert update["budget_matches"] == []
    assert update["budget_search_completed"] is True
    assert "transcript" not in update

    assert update["agent_contributions"] == [
        {
            "contribution_id": "estimate-14:budget_searcher:2",
            "agent_id": "budget_searcher",
            "sequence": 2,
            "summary": "Budget search completed with 0 matches.",
            "state_delta_keys": [
                "agent_contributions",
                "budget_matches",
                "budget_search_completed",
            ],
        }
    ]
    assert "CLIENT-SECRET" not in str(update["agent_contributions"])


@pytest.mark.asyncio
async def test_budget_searcher_rejects_missing_components_before_tool_call() -> None:
    call_count = 0

    async def search_budgets(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        nonlocal call_count
        call_count += 1
        return {"budget_matches": []}

    state = _state_with_components()
    state["components"] = []

    agent = session14_workers.build_budget_searcher_agent(
        search_budgets
    )

    with pytest.raises(ValueError, match="classified components"):
        await agent(state)

    assert call_count == 0


@pytest.mark.asyncio
async def test_budget_searcher_checks_authorization_before_tool_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    async def search_budgets(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        nonlocal call_count
        call_count += 1
        return {"budget_matches": []}

    def deny_tool(agent_id: str, tool: str) -> None:
        assert agent_id == "budget_searcher"
        assert tool == "search_budgets"
        raise PermissionError("denied for test")

    monkeypatch.setattr(
        session14_workers,
        "assert_tool_allowed",
        deny_tool,
    )

    agent = session14_workers.build_budget_searcher_agent(
        search_budgets
    )

    with pytest.raises(PermissionError, match="denied for test"):
        await agent(_state_with_components())

    assert call_count == 0
