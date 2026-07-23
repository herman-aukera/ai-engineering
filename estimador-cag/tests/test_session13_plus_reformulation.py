from __future__ import annotations

import pytest

from app.generation.graph.nodes.reformulate_request import (
    build_reformulate_request_node,
)


@pytest.mark.asyncio
async def test_context_reformulation_is_deterministic_and_scope_preserving() -> None:
    state = {
        "transcript": "Build an estimator.",
        "project_context": {
            "transcript": "Build an estimator with durable approval gates.",
            "project_type": "internal platform",
            "constraints": ["PostgreSQL", "No model-authored arithmetic"],
            "acceptance_criteria": ["Resume after restart"],
        },
    }
    result = await build_reformulate_request_node()(state)
    brief = result["reformulated_request"]
    assert "internal platform" in brief
    assert "PostgreSQL; No model-authored arithmetic" in brief
    assert "Resume after restart" in brief
    assert result["transcript"] == brief
    assert result["trace_events"][0]["event_type"] == "request_reformulated"
