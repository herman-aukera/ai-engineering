from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .base import StrictModel


class ObservationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    MISSING = "missing"
    CONFLICT = "conflict"
    NOT_APPLICABLE = "not_applicable"


class ConstraintObservation(StrictModel):
    observation_id: str
    constraint_id: str
    status: ObservationStatus
    penalty: float = Field(ge=0, allow_inf_nan=False)
    hard_blocking: bool = False
    required_evidence_missing: bool = False
    affected_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    repair_ref: str | None = None
    summary: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_status(self) -> "ConstraintObservation":
        if self.status in {ObservationStatus.PASS, ObservationStatus.NOT_APPLICABLE} and self.penalty:
            raise ValueError("passing/not-applicable observations must have zero penalty")
        if self.required_evidence_missing and self.status != ObservationStatus.MISSING:
            raise ValueError("required_evidence_missing requires status=missing")
        return self
