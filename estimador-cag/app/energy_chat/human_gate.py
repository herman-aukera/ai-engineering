"""Human-in-the-loop gate for Energy Aware Chat — revision-guarded interrupt and resume.

Milestone 12: clarify and escalate dispositions trigger a LangGraph interrupt
that waits for a typed HumanActionRequest. Resume is revision-guarded: stale
actions targeting an older state revision are rejected.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HumanGateMode = Literal["disabled", "required", "risk_based"]
HumanActionType = Literal["clarify_response", "escalate_response"]


class HumanActionRequest(BaseModel):
    """Typed human action with revision guard for safe interrupt resume.

    The *expected_revision* must match the state revision at the time the
    interrupt was requested. Stale actions targeting older revisions are
    rejected to prevent applying actions to a state that has since changed.
    """

    action_id: str = Field(min_length=1)
    action: HumanActionType
    reason: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)
    actor: str | None = Field(
        default=None,
        description="Trusted actor identifier (future production use)",
    )
    payload: dict[str, str] = Field(default_factory=dict)


class HumanGateConfig(BaseModel):
    """Configuration for human-in-the-loop behavior.

    - *disabled*: clarify/escalate terminate normally (M9 behavior).
    - *required*: every clarify/escalate interrupts for human action.
    - *risk_based*: deferred — interrupts only when risk exceeds threshold.
    """

    mode: HumanGateMode = "disabled"


class StaleHumanActionError(ValueError):
    """Raised when a human action targets a state revision that no longer matches."""


def validate_human_action(
    action: HumanActionRequest, *, current_revision: int
) -> None:
    """Reject human actions that target a stale state revision."""
    if action.expected_revision != current_revision:
        raise StaleHumanActionError(
            f"Human action {action.action_id} expected revision "
            f"{action.expected_revision} but state is at revision {current_revision}"
        )


def enable_human_gates(mode: HumanGateMode) -> bool:
    """Return True when the gate mode requires human interrupts."""
    return mode in ("required", "risk_based")
