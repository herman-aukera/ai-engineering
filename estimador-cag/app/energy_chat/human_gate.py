"""Human-in-the-loop contracts for Energy Aware Chat.

Clarify and escalate dispositions trigger a LangGraph interrupt. A trusted reviewer
then chooses approve, adjust, or reject. Revision, action identity, actor, reason,
and idempotency are validated before the authoritative checkpoint is updated.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HumanGateMode = Literal["disabled", "required", "risk_based"]
HumanActionType = Literal["clarify_response", "escalate_response"]
HumanDecision = Literal["approve", "adjust", "reject"]


class HumanAdjustment(BaseModel):
    """Allow-listed human replacement that must pass the full critic/Boss pipeline."""

    model_config = ConfigDict(extra="forbid")

    revised_answer: str = Field(min_length=1, max_length=20_000)


class HumanActionRequest(BaseModel):
    """Typed human request/response crossing a durable checkpoint boundary."""

    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1, max_length=256)
    action: HumanActionType
    reason: str = Field(min_length=1, max_length=2000)
    expected_revision: int = Field(ge=1)
    actor: str | None = Field(
        default=None,
        max_length=256,
        description="Trusted actor identifier when authentication is available",
    )
    decision: HumanDecision | None = None
    decision_reason: str | None = Field(default=None, min_length=1, max_length=2000)
    idempotency_key: str | None = Field(
        default=None,
        min_length=8,
        max_length=256,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    adjustments: HumanAdjustment | None = None
    payload: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_authority_payload(self) -> HumanActionRequest:
        if self.decision is None:
            if any(
                value is not None
                for value in (
                    self.decision_reason,
                    self.idempotency_key,
                    self.adjustments,
                )
            ):
                raise ValueError("Pending human requests cannot contain review authority")
            return self
        if not self.actor or not self.actor.strip():
            raise ValueError("Human authority requires an actor")
        if not self.decision_reason or not self.decision_reason.strip():
            raise ValueError("Human authority requires a decision reason")
        if not self.idempotency_key:
            raise ValueError("Human authority requires an idempotency key")
        if self.decision == "adjust" and self.adjustments is None:
            raise ValueError("Adjust requires a typed revised answer")
        if self.decision != "adjust" and self.adjustments is not None:
            raise ValueError("Only adjust may contain adjustments")
        return self


class HumanGateConfig(BaseModel):
    """Configuration for human-in-the-loop behavior."""

    model_config = ConfigDict(extra="forbid")

    mode: HumanGateMode = "disabled"


class StaleHumanActionError(ValueError):
    """Raised when a human action targets a stale state revision."""


class HumanActionMismatchError(ValueError):
    """Raised when action identity or type differs from the pending interrupt."""


class HumanIdempotencyConflictError(ValueError):
    """Raised when an idempotency key is reused for a different authority decision."""


def validate_human_action(
    action: HumanActionRequest,
    *,
    current_revision: int,
    expected_action_id: str | None = None,
    expected_action: HumanActionType | None = None,
) -> None:
    """Validate a reviewer action against the authoritative pending interrupt."""

    if action.decision is None:
        raise HumanActionMismatchError("Human resume requires approve, adjust, or reject")
    if action.expected_revision != current_revision:
        raise StaleHumanActionError(
            f"Human action {action.action_id} expected revision "
            f"{action.expected_revision} but state is at revision {current_revision}"
        )
    if expected_action_id is not None and action.action_id != expected_action_id:
        raise HumanActionMismatchError(
            f"Human action ID {action.action_id} does not match pending action "
            f"{expected_action_id}"
        )
    if expected_action is not None and action.action != expected_action:
        raise HumanActionMismatchError(
            f"Human action type {action.action} does not match pending action "
            f"{expected_action}"
        )


def enable_human_gates(mode: HumanGateMode) -> bool:
    """Return True when the gate mode requires human interrupts."""

    return mode in ("required", "risk_based")
