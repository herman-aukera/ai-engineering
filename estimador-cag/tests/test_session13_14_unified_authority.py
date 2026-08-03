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
from app.generation.graph.nodes.unified_supervisor import (
    build_unified_supervisor_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.unified_build import (
    _human_gate_to_supervisor,
    _phase_marker,
    _restore_source_transcript_node,
)
from app.generation.graph.unified_state import (
    new_unified_estimation_graph_state,
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


def _post_coherence_state(
    *,
    human_review_status: str,
    proposal_completed: bool = False,
):
    state = new_unified_estimation_graph_state(
        transcript="Build an auditable reporting API.",
        estimation_id="EST-HUMAN-ROUTE-001",
    )
    state.update(
        unified_structure_completed=True,
        unified_estimation_completed=True,
        plus_competition_completed=True,
        unified_reliability_completed=True,
        unified_review_policy_completed=True,
        unified_boss_action_completed=True,
        unified_coherence_completed=True,
        unified_proposal_completed=proposal_completed,
        boss_route="final_review",
        status=(
            "validated"
            if human_review_status in {"approved", "adjusted"}
            else "needs_review"
        ),
        review_required=human_review_status == "rejected",
        human_review_status=human_review_status,
        validation={
            "is_coherent": True,
            "status": (
                "validated"
                if human_review_status in {"approved", "adjusted"}
                else "needs_review"
            ),
            "review_required": human_review_status == "rejected",
        },
    )
    return state


@pytest.mark.asyncio
async def test_supervisor_finalizes_rejected_human_decision() -> None:
    command = await build_unified_supervisor_node()(
        _post_coherence_state(human_review_status="rejected")
    )

    assert command.goto == "finalize"
    assert command.update["unified_route_events"][0]["reason_code"] == (
        "human_review_rejected"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("human_status", ["approved", "adjusted"])
async def test_supervisor_routes_authorized_human_decision_to_proposal(
    human_status: str,
) -> None:
    command = await build_unified_supervisor_node()(
        _post_coherence_state(human_review_status=human_status)
    )

    assert command.goto == "proposal"
    assert command.update["unified_route_events"][0]["reason_code"] == (
        "human_review_authorized_proposal"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("human_status", ["approved", "adjusted"])
async def test_supervisor_finalizes_authorized_completed_proposal(
    human_status: str,
) -> None:
    command = await build_unified_supervisor_node()(
        _post_coherence_state(
            human_review_status=human_status,
            proposal_completed=True,
        )
    )

    assert command.goto == "finalize"
    assert command.update["unified_route_events"][0]["reason_code"] == (
        "human_review_authorized_completion"
    )


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
async def test_unified_reformulation_preserves_boundary_whitespace() -> None:
    source = "\n  Build an auditable reporting API.  \n"

    update = await build_reformulate_request_node(
        preserve_source_transcript=True
    )(
        {
            "transcript": source,
            "graph_version": "session13_14_plus.unified.v1",
            "project_context": {},
        }
    )

    assert update["transcript"] == source
    assert update["pre_reformulation_transcript"] == source
    assert "Request: Build an auditable reporting API." in update[
        "reformulated_request"
    ]


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
