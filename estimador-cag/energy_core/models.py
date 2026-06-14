from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EvidenceStatus = Literal["pass", "fail", "missing", "conflict"]
Decision = Literal["accept", "repair", "reject", "escalate"]
ConstraintDecision = Literal["reject", "repair", "repair_if_threshold_exceeded"]
ConstraintType = Literal["hard_reject", "hard_repair", "soft", "missing_evidence", "conflict"]


class EnergyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Thresholds(EnergyModel):
    accept_max_soft_energy: int = 120
    repair_min_soft_energy: int = 121
    reject_on_any_hard_reject: bool = True
    reject_on_missing_required_evidence: bool = False


class ConstraintPolicy(EnergyModel):
    description: str
    penalty: int = Field(ge=0)
    decision: ConstraintDecision
    required_evidence: list[str] = Field(default_factory=list)
    repair_hint: str = "Repair the candidate so the constraint can pass."


class EvidenceTypePolicy(EnergyModel):
    required_format: str = "text"
    trusted: bool = True


class DecisionRule(EnergyModel):
    id: str
    rule: str


class EnergyPolicy(EnergyModel):
    policy_id: str
    version: str
    owner: str
    status: str
    thresholds: Thresholds
    hard_constraints: dict[str, ConstraintPolicy]
    soft_constraints: dict[str, ConstraintPolicy] = Field(default_factory=dict)
    evidence_types: dict[str, EvidenceTypePolicy] = Field(default_factory=dict)
    required_acceptance_evidence: list[str] = Field(default_factory=list)
    decision_rules: list[DecisionRule] = Field(default_factory=list)


class CandidateState(EnergyModel):
    candidate_id: str
    spec_id: str
    energy_before: int = Field(default=0, ge=0)
    changed_files: list[str] = Field(default_factory=list)
    required_artifacts: list[str] = Field(default_factory=list)
    present_artifacts: list[str] = Field(default_factory=list)
    validation_claims: list[str] = Field(default_factory=list)
    scope_claims: list[str] = Field(default_factory=list)
    soft_flags: list[str] = Field(default_factory=list)


class EvidenceRecord(EnergyModel):
    evidence_id: str
    type: str
    status: EvidenceStatus
    summary: str
    trusted: bool = True
    command: str | None = None
    path: str | None = None
    exit_code: int | None = None


class Violation(EnergyModel):
    violation_id: str
    critic: str
    constraint_type: ConstraintType
    penalty: int = Field(ge=0)
    evidence: str
    repair_hint: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "high"


class EnergyDecision(EnergyModel):
    policy_id: str
    candidate_id: str
    decision: Decision
    energy_before: int = Field(ge=0)
    energy_after: int = Field(ge=0)
    energy_delta: int
    hard_reject_violations: list[str]
    hard_repair_violations: list[str]
    soft_violations: list[str]
    missing_evidence: list[str]
    evidence_refs: list[str]
    required_repairs: list[str]
    reasoning_summary: str
    next_action: str
