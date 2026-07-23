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
        original_transcript = str(state.get("transcript") or "").strip()
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
            "pre_reformulation_transcript": original_transcript,
            "project_context": dict(context),
            "trace_events": [
                {
                    "event_type": "request_reformulated",
                    "node": "reformulate_request",
                    "summary": "Normalized project context into the canonical graph brief.",
                    "evidence_refs": [],
                    "state_delta_keys": ["reformulated_request", "pre_reformulation_transcript", "trace_events"],
                }
            ],
        }

    return reformulate


def build_rollback_reformulation_node() -> ReformulationNode:
    """Build a node that restores the pre-reformulation transcript.

    When the state carries a ``pre_reformulation_transcript``, the original
    transcript is restored and reformulation fields are cleared.  If the state
    was never reformulated, this is a no-op.
    """

    async def rollback(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        # Already rolled back — no-op.
        if state.get("reformulated_request") is None:
            return {}  # type: ignore[return-value]

        pre = state.get("pre_reformulation_transcript")
        if isinstance(pre, str) and pre.strip():
            update: dict[str, object] = {
                "transcript": pre,
                "reformulated_request": None,
                "trace_events": [
                    {
                        "event_type": "reformulation_rolled_back",
                        "node": "reformulate_request",
                        "summary": "Restored the original pre-reformulation transcript.",
                        "evidence_refs": [],
                        "state_delta_keys": ["transcript", "reformulated_request", "trace_events"],
                    }
                ],
            }
            ctx = state.get("project_context")
            if isinstance(ctx, dict):
                update["project_context"] = dict(ctx)
            return update  # type: ignore[return-value]

        # reformulated_request exists but no pre_reformulation_transcript saved.
        return {
            "reformulated_request": None,
        }

    return rollback
