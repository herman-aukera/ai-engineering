"""User-safe, versioned audit and projection contracts for Energy Aware Chat."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.energy_chat.contracts import Decision

AUDIT_SCHEMA_VERSION = "1.0.0"
ENERGY_CARD_V2_SCHEMA_VERSION = "2.0.0"
FINAL_PROJECTION_SCHEMA_VERSION = "1.0.0"

TrustStatus = Literal["trusted", "unverified", "unknown"]
FreshnessStatus = Literal["current", "stale", "not_applicable", "unknown"]
RedactionStatus = Literal["reference_only", "redacted", "unknown"]
BodyHashStatus = Literal["hashed", "not_permitted", "unavailable"]
VerificationStatus = Literal["verified", "failed", "not_checked"]


class AuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceIntegrityMetadata(AuditRecord):
    """Integrity and disclosure metadata for one evidence reference.

    ``reference_hash`` covers the exact reference string. ``body_hash`` is present
    only when a non-sensitive project body was explicitly permitted for hashing.
    No evidence body is retained by this model.
    """

    evidence_ref: str = Field(min_length=1)
    reference_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trust_status: TrustStatus = "unknown"
    freshness_status: FreshnessStatus = "unknown"
    redaction_status: RedactionStatus = "reference_only"
    body_included: Literal[False] = False
    body_hash: str | None = Field(
        default=None,
        pattern=r"^(sha256:[0-9a-f]{64})?$",
    )
    body_hash_status: BodyHashStatus = "unavailable"
    verification_status: VerificationStatus = "not_checked"
    byte_count: int | None = Field(default=None, ge=0)


class DecisionLedgerEntry(AuditRecord):
    schema_version: Literal["1.0.0"] = AUDIT_SCHEMA_VERSION
    ledger_entry_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    thread_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    critic_panel_id: str = Field(min_length=1)
    score_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    policy_rule_id: str = Field(min_length=1)
    disposition: Decision
    reason_summary: str = Field(min_length=1)
    energy_before: int = Field(ge=0)
    energy_after: int = Field(ge=0)
    energy_delta: int
    hard_reject_violations: list[str] = Field(default_factory=list)
    hard_repair_violations: list[str] = Field(default_factory=list)
    soft_violations: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_integrity: list[EvidenceIntegrityMetadata] = Field(default_factory=list)
    provider_call_ids: list[str] = Field(default_factory=list)
    repair_request_ids: list[str] = Field(default_factory=list)
    repair_result_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class EnergyCardV2(AuditRecord):
    schema_version: Literal["2.0.0"] = ENERGY_CARD_V2_SCHEMA_VERSION
    ledger_entry_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    decision: Decision
    policy_version: str = Field(min_length=1)
    policy_rule_id: str = Field(min_length=1)
    hard_constraints_passed: bool
    hard_constraint_violations: list[str] = Field(default_factory=list)
    soft_quality_findings: list[str] = Field(default_factory=list)
    energy_before: int = Field(ge=0)
    energy_after: int = Field(ge=0)
    energy_delta: int
    repair_attempts: int = Field(ge=0)
    repair_outcomes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    reason_summary: str = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)


class FinalAnswerProjection(AuditRecord):
    schema_version: Literal["1.0.0"] = FINAL_PROJECTION_SCHEMA_VERSION
    ledger_entry_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    disposition: Decision
    answer: str = Field(min_length=1)
    energy_card: EnergyCardV2
    execution_markers: list[str] = Field(default_factory=list)
