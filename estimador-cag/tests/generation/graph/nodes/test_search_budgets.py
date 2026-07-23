from __future__ import annotations

from copy import deepcopy

import pytest

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.nodes.search_budgets import (
    build_search_budgets_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.state import new_estimation_graph_state

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

MATCH_1 = {
    "component_id": "CMP-001",
    "budget_id": "BUD-101",
    "reference_component_id": "AUTH-01",
    "source_document_id": "DOC-10",
    "source_chunk_id": "CH-101",
    "recorded_hours": 40.0,
    "distance": 0.08,
    "score": 0.92,
    "retrieval_method": "hybrid",
}

MATCH_2 = {
    "component_id": "CMP-001",
    "budget_id": "BUD-102",
    "reference_component_id": "AUTH-02",
    "source_document_id": "DOC-11",
    "source_chunk_id": "CH-102",
    "recorded_hours": 56.0,
    "distance": 0.12,
    "score": 0.88,
    "retrieval_method": "hybrid",
}

MATCH_3 = {
    "component_id": "CMP-002",
    "budget_id": "BUD-201",
    "reference_component_id": "AUDIT-01",
    "source_document_id": "DOC-20",
    "source_chunk_id": "CH-201",
    "recorded_hours": 24.0,
    "distance": 0.05,
    "score": 0.95,
    "retrieval_method": "hybrid",
}


def _dependencies(
    budget_searcher: object,
    *,
    search_k: int = 5,
) -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor([]),
        component_classifier=FakeComponentClassifier([]),
        budget_searcher=budget_searcher,
        search_k=search_k,
    )


def _state() -> dict[str, object]:
    state = new_estimation_graph_state(
        transcript="JWT authentication and audit logging are required.",
        estimation_id="estimate-123",
    )
    state["components"] = deepcopy(COMPONENTS)
    state["execution_metadata"] = {
        "graph_version": "session13.v1",
        "requirement_count": 2,
        "component_count": 2,
    }
    return state


@pytest.mark.asyncio
async def test_search_budgets_returns_partial_reducer_update_without_mutation() -> None:
    searcher = FakeBudgetSearcher(
        {
            "CMP-001": [MATCH_1, MATCH_2],
            "CMP-002": [MATCH_3],
        }
    )
    node = build_search_budgets_node(_dependencies(searcher))

    state = _state()
    original_state = deepcopy(state)

    update = await node(state)

    assert state == original_state
    assert searcher.calls == [
        {"component_id": "CMP-001", "k": 5},
        {"component_id": "CMP-002", "k": 5},
    ]

    assert set(update) == {
        "budget_matches",
        "execution_metadata",
        "trace_events",
    }
    assert update["budget_matches"] == [
        MATCH_1,
        MATCH_2,
        MATCH_3,
    ]
    assert update["budget_matches"][0] is not MATCH_1

    assert update["execution_metadata"] == {
        "graph_version": "session13.v1",
        "requirement_count": 2,
        "component_count": 2,
        "budget_match_count": 3,
    }

    assert update["trace_events"] == [
        {
            "event_type": "budget_matches_retrieved",
            "node": "search_budgets",
            "summary": "Retrieved 3 budget matches for 2 components.",
            "evidence_refs": [
                "CMP-001",
                "CMP-002",
                "BUD-101",
                "BUD-102",
                "BUD-201",
                "DOC-10:CH-101",
                "DOC-11:CH-102",
                "DOC-20:CH-201",
            ],
            "state_delta_keys": [
                "budget_matches",
                "execution_metadata",
                "trace_events",
            ],
        }
    ]

    assert "components" not in update
    assert "transcript" not in update


@pytest.mark.asyncio
async def test_search_budgets_returns_only_new_reducer_items() -> None:
    searcher = FakeBudgetSearcher(
        {
            "CMP-001": [MATCH_2],
        }
    )
    node = build_search_budgets_node(_dependencies(searcher))

    state = _state()
    state["components"] = [deepcopy(COMPONENTS[0])]
    state["budget_matches"] = [deepcopy(MATCH_1)]
    state["execution_metadata"]["component_count"] = 1

    update = await node(state)

    assert update["budget_matches"] == [MATCH_2]
    assert MATCH_1 not in update["budget_matches"]
    assert update["execution_metadata"]["budget_match_count"] == 2


@pytest.mark.asyncio
async def test_search_budgets_passes_component_copy_to_injected_port() -> None:
    class MutatingBudgetSearcher:
        async def search_budgets(
            self,
            *,
            component: dict[str, object],
            k: int,
        ) -> list[dict[str, object]]:
            del k
            component["name"] = "mutated by adapter"
            return [deepcopy(MATCH_1)]

    node = build_search_budgets_node(
        _dependencies(MutatingBudgetSearcher())
    )
    state = _state()
    state["components"] = [deepcopy(COMPONENTS[0])]
    original_state = deepcopy(state)

    await node(state)

    assert state == original_state


@pytest.mark.asyncio
async def test_search_budgets_normalizes_identifiers_and_numeric_values() -> None:
    searcher = FakeBudgetSearcher(
        {
            "CMP-001": [
                {
                    "component_id": "  CMP-001  ",
                    "budget_id": "  BUD-101  ",
                    "reference_component_id": "  AUTH-01  ",
                    "source_document_id": 10,
                    "source_chunk_id": 101,
                    "recorded_hours": 40,
                    "distance": 0,
                    "score": 1,
                    "retrieval_method": "  hybrid  ",
                }
            ]
        }
    )
    node = build_search_budgets_node(_dependencies(searcher))

    state = _state()
    state["components"] = [deepcopy(COMPONENTS[0])]

    update = await node(state)

    assert update["budget_matches"] == [
        {
            "component_id": "CMP-001",
            "budget_id": "BUD-101",
            "reference_component_id": "AUTH-01",
            "source_document_id": "10",
            "source_chunk_id": "101",
            "recorded_hours": 40.0,
            "distance": 0.0,
            "score": 1.0,
            "retrieval_method": "hybrid",
        }
    ]


@pytest.mark.asyncio
async def test_search_budgets_rejects_missing_components_without_calling_port() -> None:
    searcher = FakeBudgetSearcher({})
    node = build_search_budgets_node(_dependencies(searcher))

    state = new_estimation_graph_state(
        transcript="Valid transcript.",
        estimation_id="estimate-missing-components",
    )

    update = await node(state)

    assert searcher.calls == []
    assert update["budget_matches"] == []
    assert update["review_required"] is True
    assert update["execution_metadata"]["budget_match_count"] == 0
    assert update["errors"] == [
        {
            "code": "missing_components",
            "message": "No classified components are available for budget search.",
            "node": "search_budgets",
            "severity": "error",
        }
    ]
    assert update["trace_events"][0]["event_type"] == "components_unavailable"


@pytest.mark.asyncio
async def test_search_budgets_preserves_valid_matches_and_flags_missing_evidence() -> None:
    searcher = FakeBudgetSearcher(
        {
            "CMP-001": [MATCH_1],
            "CMP-002": [],
        }
    )
    node = build_search_budgets_node(_dependencies(searcher))

    update = await node(_state())

    assert update["budget_matches"] == [MATCH_1]
    assert update["review_required"] is True
    assert update["execution_metadata"]["budget_match_count"] == 1
    assert update["errors"] == [
        {
            "code": "missing_budget_matches",
            "message": (
                "No budget references were found for components: CMP-002."
            ),
            "node": "search_budgets",
            "severity": "warning",
        }
    ]
    assert update["trace_events"][0]["event_type"] == (
        "budget_matches_retrieved_with_gaps"
    )
    assert update["trace_events"][0]["summary"] == (
        "Retrieved 1 budget match for 2 components with 1 evidence gap."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_match",
    [
        {
            **MATCH_1,
            "component_id": "CMP-999",
        },
        {
            **MATCH_1,
            "budget_id": "",
        },
        {
            **MATCH_1,
            "reference_component_id": "   ",
        },
        {
            **MATCH_1,
            "source_document_id": "",
        },
        {
            **MATCH_1,
            "source_chunk_id": "",
        },
        {
            **MATCH_1,
            "recorded_hours": 0,
        },
        {
            **MATCH_1,
            "recorded_hours": -1,
        },
        {
            **MATCH_1,
            "recorded_hours": float("nan"),
        },
        {
            **MATCH_1,
            "distance": -0.1,
        },
        {
            **MATCH_1,
            "score": float("inf"),
        },
        {
            **MATCH_1,
            "retrieval_method": "",
        },
    ],
)
async def test_search_budgets_fails_closed_for_invalid_component_evidence(
    invalid_match: dict[str, object],
) -> None:
    searcher = FakeBudgetSearcher(
        {
            "CMP-001": [invalid_match],
            "CMP-002": [MATCH_3],
        }
    )
    node = build_search_budgets_node(_dependencies(searcher))

    update = await node(_state())

    assert update["budget_matches"] == [MATCH_3]
    assert update["review_required"] is True
    assert update["execution_metadata"]["budget_match_count"] == 1
    assert update["errors"] == [
        {
            "code": "invalid_budget_matches",
            "message": (
                "Budget search returned invalid provenance "
                "for components: CMP-001."
            ),
            "node": "search_budgets",
            "severity": "error",
        }
    ]
    assert update["trace_events"][0]["event_type"] == (
        "budget_matches_retrieved_with_gaps"
    )


@pytest.mark.asyncio
async def test_search_budgets_rejects_duplicate_provenance_for_component() -> None:
    searcher = FakeBudgetSearcher(
        {
            "CMP-001": [MATCH_1, deepcopy(MATCH_1)],
            "CMP-002": [MATCH_3],
        }
    )
    node = build_search_budgets_node(_dependencies(searcher))

    update = await node(_state())

    assert update["budget_matches"] == [MATCH_3]
    assert update["review_required"] is True
    assert update["errors"][0]["code"] == "invalid_budget_matches"


@pytest.mark.asyncio
async def test_search_budgets_propagates_operational_failure() -> None:
    class FailingBudgetSearcher:
        async def search_budgets(
            self,
            *,
            component: object,
            k: int,
        ) -> list[dict[str, object]]:
            del component, k
            raise RuntimeError("retrieval unavailable")

    node = build_search_budgets_node(
        _dependencies(FailingBudgetSearcher())
    )

    with pytest.raises(RuntimeError, match="retrieval unavailable"):
        await node(_state())
