from __future__ import annotations

from dataclasses import dataclass

from app.schemas.session14_supervision import (
    SupervisorDecision,
    SupervisorFallbackReason,
    SupervisorProposalDestination,
    SupervisorRouteProposal,
    SupervisorRouteSource,
    SupervisorStateDigest,
)
from app.services.session14_human_review import (
    DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
)

MAX_ROUTING_STEPS = 12


@dataclass(frozen=True)
class GuardedSupervisorRoute:
    """Final Python-authorized route plus model/fallback provenance."""

    decision: SupervisorDecision
    route_source: SupervisorRouteSource
    proposed_agent: SupervisorProposalDestination | None
    candidate_agents: tuple[SupervisorProposalDestination, ...]
    fallback_reason: SupervisorFallbackReason | None


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


def legal_supervisor_destinations(
    digest: SupervisorStateDigest,
    *,
    max_routing_steps: int = MAX_ROUTING_STEPS,
    confidence_threshold: float = (
        DEFAULT_SESSION14_CONFIDENCE_THRESHOLD
    ),
) -> tuple[SupervisorProposalDestination, ...]:
    """Return the closed destinations Python permits for this state."""

    policy_decision = choose_deterministic_route(
        digest,
        max_routing_steps=max_routing_steps,
        confidence_threshold=confidence_threshold,
    )
    destination = policy_decision.next_agent

    if destination == "finalize":
        # On a clean terminal state both paths are safe. The gate performs the
        # same deterministic assessment and falls through without pausing.
        return ("finalize", "human_review_gate")

    if destination == "__end__":
        raise ValueError("supervisor policy must not route directly to END")

    return (destination,)


def accept_supervisor_proposal(
    proposal: SupervisorRouteProposal,
    digest: SupervisorStateDigest,
    *,
    max_routing_steps: int = MAX_ROUTING_STEPS,
    confidence_threshold: float = (
        DEFAULT_SESSION14_CONFIDENCE_THRESHOLD
    ),
) -> GuardedSupervisorRoute:
    """Accept a legal model proposal or replace it with the safe policy route."""

    fallback = choose_deterministic_route(
        digest,
        max_routing_steps=max_routing_steps,
        confidence_threshold=confidence_threshold,
    )
    candidates = legal_supervisor_destinations(
        digest,
        max_routing_steps=max_routing_steps,
        confidence_threshold=confidence_threshold,
    )

    if proposal.next_agent not in candidates:
        return GuardedSupervisorRoute(
            decision=fallback,
            route_source="deterministic_fallback",
            proposed_agent=proposal.next_agent,
            candidate_agents=candidates,
            fallback_reason="illegal_proposal",
        )

    reason_code = (
        fallback.reason_code
        if proposal.next_agent == fallback.next_agent
        else "model_route_accepted"
    )
    return GuardedSupervisorRoute(
        decision=SupervisorDecision(
            next_agent=proposal.next_agent,
            reason_code=reason_code,
            reason=proposal.reason,
        ),
        route_source="model",
        proposed_agent=proposal.next_agent,
        candidate_agents=candidates,
        fallback_reason=None,
    )


def deterministic_supervisor_route(
    digest: SupervisorStateDigest,
    *,
    max_routing_steps: int = MAX_ROUTING_STEPS,
    confidence_threshold: float = (
        DEFAULT_SESSION14_CONFIDENCE_THRESHOLD
    ),
    fallback_reason: SupervisorFallbackReason = (
        "proposer_unavailable"
    ),
) -> GuardedSupervisorRoute:
    """Build a replay-safe deterministic route with explicit provenance."""

    decision = choose_deterministic_route(
        digest,
        max_routing_steps=max_routing_steps,
        confidence_threshold=confidence_threshold,
    )
    is_budget_limit = (
        decision.reason_code == "routing_budget_exhausted"
    )
    return GuardedSupervisorRoute(
        decision=decision,
        route_source=(
            "budget_limit"
            if is_budget_limit
            else (
                "deterministic_policy"
                if fallback_reason == "proposer_unavailable"
                else "deterministic_fallback"
            )
        ),
        proposed_agent=None,
        candidate_agents=legal_supervisor_destinations(
            digest,
            max_routing_steps=max_routing_steps,
            confidence_threshold=confidence_threshold,
        ),
        fallback_reason=(
            "routing_budget_exhausted"
            if is_budget_limit
            else fallback_reason
        ),
    )
