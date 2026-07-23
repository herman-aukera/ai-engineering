"""Energy-aware, append-only decision contracts for Session 13 Plus V3."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ObservationStatus = Literal["pass", "fail", "missing", "conflict", "not_applicable"]
TrustClassification = Literal["trusted", "untrusted", "unknown"]
RedactionStatus = Literal["not_required", "redacted", "unknown"]
RepairOutcome = Literal["improved", "no_improvement", "budget_exhausted", "not_repairable"]


class StrictEnergyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceIntegrityMetadata(StrictEnergyModel):
    evidence_id: str = Field(min_length=1)
    source_version: str | None = None
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    trust: TrustClassification = "unknown"
    redaction_status: RedactionStatus = "unknown"
    fresh_until: datetime | None = None
    required: bool = False


class ConstraintObservation(StrictEnergyModel):
    observation_id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    status: ObservationStatus
    penalty: int = Field(default=0, ge=0)
    hard_blocking: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    affected_refs: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_pass_contract(self) -> ConstraintObservation:
        if self.status in {"pass", "not_applicable"} and self.penalty:
            raise ValueError("passing observations cannot add energy")
        if self.hard_blocking and self.status not in {"fail", "missing", "conflict"}:
            raise ValueError("hard blockers require fail, missing, or conflict status")
        return self


class EstimateCandidateVersion(StrictEnergyModel):
    candidate_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    checkpoint_id: str = Field(min_length=1)
    parent_candidate_id: str | None = None
    source: Literal["graph", "repair", "human_override"]


class ConstraintEnergySnapshot(StrictEnergyModel):
    snapshot_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    energy_before: int = Field(ge=0)
    energy_after: int = Field(ge=0)
    energy_delta: int
    hard_violations: list[str] = Field(default_factory=list)
    soft_penalties: dict[str, int] = Field(default_factory=dict)
    missing_evidence: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    evidence_sufficiency: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_energy_arithmetic(self) -> ConstraintEnergySnapshot:
        if self.energy_delta != self.energy_after - self.energy_before:
            raise ValueError("energy_delta must equal energy_after - energy_before")
        if sum(self.soft_penalties.values()) > self.energy_after:
            raise ValueError("soft penalties cannot exceed total energy")
        return self


class RepairResult(StrictEnergyModel):
    repair_id: str = Field(min_length=1)
    source_candidate_id: str = Field(min_length=1)
    target_candidate_id: str = Field(min_length=1)
    energy_before_snapshot_id: str = Field(min_length=1)
    energy_after_snapshot_id: str = Field(min_length=1)
    outcome: RepairOutcome


class EstimateDecisionLedgerEntry(StrictEnergyModel):
    schema_version: Literal["session13.estimate-decision.v1"] = "session13.estimate-decision.v1"
    decision_id: str = Field(min_length=1)
    estimation_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    checkpoint_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    critic_report_ref: str = Field(min_length=1)
    energy_snapshot_id: str = Field(min_length=1)
    boss_action: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    human_decision_refs: list[str] = Field(default_factory=list)
    repair_refs: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1, max_length=2000)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EstimateEnergyCard(StrictEnergyModel):
    candidate_id: str = Field(min_length=1)
    disposition: str = Field(min_length=1)
    hard_constraints_passed: bool
    energy_before: int = Field(ge=0)
    energy_after: int = Field(ge=0)
    energy_delta: int
    evidence_sufficiency: float = Field(ge=0, le=1)
    repairs: int = Field(ge=0)
    remaining_caveats: list[str] = Field(default_factory=list)
    policy_version: str = Field(min_length=1)
