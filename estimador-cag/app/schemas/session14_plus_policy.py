"""Strict contracts for Session 14 Plus provider and context policy."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.v3_routing import ReasoningEffort

ProviderId = Literal["python", "deepseek", "moonshot", "openai"]
CapabilityLifecycle = Literal[
    "documented",
    "configured",
    "reachable",
    "contract_verified",
    "benchmark_calibrated",
    "disabled",
]
CalibrationStatus = Literal["unmeasured", "baseline", "matched", "disabled"]
ContextDetail = Literal["minimal", "medium", "max"]
Modality = Literal["text", "image", "audio", "video"]
SpeedClass = Literal["deterministic", "fast", "balanced", "slow"]
ContextScalar: TypeAlias = str | int | float | bool | None


class StrictSession14PlusModel(BaseModel):
    """Immutable, checkpoint-safe base for Plus policy records."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelCapabilityRecord(StrictSession14PlusModel):
    """One versioned provider capability record."""

    record_id: str = Field(min_length=1)
    provider: ProviderId
    provider_model_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    capability_tier: str = Field(min_length=1)
    context_window_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(ge=0)
    modalities: list[Modality] = Field(default_factory=lambda: ["text"])
    supports_tools: bool = False
    supports_structured_output: bool = False
    reasoning_efforts: list[ReasoningEffort] = Field(default_factory=lambda: ["none"])
    speed_class: SpeedClass
    cost_metadata_version: str = Field(min_length=1)
    lifecycle: CapabilityLifecycle
    verified_at: datetime | None = None
    calibration_status: CalibrationStatus = "unmeasured"
    enabled: bool = False

    @model_validator(mode="after")
    def validate_capability_state(self) -> ModelCapabilityRecord:
        if len(set(self.modalities)) != len(self.modalities):
            raise ValueError("modalities must be unique")
        if len(set(self.reasoning_efforts)) != len(self.reasoning_efforts):
            raise ValueError("reasoning_efforts must be unique")
        if self.lifecycle == "disabled" and self.enabled:
            raise ValueError("disabled capability records cannot be enabled")
        if self.enabled and self.lifecycle not in {
            "contract_verified",
            "benchmark_calibrated",
        }:
            raise ValueError(
                "enabled capability records must be contract verified or benchmark calibrated"
            )
        if self.lifecycle == "benchmark_calibrated" and self.verified_at is None:
            raise ValueError("benchmark calibrated records require verified_at")
        if self.provider == "python" and self.speed_class != "deterministic":
            raise ValueError("python capability records must be deterministic")
        return self


class ModelCapabilityRegistry(StrictSession14PlusModel):
    """Versioned collection used to authorize model routes."""

    registry_version: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    records: list[ModelCapabilityRecord]

    @model_validator(mode="after")
    def validate_unique_records(self) -> ModelCapabilityRegistry:
        record_ids: set[str] = set()
        model_keys: set[tuple[str, str]] = set()
        for record in self.records:
            if record.record_id in record_ids:
                raise ValueError(f"duplicate capability record_id: {record.record_id}")
            model_key = (record.provider, record.provider_model_id)
            if model_key in model_keys:
                raise ValueError(
                    f"duplicate capability provider/model: {record.provider}/{record.provider_model_id}"
                )
            record_ids.add(record.record_id)
            model_keys.add(model_key)
        return self


class Session14ContextSource(StrictSession14PlusModel):
    """Authoritative inputs from which a compacted handoff is derived."""

    source_revision: int = Field(ge=1)
    identity: dict[str, str]
    objective: str = Field(min_length=1)
    working_mode: str = Field(min_length=1)
    hard_constraints: list[str] = Field(default_factory=list)
    accepted_decisions: list[str] = Field(default_factory=list)
    rejected_alternatives: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    current_state: dict[str, ContextScalar] = Field(default_factory=dict)
    unresolved_questions: list[str] = Field(default_factory=list)
    execution_budgets: dict[str, int | float] = Field(default_factory=dict)
    provider_route: dict[str, str] = Field(default_factory=dict)
    repository_state: dict[str, str] = Field(default_factory=dict)
    validation_state: dict[str, str] = Field(default_factory=dict)
    checkpoint_state: dict[str, str | int] = Field(default_factory=dict)
    next_action: str = Field(min_length=1)
    rollback_boundary: str = Field(min_length=1)
    claim_boundary: str = Field(min_length=1)
    recent_events: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_identity(self) -> Session14ContextSource:
        if not self.identity:
            raise ValueError("identity must not be empty")
        if any(not key.strip() or not value.strip() for key, value in self.identity.items()):
            raise ValueError("identity keys and values must not be blank")
        return self


class CompactedSession14Context(StrictSession14PlusModel):
    """Sanitized, deterministic handoff derived from authoritative sources."""

    context_id: str = Field(min_length=1)
    source_revision: int = Field(ge=1)
    detail: ContextDetail
    identity: dict[str, str]
    objective: str
    working_mode: str
    hard_constraints: list[str]
    accepted_decisions: list[str]
    rejected_alternatives: list[str]
    evidence_refs: list[str]
    current_state: dict[str, ContextScalar]
    unresolved_questions: list[str]
    execution_budgets: dict[str, int | float]
    provider_route: dict[str, str]
    repository_state: dict[str, str]
    validation_state: dict[str, str]
    checkpoint_state: dict[str, str | int]
    next_action: str
    rollback_boundary: str
    claim_boundary: str
    recent_events: list[str]
    dropped_item_counts: dict[str, int]
    fingerprint: str = Field(min_length=64, max_length=64)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContextCompactionEvent(StrictSession14PlusModel):
    """Replay-safe audit event for one compaction boundary."""

    event_id: str = Field(min_length=1)
    source_revision: int = Field(ge=1)
    detail: ContextDetail
    context_id: str = Field(min_length=1)
    fingerprint: str = Field(min_length=64, max_length=64)
    retained_sections: list[str]
    dropped_item_counts: dict[str, int]
