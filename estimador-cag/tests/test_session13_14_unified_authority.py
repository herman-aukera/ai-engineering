from __future__ import annotations

import pytest
from langgraph.types import Command

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
