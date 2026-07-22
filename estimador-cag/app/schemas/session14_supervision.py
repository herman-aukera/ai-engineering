from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SupervisorDestination = Literal[
    "requirements_extractor",
    "budget_searcher",
    "estimate_generator",
    "coherence_validator",
    "human_review_gate",
    "finalize",
    "__end__",
]

RouteReasonCode = Literal[
    "missing_requirements",
    "missing_budget_evidence",
    "missing_estimate",
    "missing_validation",
    "human_review_required",
    "work_complete",
    "routing_budget_exhausted",
    "model_route_accepted",
]


class StrictSession14Model(BaseModel):
    """Base model that rejects undeclared data."""

    model_config = ConfigDict(extra="forbid")


class SupervisorDecision(StrictSession14Model):
    """A validated routing decision with no business-tool authority."""

    next_agent: SupervisorDestination
    reason_code: RouteReasonCode
    reason: str = Field(min_length=1, max_length=240)


class SupervisorStateDigest(StrictSession14Model):
    """A compact projection containing only routing-relevant signals."""

    requirements_count: int = Field(ge=0)
    requirements_extraction_completed: bool = False
    budget_match_count: int = Field(ge=0)
    budget_search_completed: bool = False
    estimate_ready: bool
    validation_ready: bool
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    review_required: bool
    routing_steps: int = Field(ge=0)
    status: str = Field(min_length=1, max_length=64)


def _list_size(value: object) -> int:
    """Return list cardinality without copying its potentially sensitive content."""

    return len(value) if isinstance(value, list) else 0


def build_supervisor_digest(
    state: Mapping[str, object],
) -> SupervisorStateDigest:
    """Project shared state into the minimum information needed for routing."""

    status = state.get("status")

    return SupervisorStateDigest(
        requirements_count=_list_size(state.get("requirements")),
        requirements_extraction_completed=state.get(
            "requirements_extraction_completed",
            False,
        ),
        budget_match_count=_list_size(state.get("budget_matches")),
        budget_search_completed=state.get("budget_search_completed", False),
        estimate_ready=(
            _list_size(state.get("component_estimates")) > 0
            or state.get("estimate") is not None
        ),
        validation_ready=state.get("validation") is not None,
        confidence=state.get("confidence"),
        review_required=state.get("review_required", False),
        routing_steps=state.get("routing_steps", 0),
        status=status if isinstance(status, str) and status else "pending",
    )
