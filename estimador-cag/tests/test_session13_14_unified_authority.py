from __future__ import annotations

import pytest
from langgraph.types import Command

from app.generation.graph.unified_build import _human_gate_to_supervisor


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
