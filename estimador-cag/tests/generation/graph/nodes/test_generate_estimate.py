from __future__ import annotations

from copy import deepcopy

import pytest

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.nodes.generate_estimate import (
    build_generate_estimate_node,
)
from app.generation.graph.ports import (
    EstimationPolicy,
    GraphNodeDependencies,
)
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


def _match(
    *,
    component_id: str,
    budget_id: str,
    reference_component_id: str,
    document_id: str,
    chunk_id: str,
    hours: float | None,
) -> dict[str, object]:
    return {
        "component_id": component_id,
        "budget_id": budget_id,
        "reference_component_id": reference_component_id,
        "source_document_id": document_id,
        "source_chunk_id": chunk_id,
        "recorded_hours": hours,
        "distance": 0.1,
        "score": 0.9,
        "retrieval_method": "hybrid",
    }


MATCHES = [
    _match(
        component_id="CMP-001",
        budget_id="BUD-101",
        reference_component_id="AUTH-01",
        document_id="DOC-10",
        chunk_id="CH-101",
        hours=32.0,
    ),
    _match(
        component_id="CMP-001",
        budget_id="BUD-102",
        reference_component_id="AUTH-02",
        document_id="DOC-11",
        chunk_id="CH-102",
        hours=40.0,
    ),
    _match(
        component_id="CMP-001",
        budget_id="BUD-103",
        reference_component_id="AUTH-03",
        document_id="DOC-12",
        chunk_id="CH-103",
        hours=48.0,
    ),
    _match(
        component_id="CMP-002",
        budget_id="BUD-201",
        reference_component_id="AUDIT-01",
        document_id="DOC-20",
        chunk_id="CH-201",
        hours=24.0,
    ),
]


def _dependencies(
    policy: EstimationPolicy | None = None,
) -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor([]),
        component_classifier=FakeComponentClassifier([]),
        budget_searcher=FakeBudgetSearcher({}),
        estimation_policy=policy or EstimationPolicy(),
    )


def _state(
    *,
    components: list[dict[str, object]] | None = None,
    matches: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    state = new_estimation_graph_state(
        transcript="JWT authentication and audit logging are required.",
        estimation_id="estimate-123",
    )
    state["components"] = deepcopy(
        COMPONENTS if components is None else components
    )
    state["budget_matches"] = deepcopy(
        MATCHES if matches is None else matches
    )
    state["execution_metadata"] = {
        "graph_version": "session13.v1",
        "requirement_count": 2,
        "component_count": len(state["components"]),
        "budget_match_count": len(state["budget_matches"]),
    }
    return state


@pytest.mark.parametrize(
    "policy",
    [
        EstimationPolicy(minimum_grounded_samples=2),
    ],
)
def test_default_policy_is_constructible(
    policy: EstimationPolicy,
) -> None:
    assert policy.minimum_grounded_samples == 2
    assert policy.low_confidence_dispersion_ratio == 0.5
    assert policy.conflict_dispersion_ratio == 0.75


@pytest.mark.parametrize(
    "kwargs",
    [
        {"minimum_grounded_samples": 1},
        {"low_confidence_dispersion_ratio": -0.1},
        {
            "low_confidence_dispersion_ratio": 0.5,
            "conflict_dispersion_ratio": 0.5,
        },
        {
            "low_confidence_dispersion_ratio": 0.8,
            "conflict_dispersion_ratio": 0.7,
        },
    ],
)
def test_policy_rejects_invalid_thresholds(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        EstimationPolicy(**kwargs)


@pytest.mark.asyncio
async def test_generate_estimate_returns_deterministic_partial_update() -> None:
    node = build_generate_estimate_node(_dependencies())
    state = _state()
    original_state = deepcopy(state)

    update = await node(state)

    assert state == original_state
    assert set(update) == {
        "component_estimates",
        "review_required",
        "errors",
        "execution_metadata",
        "trace_events",
    }

    assert update["component_estimates"] == [
        {
            "component_id": "CMP-001",
            "name": "JWT authentication",
            "hours": 40.0,
            "grounding_status": "grounded",
            "reference_budget_ids": [
                "BUD-101",
                "BUD-102",
                "BUD-103",
            ],
            "reference_component_ids": [
                "AUTH-01",
                "AUTH-02",
                "AUTH-03",
            ],
            "source_hours": [32.0, 40.0, 48.0],
            "source_range_low": 32.0,
            "source_range_high": 48.0,
            "dispersion": 0.4,
            "confidence": 0.8,
            "derivation_method": "median_recorded_hours",
            "review_reasons": [],
        },
        {
            "component_id": "CMP-002",
            "name": "Audit logging",
            "hours": 24.0,
            "grounding_status": "low_confidence",
            "reference_budget_ids": ["BUD-201"],
            "reference_component_ids": ["AUDIT-01"],
            "source_hours": [24.0],
            "source_range_low": 24.0,
            "source_range_high": 24.0,
            "dispersion": 0.0,
            "confidence": 0.5,
            "derivation_method": "median_recorded_hours",
            "review_reasons": [
                "Only one recorded-hours reference was available."
            ],
        },
    ]

    assert update["review_required"] is True
    assert update["errors"] == [
        {
            "code": "low_confidence_component_estimate",
            "message": (
                "Component CMP-002 has low-confidence budget evidence."
            ),
            "node": "generate_estimate",
            "severity": "warning",
        }
    ]
    assert update["execution_metadata"] == {
        "graph_version": "session13.v1",
        "requirement_count": 2,
        "component_count": 2,
        "budget_match_count": 4,
        "component_estimate_count": 2,
    }
    assert update["trace_events"] == [
        {
            "event_type": "component_estimates_generated_with_review",
            "node": "generate_estimate",
            "summary": (
                "Generated 2 component estimates; "
                "1 requires review."
            ),
            "evidence_refs": [
                "CMP-001",
                "CMP-002",
                "BUD-101",
                "BUD-102",
                "BUD-103",
                "BUD-201",
            ],
            "state_delta_keys": [
                "component_estimates",
                "review_required",
                "errors",
                "execution_metadata",
                "trace_events",
            ],
        }
    ]

    assert "components" not in update
    assert "budget_matches" not in update


@pytest.mark.asyncio
async def test_generate_estimate_returns_grounded_result_without_review() -> None:
    matches = [
        *MATCHES[:3],
        _match(
            component_id="CMP-002",
            budget_id="BUD-201",
            reference_component_id="AUDIT-01",
            document_id="DOC-20",
            chunk_id="CH-201",
            hours=20.0,
        ),
        _match(
            component_id="CMP-002",
            budget_id="BUD-202",
            reference_component_id="AUDIT-02",
            document_id="DOC-21",
            chunk_id="CH-202",
            hours=24.0,
        ),
        _match(
            component_id="CMP-002",
            budget_id="BUD-203",
            reference_component_id="AUDIT-03",
            document_id="DOC-22",
            chunk_id="CH-203",
            hours=28.0,
        ),
    ]

    node = build_generate_estimate_node(_dependencies())
    update = await node(_state(matches=matches))

    assert [
        item["grounding_status"]
        for item in update["component_estimates"]
    ] == ["grounded", "grounded"]
    assert "review_required" not in update
    assert "errors" not in update
    assert update["trace_events"][0]["event_type"] == (
        "component_estimates_generated"
    )
    assert update["trace_events"][0]["summary"] == (
        "Generated 2 grounded component estimates."
    )


@pytest.mark.asyncio
async def test_generate_estimate_does_not_invent_hours_without_data() -> None:
    no_hours_match = _match(
        component_id="CMP-001",
        budget_id="BUD-101",
        reference_component_id="AUTH-01",
        document_id="DOC-10",
        chunk_id="CH-101",
        hours=None,
    )

    node = build_generate_estimate_node(_dependencies())
    update = await node(
        _state(
            components=[COMPONENTS[0]],
            matches=[no_hours_match],
        )
    )

    assert update["component_estimates"] == [
        {
            "component_id": "CMP-001",
            "name": "JWT authentication",
            "hours": None,
            "grounding_status": "no_data",
            "reference_budget_ids": ["BUD-101"],
            "reference_component_ids": ["AUTH-01"],
            "source_hours": [],
            "source_range_low": None,
            "source_range_high": None,
            "dispersion": None,
            "confidence": 0.0,
            "derivation_method": "no_recorded_hours",
            "review_reasons": [
                "No recorded hours were available."
            ],
        }
    ]
    assert update["review_required"] is True
    assert update["errors"][0]["code"] == (
        "missing_component_evidence"
    )


@pytest.mark.asyncio
async def test_generate_estimate_flags_conflicting_evidence() -> None:
    matches = [
        _match(
            component_id="CMP-001",
            budget_id="BUD-101",
            reference_component_id="AUTH-01",
            document_id="DOC-10",
            chunk_id="CH-101",
            hours=10.0,
        ),
        _match(
            component_id="CMP-001",
            budget_id="BUD-102",
            reference_component_id="AUTH-02",
            document_id="DOC-11",
            chunk_id="CH-102",
            hours=40.0,
        ),
    ]

    node = build_generate_estimate_node(_dependencies())
    update = await node(
        _state(
            components=[COMPONENTS[0]],
            matches=matches,
        )
    )

    estimate = update["component_estimates"][0]

    assert estimate["hours"] == 25.0
    assert estimate["source_range_low"] == 10.0
    assert estimate["source_range_high"] == 40.0
    assert estimate["dispersion"] == 1.2
    assert estimate["confidence"] == 0.25
    assert estimate["grounding_status"] == "conflict"
    assert estimate["review_reasons"] == [
        (
            "Reference-hour dispersion is at or above "
            "the conflict threshold."
        )
    ]
    assert update["errors"][0]["code"] == (
        "conflicting_component_evidence"
    )
    assert update["errors"][0]["severity"] == "error"


@pytest.mark.asyncio
async def test_generate_estimate_rejects_missing_components() -> None:
    node = build_generate_estimate_node(_dependencies())

    state = new_estimation_graph_state(
        transcript="Valid transcript.",
        estimation_id="estimate-missing-components",
    )

    update = await node(state)

    assert update["component_estimates"] == []
    assert update["review_required"] is True
    assert update["errors"] == [
        {
            "code": "missing_components",
            "message": (
                "No classified components are available "
                "for deterministic estimation."
            ),
            "node": "generate_estimate",
            "severity": "error",
        }
    ]
    assert update["trace_events"][0]["event_type"] == (
        "component_estimation_failed"
    )


@pytest.mark.asyncio
async def test_generate_estimate_rejects_duplicate_provenance() -> None:
    duplicated = deepcopy(MATCHES[0])

    node = build_generate_estimate_node(_dependencies())
    update = await node(
        _state(
            components=[COMPONENTS[0]],
            matches=[MATCHES[0], duplicated],
        )
    )

    assert update["component_estimates"] == []
    assert update["review_required"] is True
    assert update["errors"][0]["code"] == (
        "invalid_budget_evidence"
    )


@pytest.mark.asyncio
async def test_generate_estimate_rejects_unknown_component_evidence() -> None:
    unknown = deepcopy(MATCHES[0])
    unknown["component_id"] = "CMP-999"

    node = build_generate_estimate_node(_dependencies())
    update = await node(
        _state(
            components=[COMPONENTS[0]],
            matches=[unknown],
        )
    )

    assert update["component_estimates"] == []
    assert update["review_required"] is True
    assert update["errors"][0]["code"] == (
        "invalid_budget_evidence"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hours",
    [
        0.0,
        -1.0,
        float("nan"),
        float("inf"),
    ],
)
async def test_generate_estimate_rejects_invalid_recorded_hours(
    hours: float,
) -> None:
    invalid = _match(
        component_id="CMP-001",
        budget_id="BUD-101",
        reference_component_id="AUTH-01",
        document_id="DOC-10",
        chunk_id="CH-101",
        hours=hours,
    )

    node = build_generate_estimate_node(_dependencies())
    update = await node(
        _state(
            components=[COMPONENTS[0]],
            matches=[invalid],
        )
    )

    assert update["component_estimates"] == []
    assert update["review_required"] is True
    assert update["errors"][0]["code"] == (
        "invalid_budget_evidence"
    )
