"""Strict V2 contracts for the graph-backed Energy Aware Chat API."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.energy_chat.audit_models import EnergyCardV2
from app.energy_chat.contracts import Mode, SourceNeedResult
from app.energy_chat.evidence_hardening import (
    CandidateCitationValidation,
    EvidenceBodyMetadata,
)
from app.energy_chat.human_gate import (
    HumanActionRequest,
    HumanActionType,
    HumanAdjustment,
    HumanDecision,
)
from app.energy_chat.observability import GraphExecutionMetrics

ProviderPreference = Literal["auto", "deepseek", "kimi", "openai"]
FallbackProvider = Literal["deepseek", "kimi", "openai"]
EffortProfile = Literal["fast", "balanced", "max"]
ContextProfile = Literal["minimal", "balanced", "max"]
OrchestrationMode = Literal["single", "critic", "committee", "adaptive"]
ExecutionProfile = Literal["deterministic", "live_bounded"]

_IDENTITY_PATTERN = r"^[a-zA-Z0-9_-]+$"
_IDENTITY_MAX_LENGTH = 128


class IDFactory(Protocol):
    def new_thread_id(self) -> str: ...
    def new_request_id(self) -> str: ...
    def new_trace_id(self) -> str: ...


class UUID4IDFactory:
    def new_thread_id(self) -> str:
        return f"thread-{uuid.uuid4().hex[:12]}"

    def new_request_id(self) -> str:
        return f"request-{uuid.uuid4().hex[:12]}"

    def new_trace_id(self) -> str:
        return f"trace-{uuid.uuid4().hex[:12]}"


class EnergyChatV2Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_message: str = Field(min_length=1, max_length=10000)
    mode: Mode = "project"
    k: int = Field(default=3, ge=1, le=8)
    required_constraints: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=_IDENTITY_MAX_LENGTH,
        pattern=_IDENTITY_PATTERN,
    )
    request_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=_IDENTITY_MAX_LENGTH,
        pattern=_IDENTITY_PATTERN,
    )
    trace_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=_IDENTITY_MAX_LENGTH,
        pattern=_IDENTITY_PATTERN,
    )
    provider_preference: ProviderPreference = "deepseek"
    effort_profile: EffortProfile = "balanced"
    context_profile: ContextProfile = "balanced"
    orchestration_mode: OrchestrationMode = "critic"
    execution_profile: ExecutionProfile | None = Field(
        default=None,
        description="Compatibility declaration; the selected HTTP route is authoritative",
    )
    allow_provider_fallback: bool = False
    fallback_provider_allowlist: list[FallbackProvider] = Field(default_factory=list)
    human_gate: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_fallback_contract(self) -> EnergyChatV2Request:
        self.fallback_provider_allowlist = list(
            dict.fromkeys(self.fallback_provider_allowlist)
        )
        if self.allow_provider_fallback and not self.fallback_provider_allowlist:
            raise ValueError(
                "fallback_provider_allowlist is required when provider fallback is enabled"
            )
        if not self.allow_provider_fallback and self.fallback_provider_allowlist:
            raise ValueError(
                "fallback_provider_allowlist requires allow_provider_fallback=true"
            )
        return self


class EnergyChatV2HumanResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1, max_length=256)
    action: HumanActionType
    expected_revision: int = Field(ge=1)
    actor: str = Field(default="same-origin-client", min_length=1, max_length=256)
    decision: HumanDecision = "approve"
    decision_reason: str = Field(
        default="Reviewer approved the current protected outcome.",
        min_length=1,
        max_length=2000,
    )
    idempotency_key: str | None = Field(
        default=None,
        min_length=8,
        max_length=256,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    adjustments: HumanAdjustment | None = None
    payload: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_decision_contract(self) -> EnergyChatV2HumanResumeRequest:
        if self.idempotency_key is None:
            digest = hashlib.sha256(self.action_id.encode("utf-8")).hexdigest()[:24]
            self.idempotency_key = f"review-{digest}"
        if self.decision == "adjust" and self.adjustments is None:
            raise ValueError("Adjust requires a typed revised answer")
        if self.decision != "adjust" and self.adjustments is not None:
            raise ValueError("Only adjust may include adjustments")
        return self


class ProviderMetricsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_call_count: int = 0
    providers_used: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    fallback_used: bool = False
    fallback_authorized: bool = False
    fallback_provider_allowlist: list[str] = Field(default_factory=list)


class EnergyChatV2Response(BaseModel):
    """User-safe projection; excludes prompts, bodies, credentials, and transcripts."""

    model_config = ConfigDict(extra="forbid")

    thread_id: str
    request_id: str
    trace_id: str
    graph_status: str
    awaiting_evidence: bool = False
    source_need: SourceNeedResult | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_body_metadata: list[EvidenceBodyMetadata] = Field(default_factory=list)
    citation_validations: list[CandidateCitationValidation] = Field(default_factory=list)
    final_disposition: str | None = None
    final_answer: str | None = None
    energy_card_v2: EnergyCardV2 | None = None
    execution_markers: list[str] = Field(default_factory=list)
    graph_metrics: GraphExecutionMetrics | None = None
    candidate_count: int = 0
    repair_count: int = 0
    repair_outcomes: list[str] = Field(default_factory=list)
    requested_provider: str = "deepseek"
    served_provider: str = "none"
    served_model: str | None = None
    fallback_used: bool = False
    fallback_authorized: bool = False
    fallback_provider_allowlist: list[str] = Field(default_factory=list)
    routing_reason: str = ""
    requested_orchestration_mode: OrchestrationMode = "critic"
    resolved_orchestration_mode: Literal["critic", "committee"] = "critic"
    orchestration_candidate_count: int = Field(default=1, ge=1, le=8)
    orchestration_reason: str = ""
    provider_metrics_summary: ProviderMetricsSummary = Field(
        default_factory=ProviderMetricsSummary
    )
    ledger_entry_ids: list[str] = Field(default_factory=list)
    trace_summary: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    checkpoint_id: str | None = None
    replayed_from_checkpoint: bool = False
    human_action_request: HumanActionRequest | None = None
    human_decision: HumanDecision | None = None


class EnergyChatV2ThreadStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    request_id: str
    trace_id: str
    checkpoint_id: str | None = None
    graph_status: str
    awaiting_evidence: bool = False
    candidate_count: int = 0
    provider_call_count: int = 0
    node_span_count: int = 0
    ledger_entry_ids: list[str] = Field(default_factory=list)
    human_action_pending: bool = False
    human_action_request: HumanActionRequest | None = None
    human_decision: HumanDecision | None = None
    process_local: bool = True
    restart_persistent: bool = False


class EnergyChatV2ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: str
    detail: str
    request_id: str | None = None
    trace_id: str | None = None


class ProviderUnavailableError(RuntimeError):
    def __init__(self, provider: str, detail: str = "") -> None:
        self.provider = provider
        self.detail = detail or f"{provider} requires a credentialed adapter (deferred)"
        super().__init__(self.detail)


class UnsupportedProfileError(RuntimeError):
    def __init__(self, field: str, value: str, detail: str = "") -> None:
        self.field = field
        self.value = value
        self.detail = detail or f"'{value}' is not implemented for {field}"
        super().__init__(self.detail)
