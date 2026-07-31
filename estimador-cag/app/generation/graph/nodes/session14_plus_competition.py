"""Deterministic candidate competition node for Session 14 Plus."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Literal

from langgraph.types import Command

from app.generation.graph.session14_plus_state import (
    Session14PlusEstimationGraphState,
)
from app.services.session14_plus_competition import (
    COMPETITION_POLICY_VERSION,
    EstimateCompetitionPolicy,
    build_estimate_competition,
)


def build_session14_plus_competition_node(
    *,
    policy: EstimateCompetitionPolicy | None = None,
):
    """Build a tool-free competition and synthesis node."""

    active_policy = policy or EstimateCompetitionPolicy()

    async def candidate_competition(
        state: Session14PlusEstimationGraphState,
    ) -> Command[Literal["supervisor"]]:
        raw_estimates = state.get("component_estimates")
        if not isinstance(raw_estimates, list) or not raw_estimates:
            raise ValueError(
                "candidate competition requires component estimates"
            )
        if not all(isinstance(item, Mapping) for item in raw_estimates):
            raise ValueError("component estimates must be mappings")
        estimation_id = state.get("estimation_id")
        if not isinstance(estimation_id, str) or not estimation_id.strip():
            raise ValueError("estimation_id must not be blank")

        outcome = build_estimate_competition(
            [dict(item) for item in raw_estimates],
            estimation_id=estimation_id,
            policy=active_policy,
        )
        assessment = outcome.assessment
        review_required = bool(
            state.get("review_required", False)
            or assessment.review_required
        )
        update = Session14PlusEstimationGraphState(
            component_estimates=deepcopy(
                outcome.selected_component_estimates
            ),
            review_required=review_required,
            plus_competition_enabled=True,
            plus_competition_completed=True,
            plus_competition_policy_version=(
                COMPETITION_POLICY_VERSION
            ),
            plus_competition_candidates=[
                candidate.model_dump(mode="json")
                for candidate in outcome.candidates
            ],
            plus_competition_assessment=(
                assessment.model_dump(mode="json")
            ),
            trace_events=[
                {
                    "event_type": "candidate_competition",
                    "node": "candidate_competition",
                    "summary": (
                        "Bounded estimate competition completed with "
                        f"disposition {assessment.disposition}."
                    ),
                    "evidence_refs": [
                        candidate.candidate_id
                        for candidate in outcome.candidates
                    ],
                    "state_delta_keys": [
                        "component_estimates",
                        "plus_competition_candidates",
                        "plus_competition_assessment",
                        "review_required",
                    ],
                }
            ],
        )
        return Command(goto="supervisor", update=update)

    return candidate_competition
