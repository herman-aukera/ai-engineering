"""Strict V2 request/response contracts for the graph-backed Energy Aware Chat API.

Milestone 10: provider-neutral selector contracts with additive V2 routes.
No persistence, HITL, or multi-provider adapters claimed.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.energy_chat.audit_models import EnergyCardV2
from app.energy_chat.contracts import Mode, SourceNeedResult

# ── Provider-neutral selectors ───────────────────────────────────────────

ProviderPreference = Literal["auto", "deepseek", "kimi", "openai"]
EffortProfile = Literal["fast", "balanced", "max"]
ContextProfile = Literal["minimal", "balanced", "max"]
OrchestrationMode = Literal["single", "critic", "committee", "adaptive"]
ExecutionProfile = Literal["deterministic", "live_bounded"]

# ── Identity factory ─────────────────────────────────────────────────────

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


# ── V2 request ───────────────────────────────────────────────────────────


class EnergyChatV2Request(BaseModel):
    """Graph-backed V2 request with provider-neutral selector contracts.

    All selector fields are additive. The underlying graph owns domain truth.
    Unknown fields are rejected to prevent silent misconfiguration.
    """

    model_config = ConfigDict(extra="forbid")

    user_message: str = Field(min_length=1, max_length=10000)
    mode: Mode = "project"
    k: int = Field(default=3, ge=1, le=8)
    required_constraints: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)

    # Identity — validated and bounded; server generates when absent
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

    # Provider-neutral selectors
    provider_preference: ProviderPreference = "deepseek"
    effort_profile: EffortProfile = "balanced"
    context_profile: ContextProfile = "balanced"
    orchestration_mode: OrchestrationMode = "critic"

    # Execution routing
    execution_profile: ExecutionProfile = "deterministic"

    # Future-compatible HITL declaration (unsupported in M10)
    human_gate: bool = Field(
        default=False,
        description="Human-in-the-loop gate declaration — unsupported in this milestone",
    )

    metadata: dict[str, str] = Field(default_factory=dict)


# ── Safe provider metrics summary ────────────────────────────────────────


class ProviderMetricsSummary(BaseModel):
    """Aggregated safe provider facts. No credentials, prompts, or raw transcripts."""

    provider_call_count: int = 0
    providers_used: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    fallback_used: bool = False


# ── V2 response ──────────────────────────────────────────────────────────


class EnergyChatV2Response(BaseModel):
    """Authoritative V2 response projected from graph state and Decision Ledger.

    Excludes prompts, evidence bodies, hidden reasoning, credentials,
    and raw provider transcripts.
    """

    # Identity
    thread_id: str
    request_id: str
    trace_id: str

    # Graph execution status
    graph_status: str
    awaiting_evidence: bool = False

    # Source need
    source_need: SourceNeedResult | None = None
    evidence_refs: list[str] = Field(default_factory=list)

    # Decision and answer
    final_disposition: str | None = None
    final_answer: str | None = None

    # Authoritative projections from graph state
    energy_card_v2: EnergyCardV2 | None = None
    execution_markers: list[str] = Field(default_factory=list)

    # Counts
    candidate_count: int = 0
    repair_count: int = 0
    repair_outcomes: list[str] = Field(default_factory=list)

    # Provider facts
    requested_provider: str = "deepseek"
    served_provider: str = ""
    served_model: str | None = None
    fallback_used: bool = False
    routing_reason: str = ""
    provider_metrics_summary: ProviderMetricsSummary = Field(
        default_factory=ProviderMetricsSummary
    )

    # Audit references
    ledger_entry_ids: list[str] = Field(default_factory=list)
    trace_summary: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


# ── Safe error response ──────────────────────────────────────────────────


class EnergyChatV2ErrorDetail(BaseModel):
    """Machine-readable error without stack traces, secrets, or raw provider data."""

    error: str
    detail: str
    request_id: str | None = None
    trace_id: str | None = None


# ── Typed application errors ─────────────────────────────────────────────


class ProviderUnavailableError(RuntimeError):
    """Raised when a requested provider has no credentialed adapter.

    Never silently falls back to a different provider.
    """

    def __init__(self, provider: str, detail: str = "") -> None:
        self.provider = provider
        self.detail = detail or f"{provider} requires a credentialed adapter (deferred)"
        super().__init__(self.detail)


class UnsupportedProfileError(RuntimeError):
    """Raised when a selector profile is valid but not yet implemented."""

    def __init__(self, field: str, value: str, detail: str = "") -> None:
        self.field = field
        self.value = value
        self.detail = detail or f"'{value}' is not implemented for {field}"
        super().__init__(self.detail)
