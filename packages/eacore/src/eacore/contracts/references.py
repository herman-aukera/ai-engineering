from __future__ import annotations

from pydantic import Field

from .base import StrictModel


class CandidateRef(StrictModel):
    candidate_id: str
    candidate_version: str
    candidate_kind: str
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_ref: str
    parent_candidate_id: str | None = None


class ConstraintRef(StrictModel):
    constraint_id: str
    constraint_class: str = Field(pattern=r"^(hard|soft)$")
    policy_ref: str
    description_ref: str | None = None
