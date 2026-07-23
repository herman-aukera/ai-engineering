"""
Session 12 trace artifact helpers.

These helpers convert an AgentRunResult into committed JSON evidence that can be
used by tests, Streamlit diagnostics, and live-provider comparisons.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.generation.agentic.agent_schemas import AgentRunResult

TRACE_SCHEMA_VERSION = "session12.agent_trace.v1"


def build_trace_artifact(
    *,
    scenario_id: str,
    request_provider: str,
    result: AgentRunResult,
) -> dict[str, Any]:
    """Build a deterministic, JSON-serializable trace artifact."""

    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "scenario_id": scenario_id,
        "provider": result.provider,
        "request_provider": request_provider,
        "model": result.model,
        "terminated": result.terminated,
        "estimate": result.estimate.model_dump(),
        "validation": result.validation.model_dump() if result.validation else None,
        "trace": [item.model_dump() for item in result.trace],
    }


def write_trace_artifact(
    *,
    output_path: Path,
    scenario_id: str,
    request_provider: str,
    result: AgentRunResult,
) -> None:
    """Write a pretty JSON trace artifact with stable ordering."""

    artifact = build_trace_artifact(
        scenario_id=scenario_id,
        request_provider=request_provider,
        result=result,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
