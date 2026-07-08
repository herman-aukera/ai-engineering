"""
Session 12 retrieval trace artifact helpers.

This module writes a second trace artifact showing the same fake-provider loop
with injected retrieval observations.
"""

from __future__ import annotations

from pathlib import Path

from app.generation.agentic.agent_schemas import AgentRunResult
from app.generation.agentic.trace_artifacts import write_trace_artifact


def write_fake_retrieval_trace_artifact(
    *,
    output_path: Path,
    scenario_id: str,
    result: AgentRunResult,
) -> None:
    """Write the fake-provider trace with retrieval observations."""

    write_trace_artifact(
        output_path=output_path,
        scenario_id=scenario_id,
        request_provider="fake+retrieval",
        result=result,
    )
