from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from types import ModuleType
from typing import Literal

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START
from langgraph.types import Command

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
    FakeSupervisorRouteProposer,
)
from app.generation.graph.ports import (
    GraphNodeDependencies,
    SupervisorRouteProposer,
)
from app.generation.graph.review_state import (
    Session14EstimationGraphState,
)
from app.generation.graph.state import new_estimation_graph_state

TRANSCRIPT = (
    "CLIENT-SECRET: build JWT authentication with an audit trail."
)

REQUIREMENTS = [
    {
        "requirement_id": "REQ-001",
        "text": "Users authenticate with JWT.",
    }
]

COMPONENTS = [
    {
        "component_id": "CMP-001",
        "name": "JWT authentication",
        "category": "backend",
        "requirement_ids": ["REQ-001"],
    }
]


def _match(
    *,
    budget_id: str,
    reference_component_id: str,
    hours: float,
) -> dict[str, object]:
    return {
        "component_id": "CMP-001",
        "budget_id": budget_id,
        "reference_component_id": reference_component_id,
        "source_document_id": f"DOC-{budget_id}",
        "source_chunk_id": f"CH-{budget_id}",
        "recorded_hours": hours,
        "distance": 0.1,
        "score": 0.9,
        "retrieval_method": "hybrid",
    }


MATCHES_BY_COMPONENT = {
    "CMP-001": [
        _match(
            budget_id="BUD-101",
            reference_component_id="AUTH-01",
            hours=32.0,
        ),
        _match(
            budget_id="BUD-102",
            reference_component_id="AUTH-02",
            hours=40.0,
        ),
        _match(
            budget_id="BUD-103",
            reference_component_id="AUTH-03",
            hours=48.0,
        ),
    ]
}


def _dependencies(
    route_proposer: SupervisorRouteProposer | None = None,
) -> tuple[
    GraphNodeDependencies,
    FakeRequirementExtractor,
    FakeComponentClassifier,
    FakeBudgetSearcher,
]:
    extractor = FakeRequirementExtractor(REQUIREMENTS)
    classifier = FakeComponentClassifier(COMPONENTS)
    searcher = FakeBudgetSearcher(MATCHES_BY_COMPONENT)

    dependencies = GraphNodeDependencies(
        requirement_extractor=extractor,
        component_classifier=classifier,
        budget_searcher=searcher,
        supervisor_route_proposer=route_proposer,
        search_k=5,
    )

    return dependencies, extractor, classifier, searcher


def _initial_state() -> Session14EstimationGraphState:
    state = Session14EstimationGraphState(
        **new_estimation_graph_state(
            transcript=TRANSCRIPT,
            estimation_id="estimate-14",
            graph_version="session14.v1",
        )
    )
    state.update(
        {
            "requirements_extraction_completed": False,
            "budget_search_completed": False,
            "validation": None,
            "confidence": None,
            "routing_steps": 0,
            "max_routing_steps": 12,
            "current_agent": None,
            "previous_agent": None,
            "next_agent": None,
            "route_reason_code": None,
            "route_events": [],
            "agent_contributions": [],
        }
    )
    return state


async def _unexpected_human_review_gate(
    state: Session14EstimationGraphState,
) -> Command[Literal["finalize"]]:
    raise AssertionError(
        "The reliable Level 1 path must not enter human review."
    )


def _session14_build_module() -> ModuleType:
    try:
        return import_module(
            "app.generation.graph.session14_build"
        )
    except ModuleNotFoundError as exc:
        pytest.fail(
            f"Session 14 graph builder is missing: {exc}",
            pytrace=False,
        )


def _build_graph(
    dependencies: GraphNodeDependencies,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
):
    module = _session14_build_module()
    builder = getattr(
        module,
        "build_session14_estimation_graph",
        None,
    )

    assert callable(builder)

    graph = builder(
        dependencies,
        human_review_gate=_unexpected_human_review_gate,
        checkpointer=checkpointer,
    )
    return module, graph


def test_session14_graph_has_command_driven_topology() -> None:
    dependencies, _, _, _ = _dependencies()
    module, graph = _build_graph(dependencies)
    drawable = graph.get_graph()

    expected_nodes = (
        "supervisor",
        "requirements_extractor",
        "budget_searcher",
        "estimate_generator",
        "coherence_validator",
        "human_review_gate",
        "finalize",
    )

    assert graph.name == module.SESSION14_GRAPH_NAME
    assert tuple(module.SESSION14_NODE_NAMES) == expected_nodes
    assert set(drawable.nodes) == {
        START,
        *expected_nodes,
        END,
    }

    static_edges = {
        (edge.source, edge.target)
        for edge in drawable.edges
        if not getattr(edge, "conditional", False)
    }
    assert static_edges == {
        (START, "supervisor"),
    }

    command_edges = {
        (edge.source, edge.target)
        for edge in drawable.edges
        if getattr(edge, "conditional", False)
    }

    assert {
        ("supervisor", "requirements_extractor"),
        ("supervisor", "budget_searcher"),
        ("supervisor", "estimate_generator"),
        ("supervisor", "coherence_validator"),
        ("supervisor", "human_review_gate"),
        ("supervisor", "finalize"),
        ("requirements_extractor", "supervisor"),
        ("budget_searcher", "supervisor"),
        ("estimate_generator", "supervisor"),
        ("coherence_validator", "supervisor"),
        ("human_review_gate", "finalize"),
        ("finalize", END),
    }.issubset(command_edges)


def test_session14_graph_accepts_injected_checkpointer() -> None:
    dependencies, _, _, _ = _dependencies()
    checkpointer = InMemorySaver()

    _, graph = _build_graph(
        dependencies,
        checkpointer=checkpointer,
    )

    assert graph.checkpointer is checkpointer


@pytest.mark.asyncio
async def test_session14_graph_runs_reliable_path_end_to_end() -> None:
    dependencies, extractor, classifier, searcher = _dependencies()
    _, graph = _build_graph(dependencies)

    initial_state = _initial_state()
    original_state = deepcopy(initial_state)

    result = await graph.ainvoke(initial_state)

    assert initial_state == original_state

    assert result["status"] == "validated"
    assert result["review_required"] is False
    assert result["errors"] == []
    assert result["estimate"]["total_hours"] == 40.0

    assert result["requirements_extraction_completed"] is True
    assert result["budget_search_completed"] is True
    assert result["validation"] == {
        "is_coherent": True,
        "review_required": False,
        "status": "validated",
    }

    assert result["routing_steps"] == 5
    assert result["previous_agent"] == "supervisor"
    assert result["current_agent"] == "finalize"
    assert result["next_agent"] == END
    assert result["route_reason_code"] == "work_complete"

    assert [
        event["sequence"]
        for event in result["route_events"]
    ] == [1, 2, 3, 4, 5]
    assert [
        event["next_agent"]
        for event in result["route_events"]
    ] == [
        "requirements_extractor",
        "budget_searcher",
        "estimate_generator",
        "coherence_validator",
        "finalize",
    ]
    assert [
        event["reason_code"]
        for event in result["route_events"]
    ] == [
        "missing_requirements",
        "missing_budget_evidence",
        "missing_estimate",
        "missing_validation",
        "work_complete",
    ]
    assert [
        event["route_event_id"]
        for event in result["route_events"]
    ] == [
        f"estimate-14:supervisor-route:{sequence}"
        for sequence in range(1, 6)
    ]

    assert [
        contribution["agent_id"]
        for contribution in result["agent_contributions"]
    ] == [
        "requirements_extractor",
        "budget_searcher",
        "estimate_generator",
        "coherence_validator",
    ]
    assert [
        contribution["sequence"]
        for contribution in result["agent_contributions"]
    ] == [1, 2, 3, 4]

    assert [
        event["node"]
        for event in result["trace_events"]
    ] == [
        "extract_requirements",
        "classify_components",
        "search_budgets",
        "generate_estimate",
        "validate_and_consolidate",
    ]

    assert "CLIENT-SECRET" not in str(result["route_events"])
    assert "CLIENT-SECRET" not in str(
        result["agent_contributions"]
    )

    assert extractor.calls == [TRANSCRIPT]
    assert classifier.calls == [REQUIREMENTS]
    assert searcher.calls == [
        {
            "component_id": "CMP-001",
            "k": 5,
        }
    ]


@pytest.mark.asyncio
async def test_session14_graph_accepts_model_owned_routes_end_to_end() -> None:
    proposer = FakeSupervisorRouteProposer(
        [
            "requirements_extractor",
            "budget_searcher",
            "estimate_generator",
            "coherence_validator",
            "finalize",
        ]
    )
    dependencies, _, _, _ = _dependencies(proposer)
    _, graph = _build_graph(dependencies)

    result = await graph.ainvoke(_initial_state())

    assert result["status"] == "validated"
    assert [
        event["route_source"]
        for event in result["route_events"]
    ] == ["model"] * 5
    assert [
        event["proposed_agent"]
        for event in result["route_events"]
    ] == [
        "requirements_extractor",
        "budget_searcher",
        "estimate_generator",
        "coherence_validator",
        "finalize",
    ]
    assert [
        call["candidates"]
        for call in proposer.calls
    ] == [
        ["requirements_extractor"],
        ["budget_searcher"],
        ["estimate_generator"],
        ["coherence_validator"],
        ["finalize", "human_review_gate"],
    ]
    assert "CLIENT-SECRET" not in str(proposer.calls)
