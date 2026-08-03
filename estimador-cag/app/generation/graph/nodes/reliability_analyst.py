"""Deterministic reliability analyst node for Session 13 Plus V6."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.services.v6_reliability import analyse_reliability

NODE_NAME = "reliability_analyst"

ReliabilityAnalystNode = Callable[
    [ReviewedEstimationGraphState],
    Awaitable[ReviewedEstimationGraphState],
]


def build_reliability_analyst_node() -> ReliabilityAnalystNode:
    """Score component estimate reliability and store the report in state."""

    async def reliability_analyst(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        estimates = state.get("component_estimates", [])
        report = analyse_reliability(estimates if isinstance(estimates, list) else [])

        update: ReviewedEstimationGraphState = {
            "reliability_report": report.model_dump(mode="json"),
            "trace_events": [
                {
                    "event_type": "reliability_analysis_completed",
                    "node": NODE_NAME,
                    "summary": report.summary,
                    "evidence_refs": [c.component_id for c in report.components],
                    "state_delta_keys": ["reliability_report", "trace_events"],
                }
            ],
        }
        if report.requires_human_review:
            update["review_required"] = True
        return update

    return reliability_analyst
