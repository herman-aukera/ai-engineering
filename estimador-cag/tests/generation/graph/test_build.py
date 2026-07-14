from __future__ import annotations

from copy import deepcopy

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START

from app.generation.graph.build import (
    GRAPH_NAME,
    REQUIRED_NODE_NAMES,
    build_estimation_graph,
)
from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.state import new_estimation_graph_state

TRANSCRIPT = (
    "The system requires JWT authentication and auditable "
    "logging of sensitive actions."
)

REQUIREMENTS = [
    {
        "requirement_id": "REQ-001",
        "text": "Users authenticate with JWT.",
    },
    {
        "requirement_id": "REQ-002",
        "text": "Sensitive actions are written to an audit log.",
    },
]

COMPONENTS = [
    {
        "component_id": "CMP-001",
        "name": "JWT authentication",
        "category": "backend",
        "requirement_ids": ["REQ-001"],
    },
    {
        "component_id": "CMP-002",
        "name": "Audit logging",
        "category": "observability",
        "requirement_ids": ["REQ-002"],
    },
]


def _match(
    *,
    component_id: str,
    budget_id: str,
    reference_component_id: str,
    hours: float,
) -> dict[str, object]:
    return {
        "component_id": component_id,
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
            component_id="CMP-001",
            budget_id="BUD-101",
            reference_component_id="AUTH-01",
            hours=32.0,
        ),
        _match(
            component_id="CMP-001",
            budget_id="BUD-102",
            reference_component_id="AUTH-02",
            hours=40.0,
        ),
        _match(
            component_id="CMP-001",
            budget_id="BUD-103",
            reference_component_id="AUTH-03",
            hours=48.0,
        ),
    ],
    "CMP-002": [
        _match(
            component_id="CMP-002",
            budget_id="BUD-201",
            reference_component_id="AUDIT-01",
            hours=20.0,
        ),
        _match(
            component_id="CMP-002",
            budget_id="BUD-202",
            reference_component_id="AUDIT-02",
            hours=24.0,
        ),
        _match(
            component_id="CMP-002",
            budget_id="BUD-203",
            reference_component_id="AUDIT-03",
            hours=28.0,
        ),
    ],
}


def _dependencies() -> tuple[
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
        search_k=5,
    )

    return dependencies, extractor, classifier, searcher


def test_graph_has_exact_required_topology() -> None:
    dependencies, _, _, _ = _dependencies()

    graph = build_estimation_graph(dependencies)
    drawable = graph.get_graph()

    assert graph.name == GRAPH_NAME
    assert tuple(REQUIRED_NODE_NAMES) == (
        "extract_requirements",
        "classify_components",
        "search_budgets",
        "generate_estimate",
        "validate_and_consolidate",
    )

    assert set(drawable.nodes) == {
        START,
        *REQUIRED_NODE_NAMES,
        END,
    }

    assert {
        (edge.source, edge.target)
        for edge in drawable.edges
    } == {
        (START, "extract_requirements"),
        ("extract_requirements", "classify_components"),
        ("classify_components", "search_budgets"),
        ("search_budgets", "generate_estimate"),
        ("generate_estimate", "validate_and_consolidate"),
        ("validate_and_consolidate", END),
    }

    assert not any(
        getattr(edge, "conditional", False)
        for edge in drawable.edges
    )


def test_graph_accepts_injected_checkpointer() -> None:
    dependencies, _, _, _ = _dependencies()
    checkpointer = InMemorySaver()

    graph = build_estimation_graph(
        dependencies,
        checkpointer=checkpointer,
    )

    assert graph.checkpointer is checkpointer


@pytest.mark.asyncio
async def test_graph_runs_all_nodes_and_accumulates_reducers_once() -> None:
    dependencies, extractor, classifier, searcher = _dependencies()
    graph = build_estimation_graph(dependencies)

    initial_state = new_estimation_graph_state(
        transcript=TRANSCRIPT,
        estimation_id="estimate-graph-001",
    )
    original_state = deepcopy(initial_state)

    result = await graph.ainvoke(initial_state)

    assert initial_state == original_state

    assert result["status"] == "validated"
    assert result["review_required"] is False
    assert result["errors"] == []

    assert result["estimate"]["subtotal_hours"] == 64.0
    assert result["estimate"]["contingency_hours"] == 0.0
    assert result["estimate"]["total_hours"] == 64.0
    assert result["estimate"]["total_cost_eur"] is None
    assert result["estimate"]["currency"] == "EUR"

    assert len(result["requirements"]) == 2
    assert len(result["components"]) == 2
    assert len(result["budget_matches"]) == 6
    assert len(result["component_estimates"]) == 2

    assert result["execution_metadata"] == {
        "requirement_count": 2,
        "component_count": 2,
        "budget_match_count": 6,
        "component_estimate_count": 2,
    }

    assert [
        event["node"]
        for event in result["trace_events"]
    ] == list(REQUIRED_NODE_NAMES)

    assert len(result["trace_events"]) == 5

    assert extractor.calls == [TRANSCRIPT]
    assert classifier.calls == [REQUIREMENTS]
    assert searcher.calls == [
        {"component_id": "CMP-001", "k": 5},
        {"component_id": "CMP-002", "k": 5},
    ]
