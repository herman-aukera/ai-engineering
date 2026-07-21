"""Human-in-the-loop gate for Energy Aware Chat.

Clarify and escalate dispositions can trigger a LangGraph interrupt that waits
for a typed human action. Production resume validates revision, action identity,
and action type before invoking ``Command(resume=...)``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HumanGateMode = Literal["disabled", "required", "risk_based"]
HumanActionType = Literal["clarify_response", "escalate_response"]


class HumanActionRequest(BaseModel):
    """Typed human action request/response crossing a checkpoint boundary."""

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
    payload: dict[str, str] = Field(default_factory=dict)


class HumanGateConfig(BaseModel):
    """Configuration for human-in-the-loop behavior."""

    model_config = ConfigDict(extra="forbid")

    mode: HumanGateMode = "disabled"


class StaleHumanActionError(ValueError):
    """Raised when a human action targets a stale state revision."""


class HumanActionMismatchError(ValueError):
    """Raised when action identity or type differs from the pending interrupt."""


def validate_human_action(
    action: HumanActionRequest,
    *,
    current_revision: int,
    expected_action_id: str | None = None,
    expected_action: HumanActionType | None = None,
) -> None:
    """Validate a human action against the authoritative pending interrupt."""

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
