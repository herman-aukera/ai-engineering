from __future__ import annotations

from copy import deepcopy

import pytest

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.nodes.extract_requirements import (
    build_extract_requirements_node,
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


def _dependencies(
    requirement_extractor: object,
) -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=requirement_extractor,
        component_classifier=FakeComponentClassifier([]),
        budget_searcher=FakeBudgetSearcher({}),
        search_k=5,
    )


@pytest.mark.asyncio
async def test_extract_requirements_returns_partial_update_without_mutation() -> None:
    extractor = FakeRequirementExtractor(REQUIREMENTS)
    node = build_extract_requirements_node(_dependencies(extractor))

    state = new_estimation_graph_state(
        transcript="The client needs JWT authentication and audit logging.",
        estimation_id="estimate-123",
    )
    state["execution_metadata"] = {
        "graph_version": "session13.v1",
    }
    original_state = deepcopy(state)

    update = await node(state)

    assert state == original_state
    assert extractor.calls == [
        "The client needs JWT authentication and audit logging."
    ]

    assert set(update) == {
        "requirements",
        "execution_metadata",
        "trace_events",
    }
    assert update["requirements"] == REQUIREMENTS
    assert update["requirements"] is not REQUIREMENTS
    assert update["requirements"][0] is not REQUIREMENTS[0]

    assert update["execution_metadata"] == {
        "graph_version": "session13.v1",
        "requirement_count": 2,
    }

    assert update["trace_events"] == [
        {
            "event_type": "requirements_extracted",
            "node": "extract_requirements",
            "summary": "Extracted 2 structured requirements.",
            "evidence_refs": ["REQ-001", "REQ-002"],
            "state_delta_keys": [
                "requirements",
                "execution_metadata",
                "trace_events",
            ],
        }
    ]

    assert "transcript" not in update
    assert "estimation_id" not in update


@pytest.mark.asyncio
async def test_extract_requirements_normalizes_surrounding_whitespace() -> None:
    extractor = FakeRequirementExtractor(
        [
            {
                "requirement_id": "  REQ-001  ",
                "text": "  Users authenticate with JWT.  ",
            }
        ]
    )
    node = build_extract_requirements_node(_dependencies(extractor))
    state = new_estimation_graph_state(
        transcript="Valid transcript.",
        estimation_id="estimate-123",
    )

    update = await node(state)

    assert update["requirements"] == [
        {
            "requirement_id": "REQ-001",
            "text": "Users authenticate with JWT.",
        }
    ]


@pytest.mark.asyncio
async def test_extract_requirements_marks_empty_result_for_review() -> None:
    extractor = FakeRequirementExtractor([])
    node = build_extract_requirements_node(_dependencies(extractor))
    state = new_estimation_graph_state(
        transcript="A transcript that produced no structured requirements.",
        estimation_id="estimate-empty",
    )

    update = await node(state)

    assert update["requirements"] == []
    assert update["review_required"] is True
    assert update["execution_metadata"]["requirement_count"] == 0
    assert update["errors"] == [
        {
            "code": "no_requirements",
            "message": "No structured requirements were extracted.",
            "node": "extract_requirements",
            "severity": "warning",
        }
    ]
    assert update["trace_events"][0]["event_type"] == "requirements_missing"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_requirements",
    [
        [
            {
                "requirement_id": "",
                "text": "Valid text.",
            }
        ],
        [
            {
                "requirement_id": "REQ-001",
                "text": "",
            }
        ],
        [
            {
                "requirement_id": "REQ-001",
                "text": "First requirement.",
            },
            {
                "requirement_id": "REQ-001",
                "text": "Duplicate identifier.",
            },
        ],
    ],
)
async def test_extract_requirements_fails_closed_for_invalid_output(
    invalid_requirements: list[dict[str, str]],
) -> None:
    extractor = FakeRequirementExtractor(invalid_requirements)
    node = build_extract_requirements_node(_dependencies(extractor))
    state = new_estimation_graph_state(
        transcript="Valid transcript.",
        estimation_id="estimate-invalid",
    )

    update = await node(state)

    assert update["requirements"] == []
    assert update["review_required"] is True
    assert update["execution_metadata"]["requirement_count"] == 0
    assert update["errors"] == [
        {
            "code": "invalid_requirements",
            "message": "Requirement extraction returned an invalid structured result.",
            "node": "extract_requirements",
            "severity": "error",
        }
    ]
    assert update["trace_events"][0]["event_type"] == "requirements_invalid"


@pytest.mark.asyncio
async def test_extract_requirements_rejects_missing_transcript_without_calling_port() -> None:
    extractor = FakeRequirementExtractor(REQUIREMENTS)
    node = build_extract_requirements_node(_dependencies(extractor))

    update = await node(
        {
            "estimation_id": "estimate-missing-transcript",
            "execution_metadata": {},
        }
    )

    assert extractor.calls == []
    assert update["requirements"] == []
    assert update["review_required"] is True
    assert update["errors"][0]["code"] == "missing_transcript"
    assert update["trace_events"][0]["event_type"] == "transcript_missing"


@pytest.mark.asyncio
async def test_extract_requirements_propagates_operational_failure() -> None:
    class FailingRequirementExtractor:
        async def extract_requirements(
            self,
            *,
            transcript: str,
        ) -> list[dict[str, str]]:
            del transcript
            raise RuntimeError("provider unavailable")

    node = build_extract_requirements_node(
        _dependencies(FailingRequirementExtractor())
    )
    state = new_estimation_graph_state(
        transcript="Valid transcript.",
        estimation_id="estimate-provider-failure",
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await node(state)
