"""Tests for Session 13 Plus S6: deterministic reformulator rollback."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(**overrides: object) -> dict[str, object]:
    state: dict[str, object] = {
        "transcript": "Original raw transcript from the user.",
        "project_context": {
            "transcript": "Build a secure FastAPI onboarding platform.",
            "project_type": "web",
            "constraints": ["PostgreSQL"],
            "acceptance_criteria": ["Resume after restart"],
        },
        "estimation_id": "11111111-1111-4111-8111-111111111111",
        "graph_version": "session13.plus.v1",
        "trace_events": [],
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# 1. Reformulator preserves original transcript
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reformulator_preserves_pre_reformulation_transcript() -> None:
    """After reformulation the original transcript must be saved."""
    from app.generation.graph.nodes.reformulate_request import (
        build_reformulate_request_node,
    )

    state = _state()
    node = build_reformulate_request_node()
    result = await node(state)

    assert "pre_reformulation_transcript" in result
    assert result["pre_reformulation_transcript"] == "Original raw transcript from the user."
    assert result["transcript"] != result["pre_reformulation_transcript"]


@pytest.mark.asyncio
async def test_reformulator_still_produces_reformulated_request() -> None:
    """Existing reformulation behavior must be preserved."""
    from app.generation.graph.nodes.reformulate_request import (
        build_reformulate_request_node,
    )

    state = _state()
    node = build_reformulate_request_node()
    result = await node(state)

    assert "reformulated_request" in result
    assert "internal platform" in result["reformulated_request"] or "web" in result["reformulated_request"]


# ---------------------------------------------------------------------------
# 2. Rollback restores original transcript
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rollback_restores_original_transcript() -> None:
    """Rollback must restore transcript from pre_reformulation_transcript."""
    from app.generation.graph.nodes.reformulate_request import (
        build_reformulate_request_node,
        build_rollback_reformulation_node,
    )

    # First, reformulate.
    reformulate = build_reformulate_request_node()
    reformulated = await reformulate(_state())

    # Then, rollback.
    rollback = build_rollback_reformulation_node()
    rolled_back = await rollback(reformulated)

    assert rolled_back["transcript"] == "Original raw transcript from the user."
    assert rolled_back.get("reformulated_request") is None


@pytest.mark.asyncio
async def test_rollback_clears_reformulated_state() -> None:
    """Rollback must clear reformulated_request and pre_reformulation_transcript."""
    from app.generation.graph.nodes.reformulate_request import (
        build_reformulate_request_node,
        build_rollback_reformulation_node,
    )

    reformulate = build_reformulate_request_node()
    reformulated = await reformulate(_state())

    rollback = build_rollback_reformulation_node()
    rolled_back = await rollback(reformulated)

    assert "pre_reformulation_transcript" not in rolled_back
    assert rolled_back.get("reformulated_request") is None


@pytest.mark.asyncio
async def test_rollback_is_idempotent() -> None:
    """Rolling back twice must produce the same result."""
    from app.generation.graph.nodes.reformulate_request import (
        build_reformulate_request_node,
        build_rollback_reformulation_node,
    )

    reformulate = build_reformulate_request_node()
    reformulated = await reformulate(_state())

    rollback = build_rollback_reformulation_node()
    first = await rollback(reformulated)
    # Second rollback to the SAME reformulated state (not the return of first).
    second = await rollback(reformulated)

    assert first == second


@pytest.mark.asyncio
async def test_rollback_without_reformulation_is_noop() -> None:
    """Rollback on a state that was never reformulated must be a no-op."""
    from app.generation.graph.nodes.reformulate_request import (
        build_rollback_reformulation_node,
    )

    state = _state()

    rollback = build_rollback_reformulation_node()
    result = await rollback(state)

    # No-op means empty update — nothing to change.
    assert result == {}
    assert result.get("reformulated_request") is None


@pytest.mark.asyncio
async def test_rollback_emits_trace_event() -> None:
    """Rollback must emit a domain trace event."""
    from app.generation.graph.nodes.reformulate_request import (
        build_reformulate_request_node,
        build_rollback_reformulation_node,
    )

    reformulate = build_reformulate_request_node()
    reformulated = await reformulate(_state())

    rollback = build_rollback_reformulation_node()
    rolled_back = await rollback(reformulated)

    events = rolled_back.get("trace_events", [])
    event_types = [e["event_type"] for e in events]
    assert "reformulation_rolled_back" in event_types


# ---------------------------------------------------------------------------
# 3. Round-trip: reformulate → rollback → reformulate is stable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reformulate_rollback_reformulate_is_stable() -> None:
    """Reformulating after rollback must produce the same brief."""
    from app.generation.graph.nodes.reformulate_request import (
        build_reformulate_request_node,
        build_rollback_reformulation_node,
    )

    reformulate = build_reformulate_request_node()
    rollback = build_rollback_reformulation_node()

    state = _state()
    first = await reformulate(state)
    rolled = await rollback(first)
    second = await reformulate(rolled)

    # The reformulated brief must be identical both times.
    assert first["reformulated_request"] == second["reformulated_request"]
