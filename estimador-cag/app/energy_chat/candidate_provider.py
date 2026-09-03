"""Typed candidate-provider contracts and adapters for Energy Aware Chat."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol

from pydantic import Field, field_validator

from app.energy_chat.agent import build_project_grounded_draft
from app.energy_chat.baseline import (
    BASELINE_TIER_LADDER,
    BaselineDraftProvider,
    generate_deepseek_baseline_draft,
)
from app.energy_chat.contracts import (
    DeepSeekBaselineRequest,
    EnergyAwareChatAgentRequest,
    Mode,
    ProjectRagResult,
    ProviderTier,
)
from app.energy_chat.graph_state import GraphStateRecord, ProviderMetrics
from app.energy_chat.live_agent import build_provider_grounded_prompt


class ProviderBudgetExceededError(RuntimeError):
    """Raised when a completed provider result exceeds an authoritative budget."""


class ProviderBudget(GraphStateRecord):
    """Per-candidate provider limits enforced before state application."""

    max_output_tokens: int = Field(default=1200, ge=64, le=4000)
    max_cost_usd: float = Field(default=0.05, ge=0.0)
    max_latency_ms: int = Field(default=30_000, ge=1)
    max_retries: int = Field(default=1, ge=0, le=8)


class CandidateProviderRequest(GraphStateRecord):
    """Provider-neutral input for one immutable answer candidate."""

    provider_call_id: str = Field(min_length=1)
    user_request: str = Field(min_length=1)
    mode: Mode
    constraints: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    project_rag: ProjectRagResult | None = None
    max_tokens: int = Field(default=1200, ge=64, le=4000)


class CandidateGenerationResult(GraphStateRecord):
    """Provider-neutral candidate plus observable call facts."""

    answer: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    metrics: ProviderMetrics

    @field_validator("answer")
    @classmethod
    def visible_answer_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Candidate provider returned no visible answer")
        return normalized


class CandidateProvider(Protocol):
    """Dependency-injected candidate generation boundary."""

    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        """Generate exactly one candidate and its metrics."""


class DeterministicCandidateProvider:
    """CI-safe adapter preserving the existing local draft behavior."""

    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        agent_request = EnergyAwareChatAgentRequest(
            user_message=request.user_request,
            mode=request.mode,
            required_constraints=request.constraints,
            required_sections=request.required_sections,
        )
        answer = build_project_grounded_draft(
            request=agent_request,
            evidence_refs=request.evidence_refs,
        )
        return CandidateGenerationResult(
            answer=answer,
            evidence_refs=request.evidence_refs,
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider="deterministic_local",
                model="energy-chat-template-v1",
                tier="local",
            ),
        )


class BaselineCandidateProvider:
    """Adapter over the existing live baseline seam.

    The legacy default remains fallback-capable. V2 configures an explicit
    per-request policy before graph execution and defaults to no fallback.
    """

    def __init__(
        self,
        *,
        provider: BaselineDraftProvider | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._provider = provider
        self._clock = clock
        self._allow_provider_fallback = True
        self._fallback_tier_ladder = list(BASELINE_TIER_LADDER)

    def configure_fallback_policy(
        self,
        *,
        allow_provider_fallback: bool,
        tier_ladder: list[ProviderTier],
    ) -> BaselineCandidateProvider:
        """Bind one explicit fallback policy to this request-scoped adapter."""

        self._allow_provider_fallback = allow_provider_fallback
        self._fallback_tier_ladder = list(tier_ladder)
        return self

    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        agent_request = EnergyAwareChatAgentRequest(
            user_message=request.user_request,
            mode=request.mode,
            required_constraints=request.constraints,
            required_sections=request.required_sections,
        )
        chunks = request.project_rag.results if request.project_rag else []
        prompt = build_provider_grounded_prompt(request=agent_request, chunks=chunks)
        started = self._clock()
        baseline = generate_deepseek_baseline_draft(
            DeepSeekBaselineRequest(
                user_message=prompt,
                mode=request.mode,
                max_tokens=request.max_tokens,
                required_constraints=request.constraints,
                required_sections=request.required_sections,
            ),
            provider=self._provider,
            allow_provider_fallback=self._allow_provider_fallback,
            tier_ladder=self._fallback_tier_ladder,
        )
        latency_ms = max(0, round((self._clock() - started) * 1000))
        evidence_refs = list(
            dict.fromkeys([*request.evidence_refs, *baseline.evidence_refs])
        )
        if baseline.fallback_used and self._allow_provider_fallback:
            evidence_refs.extend(
                [
                    f"fallback_to:{baseline.provider}",
                    "fallback_authorized:true",
                ]
            )
        return CandidateGenerationResult(
            answer=baseline.draft_answer,
            evidence_refs=list(dict.fromkeys(evidence_refs)),
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider=baseline.provider,
                model=baseline.model,
                tier=baseline.tier,
                input_tokens=baseline.input_tokens,
                output_tokens=baseline.output_tokens,
                cost_usd=baseline.cost_usd or 0.0,
                latency_ms=latency_ms,
                retries=_safe_retries(baseline.metadata),
                fallback_used=baseline.fallback_used,
                finish_reason=baseline.finish_reason,
            ),
        )


def enforce_provider_budget(metrics: ProviderMetrics, budget: ProviderBudget) -> None:
    """Fail closed when observable provider facts exceed configured limits."""

    if metrics.output_tokens is not None and metrics.output_tokens > budget.max_output_tokens:
        raise ProviderBudgetExceededError("Provider output token budget exceeded")
    if metrics.cost_usd > budget.max_cost_usd:
        raise ProviderBudgetExceededError("Provider cost budget exceeded")
    if metrics.latency_ms > budget.max_latency_ms:
        raise ProviderBudgetExceededError("Provider latency budget exceeded")
    if metrics.retries > budget.max_retries:
        raise ProviderBudgetExceededError("Provider retry budget exceeded")


def _safe_retries(metadata: dict[str, Any]) -> int:
    value = metadata.get("retries", 0)
    return max(0, int(value)) if isinstance(value, int | float | str) else 0


__all__ = [
    "BaselineCandidateProvider",
    "CandidateGenerationResult",
    "CandidateProvider",
    "CandidateProviderRequest",
    "DeterministicCandidateProvider",
    "ProviderBudget",
    "ProviderBudgetExceededError",
    "ProviderMetrics",
]
