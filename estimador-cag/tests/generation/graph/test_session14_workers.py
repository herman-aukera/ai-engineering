from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.generation.graph.nodes.session14_workers as session14_workers
from app.generation.graph.nodes import (
    build_classify_components_node,
    build_generate_estimate_node,
    build_validate_and_consolidate_node,
)
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

def _state_for_estimate() -> Session14EstimationGraphState:
    return {
        "estimation_id": "estimate-14",
        "transcript": "CLIENT-SECRET: confidential acquisition",
        "requirements": [
            {
                "requirement_id": "requirement-1",
                "text": "Provide authentication.",
            }
        ],
        "components": [
            {
                "component_id": "component-1",
                "name": "Authentication",
                "category": "backend",
                "requirement_ids": ["requirement-1"],
            }
        ],
        "budget_matches": [
            {
                "component_id": "component-1",
                "budget_id": "budget-1",
                "reference_component_id": "reference-1",
                "source_document_id": "document-1",
                "source_chunk_id": "chunk-1",
                "recorded_hours": 80.0,
                "distance": 0.1,
                "score": 0.9,
                "retrieval_method": "vector",
            },
            {
                "component_id": "component-1",
                "budget_id": "budget-2",
                "reference_component_id": "reference-2",
                "source_document_id": "document-2",
                "source_chunk_id": "chunk-2",
                "recorded_hours": 120.0,
                "distance": 0.2,
                "score": 0.8,
                "retrieval_method": "vector",
            },
        ],
        "budget_search_completed": True,
        "execution_metadata": {
            "graph_version": "session13.v1",
            "budget_match_count": 2,
        },
        "routing_steps": 3,
        "validation": {"stale": True},
    }


@pytest.mark.asyncio
async def test_estimate_generator_uses_authorized_minimum_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received_states: list[Session14EstimationGraphState] = []
    authorization_checks: list[tuple[str, str]] = []

    component_estimates = [
        {
            "component_id": "component-1",
            "name": "Authentication",
            "hours": 100.0,
            "grounding_status": "grounded",
            "reference_budget_ids": ["budget-1", "budget-2"],
            "reference_component_ids": [
                "reference-1",
                "reference-2",
            ],
            "source_hours": [80.0, 120.0],
            "source_range_low": 80.0,
            "source_range_high": 120.0,
            "dispersion": 0.4,
            "confidence": 0.55,
            "derivation_method": "median_recorded_hours",
            "review_reasons": [],
        }
    ]
    trace_event = {
        "event_type": "component_estimates_generated",
        "node": "generate_estimate",
        "summary": "Generated 1 grounded component estimates.",
        "evidence_refs": [
            "component-1",
            "budget-1",
            "budget-2",
        ],
        "state_delta_keys": [
            "component_estimates",
            "execution_metadata",
            "trace_events",
        ],
    }

    async def calculate_estimate(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        received_states.append(deepcopy(state))
        return {
            "component_estimates": deepcopy(component_estimates),
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "component_estimate_count": 1,
            },
            "trace_events": [deepcopy(trace_event)],
        }

    def record_authorization(
        agent_id: str,
        tool: str,
    ) -> None:
        authorization_checks.append((agent_id, tool))

    monkeypatch.setattr(
        session14_workers,
        "assert_tool_allowed",
        record_authorization,
    )

    state = _state_for_estimate()
    before = deepcopy(state)
    agent = session14_workers.build_estimate_generator_agent(
        calculate_estimate
    )

    update = await agent(state)

    assert authorization_checks == [
        ("estimate_generator", "calculate_estimate")
    ]
    assert received_states == [
        {
            "components": before["components"],
            "budget_matches": before["budget_matches"],
            "execution_metadata": before["execution_metadata"],
        }
    ]
    assert "transcript" not in received_states[0]
    assert "requirements" not in received_states[0]
    assert "validation" not in received_states[0]
    assert state == before

    assert update["component_estimates"] == component_estimates
    assert update["execution_metadata"] == {
        "graph_version": "session13.v1",
        "budget_match_count": 2,
        "component_estimate_count": 1,
    }
    assert update["trace_events"] == [trace_event]
    assert "transcript" not in update
    assert "requirements" not in update
    assert "budget_matches" not in update

    assert update["agent_contributions"] == [
        {
            "contribution_id": (
                "estimate-14:estimate_generator:3"
            ),
            "agent_id": "estimate_generator",
            "sequence": 3,
            "summary": "Generated 1 component estimate.",
            "state_delta_keys": [
                "agent_contributions",
                "component_estimates",
                "execution_metadata",
                "trace_events",
            ],
        }
    ]
    assert "CLIENT-SECRET" not in str(
        update["agent_contributions"]
    )


@pytest.mark.asyncio
async def test_estimate_generator_rejects_missing_prerequisites_before_call() -> None:
    call_count = 0

    async def calculate_estimate(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        nonlocal call_count
        call_count += 1
        return {"component_estimates": []}

    agent = session14_workers.build_estimate_generator_agent(
        calculate_estimate
    )

    missing_components = _state_for_estimate()
    missing_components["components"] = []

    with pytest.raises(ValueError, match="classified components"):
        await agent(missing_components)

    unfinished_search = _state_for_estimate()
    unfinished_search.pop("budget_search_completed")

    with pytest.raises(ValueError, match="completed budget search"):
        await agent(unfinished_search)

    assert call_count == 0


@pytest.mark.asyncio
async def test_estimate_generator_checks_authorization_before_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    async def calculate_estimate(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        nonlocal call_count
        call_count += 1
        return {"component_estimates": []}

    def deny_tool(agent_id: str, tool: str) -> None:
        assert agent_id == "estimate_generator"
        assert tool == "calculate_estimate"
        raise PermissionError("denied for test")

    monkeypatch.setattr(
        session14_workers,
        "assert_tool_allowed",
        deny_tool,
    )

    agent = session14_workers.build_estimate_generator_agent(
        calculate_estimate
    )

    with pytest.raises(PermissionError, match="denied for test"):
        await agent(_state_for_estimate())

    assert call_count == 0

@pytest.mark.asyncio
async def test_estimate_generator_preserves_real_python_arithmetic(
) -> None:
    calculate_estimate = build_generate_estimate_node(
        GraphNodeDependencies(
            requirement_extractor=object(),
            component_classifier=object(),
            budget_searcher=object(),
        )
    )

    state = _state_for_estimate()
    state["budget_matches"][1]["recorded_hours"] = 110.0
    state["budget_matches"].append(
        {
            "component_id": "component-1",
            "budget_id": "budget-3",
            "reference_component_id": "reference-3",
            "source_document_id": "document-3",
            "source_chunk_id": "chunk-3",
            "recorded_hours": 100.0,
            "distance": 0.15,
            "score": 0.85,
            "retrieval_method": "vector",
        }
    )
    state["execution_metadata"]["budget_match_count"] = 3
    before = deepcopy(state)

    agent = session14_workers.build_estimate_generator_agent(
        calculate_estimate
    )

    update = await agent(state)

    assert state == before
    assert update["component_estimates"] == [
        {
            "component_id": "component-1",
            "name": "Authentication",
            "hours": 100.0,
            "grounding_status": "grounded",
            "reference_budget_ids": [
                "budget-1",
                "budget-2",
                "budget-3",
            ],
            "reference_component_ids": [
                "reference-1",
                "reference-2",
                "reference-3",
            ],
            "source_hours": [80.0, 100.0, 110.0],
            "source_range_low": 80.0,
            "source_range_high": 110.0,
            "dispersion": 0.3,
            "confidence": 0.85,
            "derivation_method": "median_recorded_hours",
            "review_reasons": [],
        }
    ]
    assert update["execution_metadata"] == {
        "graph_version": "session13.v1",
        "budget_match_count": 3,
        "component_estimate_count": 1,
    }
    assert update["trace_events"] == [
        {
            "event_type": "component_estimates_generated",
            "node": "generate_estimate",
            "summary": "Generated 1 grounded component estimates.",
            "evidence_refs": [
                "component-1",
                "budget-1",
                "budget-2",
                "budget-3",
            ],
            "state_delta_keys": [
                "component_estimates",
                "execution_metadata",
                "trace_events",
            ],
        }
    ]
    assert "review_required" not in update
    assert "errors" not in update
    assert "components" not in update
    assert "budget_matches" not in update
    assert "transcript" not in update

    assert update["agent_contributions"] == [
        {
            "contribution_id": (
                "estimate-14:estimate_generator:3"
            ),
            "agent_id": "estimate_generator",
            "sequence": 3,
            "summary": "Generated 1 component estimate.",
            "state_delta_keys": [
                "agent_contributions",
                "component_estimates",
                "execution_metadata",
                "trace_events",
            ],
        }
    ]
def _state_for_validation() -> Session14EstimationGraphState:
    state = _state_for_estimate()
    state["component_estimates"] = [
        {
            "component_id": "component-1",
            "name": "Authentication",
            "hours": 100.0,
            "grounding_status": "grounded",
            "reference_budget_ids": ["budget-1", "budget-2"],
            "reference_component_ids": [
                "reference-1",
                "reference-2",
            ],
            "source_hours": [80.0, 120.0],
            "source_range_low": 80.0,
            "source_range_high": 120.0,
            "dispersion": 0.4,
            "confidence": 0.55,
            "derivation_method": "median_recorded_hours",
            "review_reasons": [],
        }
    ]
    state["status"] = "pending"
    state["review_required"] = False
    state["errors"] = []
    state["routing_steps"] = 4
    state.pop("validation", None)
    return state


def _canonical_validation_estimate(
    state: Session14EstimationGraphState,
) -> dict[str, object]:
    return {
        "components": deepcopy(state["component_estimates"]),
        "subtotal_hours": 100.0,
        "contingency_hours": 0.0,
        "total_hours": 100.0,
        "total_cost_eur": None,
        "currency": "EUR",
    }


@pytest.mark.asyncio
async def test_coherence_validator_uses_authorized_minimum_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received_states: list[Session14EstimationGraphState] = []
    authorization_checks: list[tuple[str, str]] = []

    state = _state_for_validation()
    state["validation"] = {"stale": True}
    before = deepcopy(state)
    canonical_estimate = _canonical_validation_estimate(state)
    trace_event = {
        "event_type": "estimate_validated",
        "node": "validate_and_consolidate",
        "summary": (
            "Validated 1 grounded component estimates "
            "totaling 100.0 hours."
        ),
        "evidence_refs": [
            "component-1",
            "budget-1",
            "budget-2",
        ],
        "state_delta_keys": [
            "estimate",
            "status",
            "review_required",
            "trace_events",
        ],
    }

    async def validate_estimate(
        projected_state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        received_states.append(deepcopy(projected_state))
        return {
            "estimate": deepcopy(canonical_estimate),
            "status": "validated",
            "review_required": False,
            "trace_events": [deepcopy(trace_event)],
        }

    def record_authorization(
        agent_id: str,
        tool: str,
    ) -> None:
        authorization_checks.append((agent_id, tool))

    monkeypatch.setattr(
        session14_workers,
        "assert_tool_allowed",
        record_authorization,
    )

    agent = session14_workers.build_coherence_validator_agent(
        validate_estimate
    )

    update = await agent(state)

    assert authorization_checks == [
        ("coherence_validator", "validate_estimate")
    ]
    assert received_states == [
        {
            "component_estimates": before["component_estimates"],
            "review_required": False,
            "errors": [],
        }
    ]
    assert "transcript" not in received_states[0]
    assert "requirements" not in received_states[0]
    assert "components" not in received_states[0]
    assert "budget_matches" not in received_states[0]
    assert "execution_metadata" not in received_states[0]
    assert "validation" not in received_states[0]
    assert "estimate" not in received_states[0]
    assert state == before

    assert update["estimate"] == canonical_estimate
    assert update["status"] == "validated"
    assert update["review_required"] is False
    assert update["validation"] == {
        "is_coherent": True,
        "review_required": False,
        "status": "validated",
    }
    assert update["trace_events"] == [trace_event]
    assert "component_estimates" not in update
    assert "transcript" not in update
    assert "budget_matches" not in update

    assert update["agent_contributions"] == [
        {
            "contribution_id": (
                "estimate-14:coherence_validator:4"
            ),
            "agent_id": "coherence_validator",
            "sequence": 4,
            "summary": (
                "Validation completed with status validated."
            ),
            "state_delta_keys": [
                "agent_contributions",
                "estimate",
                "review_required",
                "status",
                "trace_events",
                "validation",
            ],
        }
    ]
    assert "CLIENT-SECRET" not in str(
        update["agent_contributions"]
    )


@pytest.mark.asyncio
async def test_coherence_validator_rejects_missing_estimates_before_call() -> None:
    call_count = 0

    async def validate_estimate(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        nonlocal call_count
        call_count += 1
        return {
            "estimate": {},
            "status": "needs_review",
            "review_required": True,
        }

    agent = session14_workers.build_coherence_validator_agent(
        validate_estimate
    )

    missing_estimates = _state_for_validation()
    missing_estimates.pop("component_estimates")

    with pytest.raises(ValueError, match="component estimates"):
        await agent(missing_estimates)

    empty_estimates = _state_for_validation()
    empty_estimates["component_estimates"] = []

    with pytest.raises(ValueError, match="component estimates"):
        await agent(empty_estimates)

    assert call_count == 0


@pytest.mark.asyncio
async def test_coherence_validator_checks_authorization_before_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    async def validate_estimate(
        state: Session14EstimationGraphState,
    ) -> Session14EstimationGraphState:
        nonlocal call_count
        call_count += 1
        return {
            "estimate": {},
            "status": "validated",
            "review_required": False,
        }

    def deny_tool(agent_id: str, tool: str) -> None:
        assert agent_id == "coherence_validator"
        assert tool == "validate_estimate"
        raise PermissionError("denied for test")

    monkeypatch.setattr(
        session14_workers,
        "assert_tool_allowed",
        deny_tool,
    )

    agent = session14_workers.build_coherence_validator_agent(
        validate_estimate
    )

    with pytest.raises(PermissionError, match="denied for test"):
        await agent(_state_for_validation())

    assert call_count == 0


@pytest.mark.asyncio
async def test_coherence_validator_preserves_real_mismatch_detection() -> None:
    state = _state_for_validation()
    stale_estimate = _canonical_validation_estimate(state)
    stale_estimate["total_hours"] = 999.0
    state["estimate"] = stale_estimate
    before = deepcopy(state)

    agent = session14_workers.build_coherence_validator_agent(
        build_validate_and_consolidate_node()
    )

    update = await agent(state)

    assert state == before
    assert update["estimate"] == {
        "components": before["component_estimates"],
        "subtotal_hours": 100.0,
        "contingency_hours": 0.0,
        "total_hours": 100.0,
        "total_cost_eur": None,
        "currency": "EUR",
    }
    assert update["status"] == "needs_review"
    assert update["review_required"] is True
    assert update["validation"] == {
        "is_coherent": False,
        "review_required": True,
        "status": "needs_review",
    }
    assert update["errors"] == [
        {
            "code": "estimate_total_mismatch",
            "message": (
                "A pre-existing aggregate estimate did not match "
                "the component-derived arithmetic."
            ),
            "node": "validate_and_consolidate",
            "severity": "error",
        }
    ]
    assert update["trace_events"] == [
        {
            "event_type": "estimate_needs_review",
            "node": "validate_and_consolidate",
            "summary": (
                "Consolidated 1 component estimates; "
                "0 requires review."
            ),
            "evidence_refs": [
                "component-1",
                "budget-1",
                "budget-2",
            ],
            "state_delta_keys": [
                "estimate",
                "status",
                "review_required",
                "errors",
                "trace_events",
            ],
        }
    ]
    assert "component_estimates" not in update
    assert "transcript" not in update
    assert "budget_matches" not in update

    assert update["agent_contributions"] == [
        {
            "contribution_id": (
                "estimate-14:coherence_validator:4"
            ),
            "agent_id": "coherence_validator",
            "sequence": 4,
            "summary": (
                "Validation completed with status needs_review."
            ),
            "state_delta_keys": [
                "agent_contributions",
                "errors",
                "estimate",
                "review_required",
                "status",
                "trace_events",
                "validation",
            ],
        }
    ]
