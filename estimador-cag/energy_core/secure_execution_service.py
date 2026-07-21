"""One-time secure execution orchestration and normalized evidence.

The service atomically reserves authority before invoking the process adapter,
records execution completion only after a process actually starts, and emits
sanitized evidence for deterministic critics. It never accepts a candidate or
changes the deterministic judge decision.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Protocol

from pydantic import Field, model_validator

from energy_core.live_authorization import LiveAuthorizationReceipt
from energy_core.live_execution_contract import LiveExecutionIntent, LiveExecutionPlan
from energy_core.models import (
    EnergyModel,
    EvidenceRecord,
    EvidenceStatus,
    RedactionStatus,
    TrustClassification,
)
from energy_core.secure_process_adapter import SecureProcessResult


class SecureProcessPort(Protocol):
    def invoke(
        self,
        plan: LiveExecutionPlan,
        authorization_receipt: LiveAuthorizationReceipt,
        live_intent: LiveExecutionIntent,
    ) -> SecureProcessResult:
        """Return sanitized process evidence without deciding acceptance."""


class LiveReceiptLifecycleStore(Protocol):
    def get(self, receipt_id: str) -> LiveAuthorizationReceipt | None:
        """Return the authoritative receipt."""

    def is_execution_reserved(self, receipt_id: str) -> bool:
        """Return whether the one process attempt is reserved."""

    def reserve_execution(self, receipt_id: str) -> LiveAuthorizationReceipt:
        """Atomically reserve one process attempt."""

    def mark_executed(self, receipt_id: str) -> LiveAuthorizationReceipt:
        """Atomically record that a process started."""


class LiveExecutionEvidence(EnergyModel):
    """Normalized, sanitized evidence returned to deterministic critics."""

    schema_version: str = "1.0.0"
    evidence_id: str = Field(min_length=1, max_length=240)
    run_id: str = Field(min_length=1, max_length=240)
    recorded_at: datetime
    status: EvidenceStatus
    summary: str = Field(min_length=1, max_length=4_000)
    live_plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    base_plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    repository_snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    authorization_receipt_id: str = Field(min_length=1, max_length=240)
    authorization_record_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    accepted_revision: int = Field(ge=0)
    adapter_invoked: bool = True
    authority_reserved: bool
    authority_completion_verified: bool
    execution_performed: bool
    cleanup_verified: bool
    failure_class: str | None = Field(default=None, max_length=100)
    exit_code: int | None = None
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    output_truncated: bool = False
    redaction_status: RedactionStatus = "not_required"
    artifact_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    trust_classification: TrustClassification = "unknown"

    @model_validator(mode="after")
    def validate_evidence_integrity(self) -> LiveExecutionEvidence:
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise ValueError("recorded_at must be timezone-aware")
        if self.artifact_hash != self.calculate_artifact_hash():
            raise ValueError("artifact_hash does not match live execution evidence")
        return self

    def calculate_artifact_hash(self) -> str:
        return _sha256_json(
            self.model_dump(mode="json", exclude={"artifact_hash"})
        )

    def to_evidence_record(self) -> EvidenceRecord:
        return EvidenceRecord(
            schema_version=self.schema_version,
            evidence_id=self.evidence_id,
            run_id=self.run_id,
            recorded_at=self.recorded_at.isoformat(),
            type="controlled_live_execution",
            status=self.status,
            summary=self.summary,
            trusted=self.trust_classification == "trusted",
            trust_classification=self.trust_classification,
            provenance={
                "execution_mode": "live",
                "live_plan_hash": self.live_plan_hash,
                "base_plan_hash": self.base_plan_hash,
                "repository_snapshot_hash": self.repository_snapshot_hash,
                "authorization_receipt_id": self.authorization_receipt_id,
                "authorization_record_hash": self.authorization_record_hash,
                "accepted_revision": self.accepted_revision,
                "adapter_invoked": self.adapter_invoked,
                "authority_reserved": self.authority_reserved,
                "authority_completion_verified": self.authority_completion_verified,
                "execution_performed": self.execution_performed,
                "cleanup_verified": self.cleanup_verified,
                "failure_class": self.failure_class,
                "output_truncated": self.output_truncated,
            },
            redaction_status=self.redaction_status,
            command_hash=self.live_plan_hash,
            artifact_hash=self.artifact_hash,
            exit_code=self.exit_code,
        )


class SecureExecutionOutcome(EnergyModel):
    """Execution result, final authority state, and evidence as one typed unit."""

    result: SecureProcessResult
    reserved_receipt: LiveAuthorizationReceipt
    final_receipt: LiveAuthorizationReceipt | None = None
    evidence: LiveExecutionEvidence


class SecureExecutionService:
    """Coordinate one non-replayable process attempt and evidence handoff."""

    def __init__(
        self,
        *,
        adapter: SecureProcessPort,
        receipt_store: LiveReceiptLifecycleStore,
    ) -> None:
        self._adapter = adapter
        self._receipt_store = receipt_store

    def execute(
        self,
        plan: LiveExecutionPlan,
        intent: LiveExecutionIntent,
        receipt: LiveAuthorizationReceipt,
        *,
        run_id: str,
    ) -> SecureExecutionOutcome:
        reserved = self._receipt_store.reserve_execution(receipt.receipt_id)
        result = self._adapter.invoke(plan, reserved, intent)

        final_receipt: LiveAuthorizationReceipt | None = None
        completion_error: str | None = None
        if result.process_started:
            try:
                final_receipt = self._receipt_store.mark_executed(receipt.receipt_id)
            except PermissionError as exc:
                completion_error = type(exc).__name__
                final_receipt = self._receipt_store.get(receipt.receipt_id)
        else:
            final_receipt = self._receipt_store.get(receipt.receipt_id)

        evidence = build_live_execution_evidence(
            plan=plan,
            result=result,
            reserved_receipt=reserved,
            final_receipt=final_receipt,
            run_id=run_id,
            completion_error=completion_error,
        )
        return SecureExecutionOutcome(
            result=result,
            reserved_receipt=reserved,
            final_receipt=final_receipt,
            evidence=evidence,
        )


def build_live_execution_evidence(
    *,
    plan: LiveExecutionPlan,
    result: SecureProcessResult,
    reserved_receipt: LiveAuthorizationReceipt,
    final_receipt: LiveAuthorizationReceipt | None,
    run_id: str,
    completion_error: str | None = None,
    recorded_at: datetime | None = None,
) -> LiveExecutionEvidence:
    """Build integrity-protected evidence without assigning a judge decision."""

    completion_verified = bool(
        result.process_started
        and final_receipt is not None
        and final_receipt.execution_performed
        and completion_error is None
    )
    if completion_error is not None:
        status: EvidenceStatus = "conflict"
    elif result.process_started and not result.cleanup_verified:
        status = "conflict"
    elif not result.process_started:
        status = "missing"
    elif result.failure_class is not None or result.exit_code not in (0, None):
        status = "fail"
    else:
        status = "pass"

    trusted = not (
        completion_error is not None
        or (result.process_started and not result.cleanup_verified)
        or result.failure_class == "stream_failure"
    )
    summary_parts = ["Secure live execution evidence recorded."]
    if not result.process_started:
        summary_parts.append("Process did not start; authority remains reserved.")
    if result.timed_out:
        summary_parts.append("Process timed out.")
    if result.cancelled:
        summary_parts.append("Process was cancelled.")
    if result.failure_class == "non_zero_exit":
        summary_parts.append(f"Process exited with code {result.exit_code}.")
    if not result.cleanup_verified and result.process_started:
        summary_parts.append("Process-tree cleanup was not verified.")
    if completion_error is not None:
        summary_parts.append("Authority completion persistence was not verified.")
    if result.redacted:
        summary_parts.append("Output was redacted.")
    if result.stdout_truncated or result.stderr_truncated:
        summary_parts.append("Output was truncated.")

    effective_receipt = final_receipt or reserved_receipt
    payload = {
        "evidence_id": f"live-execution-{plan.plan_hash[:16]}",
        "run_id": run_id,
        "recorded_at": recorded_at or datetime.now(UTC),
        "status": status,
        "summary": " ".join(summary_parts),
        "live_plan_hash": plan.plan_hash,
        "base_plan_hash": plan.base_plan_hash,
        "repository_snapshot_hash": plan.repository_snapshot_hash,
        "authorization_receipt_id": reserved_receipt.receipt_id,
        "authorization_record_hash": effective_receipt.record_hash,
        "accepted_revision": reserved_receipt.accepted_revision,
        "adapter_invoked": True,
        "authority_reserved": reserved_receipt.execution_reserved,
        "authority_completion_verified": completion_verified,
        "execution_performed": result.process_started,
        "cleanup_verified": result.cleanup_verified,
        "failure_class": result.failure_class,
        "exit_code": result.exit_code,
        "stdout_excerpt": result.stdout,
        "stderr_excerpt": result.stderr,
        "output_truncated": result.stdout_truncated or result.stderr_truncated,
        "redaction_status": "redacted" if result.redacted else "not_required",
        "trust_classification": "trusted" if trusted else "unknown",
    }
    draft = LiveExecutionEvidence.model_construct(artifact_hash="0" * 64, **payload)
    return LiveExecutionEvidence(
        artifact_hash=draft.calculate_artifact_hash(),
        **payload,
    )


def _sha256_json(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object is not JSON serializable: {type(value).__name__}")
