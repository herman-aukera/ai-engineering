from __future__ import annotations

from copy import deepcopy

import pytest

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.nodes.classify_components import (
    build_classify_components_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.state import new_estimation_graph_state

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
        "category": "backend",
        "requirement_ids": ["REQ-002"],
    },
]


def _dependencies(
    component_classifier: object,
) -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor([]),
        component_classifier=component_classifier,
        budget_searcher=FakeBudgetSearcher({}),
        search_k=5,
    )


def _state() -> dict[str, object]:
    state = new_estimation_graph_state(
        transcript="JWT authentication and audit logging are required.",
        estimation_id="estimate-123",
    )
    state["requirements"] = deepcopy(REQUIREMENTS)
    state["execution_metadata"] = {
        "graph_version": "session13.v1",
        "requirement_count": 2,
    }
    return state


@pytest.mark.asyncio
async def test_classify_components_returns_partial_update_without_mutation() -> None:
    classifier = FakeComponentClassifier(COMPONENTS)
    node = build_classify_components_node(_dependencies(classifier))

    state = _state()
    original_state = deepcopy(state)

    update = await node(state)

    assert state == original_state
    assert classifier.calls == [REQUIREMENTS]
    assert classifier.calls[0] is not state["requirements"]

    assert set(update) == {
        "components",
        "execution_metadata",
        "trace_events",
    }

    assert update["components"] == COMPONENTS
    assert update["components"] is not COMPONENTS
    assert update["components"][0] is not COMPONENTS[0]

    assert update["execution_metadata"] == {
        "graph_version": "session13.v1",
        "requirement_count": 2,
        "component_count": 2,
    }

    assert update["trace_events"] == [
        {
            "event_type": "components_classified",
            "node": "classify_components",
            "summary": "Classified 2 implementation components.",
            "evidence_refs": [
                "CMP-001",
                "CMP-002",
                "REQ-001",
                "REQ-002",
            ],
            "state_delta_keys": [
                "components",
                "execution_metadata",
                "trace_events",
            ],
        }
    ]

    assert "requirements" not in update
    assert "transcript" not in update


@pytest.mark.asyncio
async def test_classify_components_normalizes_whitespace() -> None:
    classifier = FakeComponentClassifier(
        [
            {
                "component_id": "  CMP-001  ",
                "name": "  JWT authentication  ",
                "category": "  backend  ",
                "requirement_ids": ["  REQ-001  "],
            },
            {
                "component_id": "  CMP-002  ",
                "name": "  Audit logging  ",
                "category": "  observability  ",
                "requirement_ids": ["  REQ-002  "],
            },
        ]
    )
    node = build_classify_components_node(_dependencies(classifier))

    update = await node(_state())

    assert update["components"] == [
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


@pytest.mark.asyncio
async def test_classify_components_rejects_missing_requirements_without_calling_port() -> None:
    classifier = FakeComponentClassifier(COMPONENTS)
    node = build_classify_components_node(_dependencies(classifier))

    state = new_estimation_graph_state(
        transcript="Valid transcript.",
        estimation_id="estimate-missing-requirements",
    )

    update = await node(state)

    assert classifier.calls == []
    assert update["components"] == []
    assert update["review_required"] is True
    assert update["execution_metadata"]["component_count"] == 0
    assert update["errors"] == [
        {
            "code": "missing_requirements",
            "message": "No structured requirements are available for classification.",
            "node": "classify_components",
            "severity": "error",
        }
    ]
    assert update["trace_events"][0]["event_type"] == "requirements_unavailable"


@pytest.mark.asyncio
async def test_classify_components_marks_empty_result_for_review() -> None:
    classifier = FakeComponentClassifier([])
    node = build_classify_components_node(_dependencies(classifier))

    update = await node(_state())

    assert update["components"] == []
    assert update["review_required"] is True
    assert update["execution_metadata"]["component_count"] == 0
    assert update["errors"] == [
        {
            "code": "no_components",
            "message": "No implementation components were classified.",
            "node": "classify_components",
            "severity": "warning",
        }
    ]
    assert update["trace_events"][0]["event_type"] == "components_missing"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_components",
    [
        [
            {
                "component_id": "",
                "name": "JWT authentication",
                "category": "backend",
                "requirement_ids": ["REQ-001"],
            }
        ],
        [
            {
                "component_id": "CMP-001",
                "name": "",
                "category": "backend",
                "requirement_ids": ["REQ-001"],
            }
        ],
        [
            {
                "component_id": "CMP-001",
                "name": "JWT authentication",
                "category": "",
                "requirement_ids": ["REQ-001"],
            }
        ],
        [
            {
                "component_id": "CMP-001",
                "name": "JWT authentication",
                "category": "backend",
                "requirement_ids": [],
            }
        ],
        [
            {
                "component_id": "CMP-001",
                "name": "JWT authentication",
                "category": "backend",
                "requirement_ids": ["REQ-001"],
            },
            {
                "component_id": "CMP-001",
                "name": "Duplicate component identifier",
                "category": "backend",
                "requirement_ids": ["REQ-002"],
            },
        ],
        [
            {
                "component_id": "CMP-001",
                "name": "JWT authentication",
                "category": "backend",
                "requirement_ids": ["REQ-001", "REQ-001"],
            }
        ],
    ],
)
async def test_classify_components_fails_closed_for_invalid_output(
    invalid_components: list[dict[str, object]],
) -> None:
    classifier = FakeComponentClassifier(invalid_components)
    node = build_classify_components_node(_dependencies(classifier))

    update = await node(_state())

    assert update["components"] == []
    assert update["review_required"] is True
    assert update["execution_metadata"]["component_count"] == 0
    assert update["errors"] == [
        {
            "code": "invalid_components",
            "message": "Component classification returned an invalid structured result.",
            "node": "classify_components",
            "severity": "error",
        }
    ]
    assert update["trace_events"][0]["event_type"] == "components_invalid"


@pytest.mark.asyncio
async def test_classify_components_rejects_unknown_requirement_links() -> None:
    classifier = FakeComponentClassifier(
        [
            {
                "component_id": "CMP-001",
                "name": "JWT authentication",
                "category": "backend",
                "requirement_ids": ["REQ-999"],
            }
        ]
    )
    node = build_classify_components_node(_dependencies(classifier))

    update = await node(_state())

    assert update["components"] == []
    assert update["review_required"] is True
    assert update["errors"][0]["code"] == "invalid_components"
    assert update["trace_events"][0]["event_type"] == "components_invalid"


@pytest.mark.asyncio
async def test_classify_components_preserves_valid_components_but_flags_unmapped_requirements() -> None:
    classifier = FakeComponentClassifier(
        [
            {
                "component_id": "CMP-001",
                "name": "JWT authentication",
                "category": "backend",
                "requirement_ids": ["REQ-001"],
            }
        ]
    )
    node = build_classify_components_node(_dependencies(classifier))

    update = await node(_state())

    assert update["components"] == [
        {
            "component_id": "CMP-001",
            "name": "JWT authentication",
            "category": "backend",
            "requirement_ids": ["REQ-001"],
        }
    ]
    assert update["review_required"] is True
    assert update["execution_metadata"]["component_count"] == 1
    assert update["errors"] == [
        {
            "code": "unmapped_requirements",
            "message": "Some requirements were not assigned to a component: REQ-002.",
            "node": "classify_components",
            "severity": "warning",
        }
    ]
    assert update["trace_events"] == [
        {
            "event_type": "components_classified_with_gaps",
            "node": "classify_components",
            "summary": (
                "Classified 1 implementation component with "
                "1 unmapped requirement."
            ),
            "evidence_refs": ["CMP-001", "REQ-001", "REQ-002"],
            "state_delta_keys": [
                "components",
                "review_required",
                "errors",
                "execution_metadata",
                "trace_events",
            ],
        }
    ]


@pytest.mark.asyncio
async def test_classify_components_propagates_operational_failure() -> None:
    class FailingComponentClassifier:
        async def classify_components(
            self,
            *,
            requirements: object,
        ) -> list[dict[str, object]]:
            del requirements
            raise RuntimeError("classifier unavailable")

    node = build_classify_components_node(
        _dependencies(FailingComponentClassifier())
    )

    with pytest.raises(RuntimeError, match="classifier unavailable"):
        await node(_state())
