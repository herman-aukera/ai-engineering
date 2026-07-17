"""Deterministic context normalization before the estimation graph."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping

from app.generation.graph.review_state import ReviewedEstimationGraphState

ReformulationNode = Callable[
    [ReviewedEstimationGraphState], Awaitable[ReviewedEstimationGraphState]
]


def build_reformulate_request_node() -> ReformulationNode:
    """Create one stable, auditable brief without model-authored scope."""

    async def reformulate(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        context = state.get("project_context", {})
        if not isinstance(context, Mapping):
            context = {}
        transcript = str(context.get("transcript") or state.get("transcript") or "").strip()
        project_type = str(context.get("project_type") or "unspecified")
        constraints = [str(value) for value in context.get("constraints", [])]
        criteria = [str(value) for value in context.get("acceptance_criteria", [])]
        brief = "\n".join(
            (
                f"Project type: {project_type}",
                f"Request: {transcript}",
                "Constraints: " + ("; ".join(constraints) if constraints else "none supplied"),
                "Acceptance criteria: " + ("; ".join(criteria) if criteria else "none supplied"),
            )
        )
        return {
            "transcript": brief,
            "reformulated_request": brief,
            "trace_events": [
                {
                    "event_type": "request_reformulated",
                    "node": "reformulate_request",
                    "summary": "Normalized project context into the canonical graph brief.",
                    "evidence_refs": [],
                    "state_delta_keys": ["reformulated_request", "trace_events"],
                }
            ],
        }

    return reformulate
