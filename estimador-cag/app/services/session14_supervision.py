from __future__ import annotations

from app.schemas.session14_supervision import (
    SupervisorDecision,
    SupervisorStateDigest,
)
from app.services.session14_human_review import (
    DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
)

MAX_ROUTING_STEPS = 12


def choose_deterministic_route(
    digest: SupervisorStateDigest,
    *,
    max_routing_steps: int = MAX_ROUTING_STEPS,
    confidence_threshold: float = (
        DEFAULT_SESSION14_CONFIDENCE_THRESHOLD
    ),
) -> SupervisorDecision:
    """Choose the next safe route from deterministic workflow prerequisites."""

    if not 0 <= confidence_threshold <= 1:
        raise ValueError(
            "confidence_threshold must be between zero and one"
        )

    if digest.routing_steps >= max_routing_steps:
        return SupervisorDecision(
            next_agent="human_review_gate",
            reason_code="routing_budget_exhausted",
            reason="The supervisor routing budget is exhausted.",
        )

    if not digest.requirements_extraction_completed:
        return SupervisorDecision(
            next_agent="requirements_extractor",
            reason_code="missing_requirements",
            reason="Requirements extraction has not completed.",
        )

    if not digest.budget_search_completed:
        return SupervisorDecision(
            next_agent="budget_searcher",
            reason_code="missing_budget_evidence",
            reason="Historical budget search has not completed.",
        )

    if not digest.estimate_ready:
        return SupervisorDecision(
            next_agent="estimate_generator",
            reason_code="missing_estimate",
            reason="No estimate has been produced.",
        )

    if not digest.validation_ready:
        return SupervisorDecision(
            next_agent="coherence_validator",
            reason_code="missing_validation",
            reason="The estimate has not been validated.",
        )

    if (
        digest.confidence is not None
        and digest.confidence < confidence_threshold
    ):
        return SupervisorDecision(
            next_agent="human_review_gate",
            reason_code="human_review_required",
            reason="The estimate confidence is below the review threshold.",
        )

    if digest.review_required:
        return SupervisorDecision(
            next_agent="human_review_gate",
            reason_code="human_review_required",
            reason="The validated result requires human review.",
        )

    return SupervisorDecision(
        next_agent="finalize",
        reason_code="work_complete",
        reason="All required specialist work is complete.",
    )
