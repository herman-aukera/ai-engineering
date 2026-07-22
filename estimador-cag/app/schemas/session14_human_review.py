"""Strict Session 14 contracts for persistent human review."""

from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator

Session14HumanReviewAction = Literal["approve", "adjust", "reject"]
Session14HumanReviewReasonCode = Literal[
    "low_confidence",
    "outside_historical_range",
    "no_precedent",
    "validation_requires_review",
    "routing_budget_exhausted",
]
Session14HumanReviewStatus = Literal[
    "not_requested",
    "awaiting_human_review",
    "approved",
    "adjusted",
    "rejected",
]
HistoricalRangeStatus = Literal[
    "within_range",
    "outside_range",
    "unavailable",
]


class StrictSession14ReviewPayload(BaseModel):
    """Reject fields that are not part of the public review contract."""

    model_config = ConfigDict(extra="forbid")


class Session14EstimateAdjustment(StrictSession14ReviewPayload):
    """One typed, human-evidenced component-hours adjustment."""

    component_id: str = Field(min_length=1, max_length=120)
    hours: float = Field(gt=0, le=100_000)
    evidence_refs: list[str] = Field(min_length=1, max_length=50)


class Session14HumanReviewDecision(StrictSession14ReviewPayload):
    """Validated value supplied through ``Command(resume=...)``."""

    action: Session14HumanReviewAction
    expected_revision: int = Field(ge=1)
    actor: str = Field(min_length=1, max_length=240)
    reason: str | None = Field(default=None, max_length=2_000)
    idempotency_key: str = Field(
        min_length=8,
        max_length=120,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )
    adjustments: list[Session14EstimateAdjustment] | None = None

    @model_validator(mode="after")
    def validate_action_contract(
        self,
    ) -> Session14HumanReviewDecision:
        reason = (self.reason or "").strip()

        if self.action == "adjust":
            if not reason:
                raise ValueError("adjust requires a reason")
            if not self.adjustments:
                raise ValueError(
                    "adjust requires at least one component adjustment"
                )
            component_ids = [
                adjustment.component_id
                for adjustment in self.adjustments
            ]
            if len(component_ids) != len(set(component_ids)):
                raise ValueError(
                    "adjustment component_id values must be unique"
                )
        elif self.adjustments is not None:
            raise ValueError("only adjust may include adjustments")

        if self.action == "reject" and not reason:
            raise ValueError("reject requires a reason")

        return self


class Session14HumanReviewActionRecord(TypedDict):
    """Sanitized, replay-safe record persisted after a human action."""

    action_id: str
    idempotency_key: str
    action: Session14HumanReviewAction
    actor: str
    reason: str | None
    revision: int
    adjustments: list[dict[str, object]]
