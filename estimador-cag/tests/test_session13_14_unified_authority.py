from __future__ import annotations

import pytest
from langgraph.types import Command

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
)
from app.generation.graph.nodes.extract_requirements import (
    build_extract_requirements_node,
)
from app.generation.graph.nodes.reformulate_request import (
    build_reformulate_request_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.unified_build import (
    _human_gate_to_supervisor,
    _phase_marker,
    _restore_source_transcript_node,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("human_status", "base_destination"),
    [
        ("approved", "proposal"),
        ("adjusted", "proposal"),
        ("rejected", "finalize"),
    ],
)
async def test_human_gate_cannot_bypass_unified_supervisor(
    human_status: str,
    base_destination: str,
) -> None:
    async def base_gate(_state):
        return Command(
            goto=base_destination,
            update={
                "human_review_status": human_status,
                "human_review_revision": 2,
            },
        )

    command = await _human_gate_to_supervisor(base_gate)({})

    assert command.goto == "supervisor"
    assert command.update == {
        "human_review_status": human_status,
        "human_review_revision": 2,
        "unified_phase": "human_review",
    }


@pytest.mark.asyncio
async def test_unified_reformulation_preserves_request_identity() -> None:
    source = "Build an auditable reporting API."

    update = await build_reformulate_request_node()(
        {
            "transcript": source,
            "graph_version": "session13_14_plus.unified.v1",
            "project_context": {
                "project_type": "backend",
                "constraints": ["GDPR"],
                "acceptance_criteria": ["Auditable"],
            },
        }
    )

    assert update["transcript"] == source
    assert update["pre_reformulation_transcript"] == source
    assert update["reformulated_request"] != source
    assert f"Request: {source}" in update["reformulated_request"]


@pytest.mark.asyncio
async def test_reviewed_reformulation_retains_historical_working_brief() -> None:
    source = "Build an auditable reporting API."

    update = await build_reformulate_request_node()(
        {
            "transcript": source,
            "graph_version": "session13.reviewed.v3",
            "project_context": {},
        }
    )

    assert update["transcript"] == update["reformulated_request"]
    assert update["transcript"] != source
    assert update["pre_reformulation_transcript"] == source


class CapturingRequirementExtractor:
    def __init__(self) -> None:
        self.transcripts: list[str] = []

    async def extract_requirements(
        self,
        *,
        transcript: str,
    ) -> list[dict[str, str]]:
        self.transcripts.append(transcript)
        return [
            {
                "requirement_id": "REQ-1",
                "text": "Provide an auditable API.",
            }
        ]


@pytest.mark.asyncio
async def test_requirement_extraction_uses_canonical_brief() -> None:
    extractor = CapturingRequirementExtractor()
    node = build_extract_requirements_node(
        GraphNodeDependencies(
            requirement_extractor=extractor,
            component_classifier=FakeComponentClassifier([]),
            budget_searcher=FakeBudgetSearcher({}),
        )
    )

    update = await node(
        {
            "transcript": "Original source request",
            "reformulated_request": "Canonical structure brief",
        }
    )

    assert extractor.transcripts == ["Canonical structure brief"]
    assert update["requirements"][0]["requirement_id"] == "REQ-1"


@pytest.mark.asyncio
async def test_structure_phase_restores_exact_source_transcript() -> None:
    update = await _restore_source_transcript_node()(
        {
            "transcript": "Canonical structure brief",
            "pre_reformulation_transcript": "Original source request",
        }
    )

    assert update["transcript"] == "Original source request"
    assert update["trace_events"][0]["event_type"] == (
        "source_transcript_restored"
    )


@pytest.mark.asyncio
async def test_structure_completion_restores_parent_checkpoint_identity() -> None:
    command = await _phase_marker(
        flag="unified_structure_completed",
        phase="structure",
    )(
        {
            "transcript": "Canonical structure brief",
            "pre_reformulation_transcript": "Original source request",
        }
    )

    assert command.goto == "supervisor"
    assert command.update["unified_structure_completed"] is True
    assert command.update["transcript"] == "Original source request"


@pytest.mark.asyncio
async def test_structure_phase_rejects_missing_source_transcript() -> None:
    with pytest.raises(ValueError, match="lost the source transcript"):
        await _restore_source_transcript_node()(
            {"transcript": "Canonical structure brief"}
        )
