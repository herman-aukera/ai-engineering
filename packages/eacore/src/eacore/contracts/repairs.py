from __future__ import annotations

from enum import StrEnum

from .base import StrictModel


class RepairResult(StrEnum):
    IMPROVED = "improved"
    NO_IMPROVEMENT = "no_improvement"
    BUDGET_EXHAUSTED = "budget_exhausted"
    NOT_REPAIRABLE = "not_repairable"
    HUMAN_REQUIRED = "human_required"


class RepairRef(StrictModel):
    repair_id: str
    source_candidate_id: str
    target_candidate_id: str
    repair_kind: str
    instruction_ref: str
    result: RepairResult
    energy_before_ref: str
    energy_after_ref: str
