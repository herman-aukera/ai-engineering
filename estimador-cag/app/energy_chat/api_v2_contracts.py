"""Strict V2 request/response contracts for the graph-backed Energy Aware Chat API.

Milestone 10 repair: route-owned execution, explicit fallback authorization,
and truthful provider projection. Milestone 11 adds typed application-lifetime
checkpoint inspection and replay without claiming restart persistence.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.energy_chat.audit_models import EnergyCardV2
from app.energy_chat.contracts import Mode, SourceNeedResult

ProviderPreference = Literal["auto", "deepseek", "kimi", "openai"]
FallbackProvider = Literal["deepseek", "kimi", "openai"]
EffortProfile = Literal["fast", "balanced", "max"]
ContextProfile = Literal["minimal", "balanced", "max"]
OrchestrationMode = Literal["single", "critic", "committee", "adaptive"]
ExecutionProfile = Literal["deterministic", "live_bounded"]

_IDENTITY_PATTERN = r"^[a-zA-Z0-9_-]+$"
_IDENTITY_MAX_LENGTH = 128


class IDFactory(Protocol):
    """Dependency-injected identity generation for deterministic testing."""

    def new_thread_id(self) -> str: ...
    def new_request_id(self) -> str: ...
    def new_trace_id(self) -> str: ...


class UUID4IDFactory:
    """Production identity generator using UUID4."""

    def new_thread_id(self) -> str:
        return f"thread-{uuid.uuid4().hex[:12]}"

    def new_request_id(self) -> str:
        return f"request-{uuid.uuid4().hex[:12]}"

    def new_trace_id(self) -> str:
        return f"trace-{uuid.uuid4().hex[:12]}"


class EnergyChatV2Request(BaseModel):
    """Strict graph-backed V2 request.

    ``execution_profile`` remains temporarily accepted for transport
    compatibility, but the selected route owns the profile and rejects a
    contradictory value. Unknown fields fail validation.
    """

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

    human_gate: bool = Field(
        default=False,
        description="Human-in-the-loop declaration; public resume is not active yet",
    )
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


class ProviderMetricsSummary(BaseModel):
    """Aggregated safe provider facts."""

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
    """Authoritative user-safe projection of graph state."""

    model_config = ConfigDict(extra="forbid")

    thread_id: str
    request_id: str
    trace_id: str
    graph_status: str
    awaiting_evidence: bool = False
    source_need: SourceNeedResult | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    final_disposition: str | None = None
    final_answer: str | None = None
    energy_card_v2: EnergyCardV2 | None = None
    execution_markers: list[str] = Field(default_factory=list)
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
    provider_metrics_summary: ProviderMetricsSummary = Field(
        default_factory=ProviderMetricsSummary
    )
    ledger_entry_ids: list[str] = Field(default_factory=list)
    trace_summary: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    checkpoint_id: str | None = None
    replayed_from_checkpoint: bool = False


class EnergyChatV2ThreadStateResponse(BaseModel):
    """Safe metadata projection for the latest checkpoint in one public thread."""

    model_config = ConfigDict(extra="forbid")

    thread_id: str
    request_id: str
    trace_id: str
    checkpoint_id: str | None = None
    graph_status: str
    awaiting_evidence: bool = False
    candidate_count: int = 0
    provider_call_count: int = 0
    ledger_entry_ids: list[str] = Field(default_factory=list)
    process_local: bool = True
    restart_persistent: bool = False


class EnergyChatV2ErrorDetail(BaseModel):
    """Machine-readable error without stack traces or provider bodies."""

    model_config = ConfigDict(extra="forbid")

    error: str
    detail: str
    request_id: str | None = None
    trace_id: str | None = None


class ProviderUnavailableError(RuntimeError):
    """Raised when a requested provider has no verified adapter."""

    def __init__(self, provider: str, detail: str = "") -> None:
        self.provider = provider
        self.detail = detail or f"{provider} requires a credentialed adapter (deferred)"
        super().__init__(self.detail)


class UnsupportedProfileError(RuntimeError):
    """Raised when a valid selector conflicts with the active route or runtime."""

    def __init__(self, field: str, value: str, detail: str = "") -> None:
        self.field = field
        self.value = value
        self.detail = detail or f"'{value}' is not implemented for {field}"
        super().__init__(self.detail)
