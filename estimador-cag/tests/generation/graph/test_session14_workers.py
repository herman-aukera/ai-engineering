from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.generation.graph.nodes.session14_workers as session14_workers
from app.generation.graph.nodes import build_classify_components_node
from app.generation.graph.ports import GraphNodeDependencies
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

def _state_for_requirements() -> Session14EstimationGraphState:
    return {
        "estimation_id": "estimate-14",
        "transcript": "CLIENT-SECRET: confidential acquisition",
        "execution_metadata": {
            "graph_version": "session13.v1",
        },
        "routing_steps": 1,
    }


@pytest.mark.asyncio
async def test_requirements_extractor_composes_inherited_nodes_with_minimum_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extraction_states: list[Session14EstimationGraphState] = []
    classification_states: list[Session14EstimationGraphState] = []

    requirements = [
        {
            "requirement_id": "requirement-1",
            "text": "Provide authentication.",
        },
        {
            "requirement_id": "requirement-2",
            "text": "Retain an audit trail.",
        },
    ]
    components = [
        {
            "component_id": "component-1",
            "name": "Authentication",
            "category": "backend",
            "requirement_ids": ["requirement-1"],
        }
    ]
    extraction_trace = {
        "event_type": "requirements_extracted",
        "node": "extract_requirements",
        "summary": "Extracted 2 structured requirements.",
        "evidence_refs": [
            "requirement-1",
            "requirement-2",
        ],
        "state_delta_keys": [
            "requirements",
            "execution_metadata",
            "trace_events",
        ],
    }
    classification_trace = {
        "event_type": "components_classified_with_gaps",
        "node": "classify_components",
        "summary": (
            "Classified 1 implementation component "
            "with 1 unmapped requirement."
        ),
        "evidence_refs": [
            "component-1",
            "requirement-1",
            "requirement-2",
        ],
        "state_delta_keys": [
            "components",
            "review_required",
            "errors",
            "execution_metadata",
            "trace_events",
        ],
    }
    classification_issue = {
        "code": "unmapped_requirements",
        "message": (
            "Some requirements were not assigned "
            "to a component: requirement-2."
        ),
        "node": "classify_components",
        "severity": "warning",
    }

    async def extract_requirements(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        extraction_states.append(deepcopy(state))
        return {
            "requirements": deepcopy(requirements),
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "requirement_count": 2,
            },
            "trace_events": [deepcopy(extraction_trace)],
        }

    async def classify_components(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        classification_states.append(deepcopy(state))
        return {
            "components": deepcopy(components),
            "review_required": True,
            "errors": [deepcopy(classification_issue)],
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "component_count": 1,
            },
            "trace_events": [deepcopy(classification_trace)],
        }

    def fail_if_business_tool_is_checked(
        agent_id: str,
        tool: str,
    ) -> None:
        raise AssertionError(
            f"requirements_extractor requested business tool "
            f"{agent_id}:{tool}"
        )

    monkeypatch.setattr(
        session14_workers,
        "assert_tool_allowed",
        fail_if_business_tool_is_checked,
    )

    state = _state_for_requirements()
    before = deepcopy(state)
    agent = session14_workers.build_requirements_extractor_agent(
        extract_requirements,
        classify_components,
    )

    update = await agent(state)

    assert extraction_states == [
        {
            "transcript": before["transcript"],
            "execution_metadata": before["execution_metadata"],
        }
    ]
    assert classification_states == [
        {
            "requirements": requirements,
            "execution_metadata": {
                "graph_version": "session13.v1",
                "requirement_count": 2,
            },
        }
    ]
    assert "transcript" not in classification_states[0]
    assert state == before

    assert update["requirements"] == requirements
    assert update["components"] == components
    assert update["execution_metadata"] == {
        "graph_version": "session13.v1",
        "requirement_count": 2,
        "component_count": 1,
    }
    assert update["trace_events"] == [
        extraction_trace,
        classification_trace,
    ]
    assert update["errors"] == [classification_issue]
    assert update["review_required"] is True
    assert update["requirements_extraction_completed"] is True
    assert "transcript" not in update

    assert update["agent_contributions"] == [
        {
            "contribution_id": (
                "estimate-14:requirements_extractor:1"
            ),
            "agent_id": "requirements_extractor",
            "sequence": 1,
            "summary": (
                "Extracted 2 requirements and "
                "classified 1 component."
            ),
            "state_delta_keys": [
                "agent_contributions",
                "components",
                "errors",
                "execution_metadata",
                "requirements",
                "requirements_extraction_completed",
                "review_required",
                "trace_events",
            ],
        }
    ]
    assert "CLIENT-SECRET" not in str(
        update["agent_contributions"]
    )


@pytest.mark.asyncio
async def test_requirements_extractor_stops_before_classification_on_failure() -> None:
    classification_call_count = 0
    extraction_issue = {
        "code": "no_requirements",
        "message": "No structured requirements were extracted.",
        "node": "extract_requirements",
        "severity": "warning",
    }
    extraction_trace = {
        "event_type": "requirements_missing",
        "node": "extract_requirements",
        "summary": "Requirement extraction produced no requirements.",
        "evidence_refs": [],
        "state_delta_keys": [
            "requirements",
            "review_required",
            "errors",
            "execution_metadata",
            "trace_events",
        ],
    }

    async def extract_requirements(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        return {
            "requirements": [],
            "review_required": True,
            "errors": [deepcopy(extraction_issue)],
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "requirement_count": 0,
            },
            "trace_events": [deepcopy(extraction_trace)],
        }

    async def classify_components(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        nonlocal classification_call_count
        classification_call_count += 1
        return {"components": []}

    state = _state_for_requirements()
    state["components"] = [
        {
            "component_id": "stale-component",
            "name": "Stale component",
            "category": "backend",
            "requirement_ids": ["stale-requirement"],
        }
    ]
    before = deepcopy(state)

    agent = session14_workers.build_requirements_extractor_agent(
        extract_requirements,
        classify_components,
    )

    update = await agent(state)

    assert classification_call_count == 0
    assert state == before
    assert update["requirements"] == []
    assert update["components"] == []
    assert update["requirements_extraction_completed"] is False
    assert update["errors"] == [extraction_issue]
    assert update["trace_events"] == [extraction_trace]
    assert "transcript" not in update

    assert update["agent_contributions"] == [
        {
            "contribution_id": (
                "estimate-14:requirements_extractor:1"
            ),
            "agent_id": "requirements_extractor",
            "sequence": 1,
            "summary": (
                "Requirement extraction produced no usable "
                "requirements; component classification was skipped."
            ),
            "state_delta_keys": [
                "agent_contributions",
                "components",
                "errors",
                "execution_metadata",
                "requirements",
                "requirements_extraction_completed",
                "review_required",
                "trace_events",
            ],
        }
    ]


@pytest.mark.asyncio
async def test_requirements_extractor_marks_empty_real_classification_incomplete() -> None:
    requirements = [
        {
            "requirement_id": "requirement-1",
            "text": "Provide authentication.",
        }
    ]
    classifier = AsyncMock(return_value=[])
    classify_components = build_classify_components_node(
        GraphNodeDependencies(
            requirement_extractor=object(),
            component_classifier=SimpleNamespace(
                classify_components=classifier,
            ),
            budget_searcher=object(),
        )
    )

    async def extract_requirements(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        return {
            "requirements": deepcopy(requirements),
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "requirement_count": 1,
            },
            "trace_events": [
                {
                    "event_type": "requirements_extracted",
                    "node": "extract_requirements",
                    "summary": "Extracted 1 structured requirement.",
                    "evidence_refs": ["requirement-1"],
                    "state_delta_keys": [
                        "requirements",
                        "execution_metadata",
                        "trace_events",
                    ],
                }
            ],
        }

    state = _state_for_requirements()
    state["components"] = [
        {
            "component_id": "stale-component",
            "name": "Stale component",
            "category": "backend",
            "requirement_ids": ["stale-requirement"],
        }
    ]
    before = deepcopy(state)

    agent = session14_workers.build_requirements_extractor_agent(
        extract_requirements,
        classify_components,
    )

    update = await agent(state)

    classifier.assert_awaited_once_with(
        requirements=requirements,
    )
    assert state == before
    assert update["requirements"] == requirements
    assert update["components"] == []
    assert update["requirements_extraction_completed"] is False
    assert update["review_required"] is True
    assert update["execution_metadata"] == {
        "graph_version": "session13.v1",
        "requirement_count": 1,
        "component_count": 0,
    }
    assert update["errors"] == [
        {
            "code": "no_components",
            "message": "No implementation components were classified.",
            "node": "classify_components",
            "severity": "warning",
        }
    ]
    assert [
        event["event_type"]
        for event in update["trace_events"]
    ] == [
        "requirements_extracted",
        "components_missing",
    ]
    assert update["agent_contributions"][0]["summary"] == (
        "Extracted 1 requirement, but component classification "
        "produced no usable components."
    )
    assert "transcript" not in update
