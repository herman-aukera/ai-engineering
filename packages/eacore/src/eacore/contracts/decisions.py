from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .base import StrictModel


class OutcomeClass(StrEnum):
    ACCEPTED = "accepted"
    CHANGE_REQUIRED = "change_required"
    BLOCKED = "blocked"
    HUMAN_REQUIRED = "human_required"
    IN_PROGRESS = "in_progress"


class DecisionEnvelope(StrictModel):
    decision_id: str
    candidate_id: str
    product_decision_code: str
    outcome_class: OutcomeClass
    policy_ref: str
    energy_snapshot_ref: str
    finding_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    repair_refs: tuple[str, ...] = ()
    human_decision_refs: tuple[str, ...] = ()
    authorization_ref: str | None = None
    reason_summary: str = Field(min_length=1, max_length=2000)
    limitations: tuple[str, ...] = ()
