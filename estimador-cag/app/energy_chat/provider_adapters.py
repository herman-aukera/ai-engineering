"""Provider-neutral candidate adapters for DeepSeek, Kimi Platform, and OpenAI.

Normal tests inject a fake transport. Default transports are created lazily only
for credentialed live requests. Adapters never perform provider fallback; the
application policy owns any explicitly authorized escalation.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProviderRequest,
)
from app.energy_chat.contracts import EnergyAwareChatAgentRequest
from app.energy_chat.graph_state import ProviderMetrics
from app.energy_chat.live_agent import build_provider_grounded_prompt
from app.energy_chat.provider_catalog import (
    EffortProfile,
    ProviderName,
    ResolvedProviderProfile,
    resolve_effort_profile,
)


class ProviderTransportResult(BaseModel):
    """Normalized visible provider result; hidden reasoning is excluded."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    finish_reason: str | None = None


class ProviderTransport(Protocol):
    """One no-fallback provider call boundary."""

    def complete(
        self,
        *,
        profile: ResolvedProviderProfile,
        messages: list[dict[str, str]],
        max_output_tokens: int,
    ) -> ProviderTransportResult: ...


class CatalogCandidateProvider:
    """Candidate provider bound to one verified catalog profile and transport."""

    def __init__(
        self,
        *,
        profile: ResolvedProviderProfile,
        transport: ProviderTransport,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        if not profile.capability.eligible_for_eachat:
            raise ValueError("Coding-only provider surfaces cannot serve EACHAT")
        self.profile = profile
        self.transport = transport
        self.clock = clock

    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        agent_request = EnergyAwareChatAgentRequest(
            user_message=request.user_request,
            mode=request.mode,
            required_constraints=request.constraints,
            required_sections=request.required_sections,
        )
        chunks = request.project_rag.results if request.project_rag else []
        prompt = build_provider_grounded_prompt(request=agent_request, chunks=chunks)
        messages = [
            {
                "role": "system",
                "content": (
                    "Generate one visible answer candidate for deterministic Energy Aware "
                    "evaluation. Do not expose hidden reasoning. Do not claim evidence "
                    "that is not present in the supplied project context."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        started = self.clock()
        result = self.transport.complete(
            profile=self.profile,
            messages=messages,
            max_output_tokens=request.max_tokens,
        )
        latency_ms = max(0, round((self.clock() - started) * 1000))
        return CandidateGenerationResult(
            answer=result.answer,
            evidence_refs=request.evidence_refs,
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider=self.profile.provider,
                model=self.profile.capability.model_id,
                tier=self.profile.effort_profile,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cost_usd=_estimate_cost_usd(self.profile, result),
                latency_ms=latency_ms,
                retries=0,
                fallback_used=False,
                finish_reason=result.finish_reason,
            ),
        )


class OpenAICompatibleChatTransport:
    """OpenAI ChatCompletions transport for DeepSeek and Kimi Platform."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        if not _usable_api_key(api_key):
            raise ValueError("A non-placeholder provider API key is required")
        self.api_key = api_key
        self.base_url = base_url
        self.client_factory = client_factory or _openai_client_factory

    def complete(
        self,
        *,
        profile: ResolvedProviderProfile,
        messages: list[dict[str, str]],
        max_output_tokens: int,
    ) -> ProviderTransportResult:
        client = self.client_factory(api_key=self.api_key, base_url=self.base_url)
        kwargs: dict[str, Any] = {
            "model": profile.capability.model_id,
            "messages": messages,
            "max_tokens": max_output_tokens,
            "stream": False,
        }
        parameters = profile.provider_parameters
        if profile.provider == "deepseek":
            thinking = str(parameters.get("thinking", "enabled"))
            kwargs["extra_body"] = {"thinking": {"type": thinking}}
            if thinking == "enabled":
                kwargs["reasoning_effort"] = (
                    "max" if profile.effort_profile == "max" else "high"
                )
        elif profile.provider == "kimi":
            reasoning_effort = parameters.get("reasoning_effort")
            if reasoning_effort is not None:
                kwargs["reasoning_effort"] = reasoning_effort

        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        answer = str(getattr(choice.message, "content", "") or "").strip()
        if not answer:
            raise RuntimeError("Provider returned no visible answer")
        usage = getattr(response, "usage", None)
        return ProviderTransportResult(
            answer=answer,
            input_tokens=_optional_int(getattr(usage, "prompt_tokens", None)),
            output_tokens=_optional_int(getattr(usage, "completion_tokens", None)),
            finish_reason=_optional_str(getattr(choice, "finish_reason", None)),
        )


class OpenAIResponsesTransport:
    """OpenAI Responses API transport for GPT-5.6 models."""

    def __init__(
        self,
        *,
        api_key: str,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        if not _usable_api_key(api_key):
            raise ValueError("A non-placeholder OpenAI API key is required")
        self.api_key = api_key
        self.client_factory = client_factory or _openai_client_factory

    def complete(
        self,
        *,
        profile: ResolvedProviderProfile,
        messages: list[dict[str, str]],
        max_output_tokens: int,
    ) -> ProviderTransportResult:
        client = self.client_factory(api_key=self.api_key)
        kwargs: dict[str, Any] = {
            "model": profile.capability.model_id,
            "input": messages,
            "max_output_tokens": max_output_tokens,
        }
        kwargs.update(profile.provider_parameters)
        response = client.responses.create(**kwargs)
        answer = str(getattr(response, "output_text", "") or "").strip()
        if not answer:
            raise RuntimeError("OpenAI Responses API returned no visible answer")
        usage = getattr(response, "usage", None)
        return ProviderTransportResult(
            answer=answer,
            input_tokens=_optional_int(getattr(usage, "input_tokens", None)),
            output_tokens=_optional_int(getattr(usage, "output_tokens", None)),
            finish_reason=_optional_str(getattr(response, "status", None)),
        )


def build_catalog_candidate_provider(
    provider: ProviderName,
    effort: EffortProfile,
    *,
    transport: ProviderTransport | None = None,
    environment: dict[str, str] | None = None,
) -> CatalogCandidateProvider:
    """Build one no-fallback adapter or fail closed on unavailable credentials."""

    profile = resolve_effort_profile(provider, effort)
    if profile is None:
        raise ValueError(f"No catalog profile for {provider}/{effort}")
    active_transport = transport or _default_transport(
        profile,
        environment=environment,
    )
    return CatalogCandidateProvider(profile=profile, transport=active_transport)


def _default_transport(
    profile: ResolvedProviderProfile,
    *,
    environment: dict[str, str] | None,
) -> ProviderTransport:
    env = environment if environment is not None else os.environ
    if profile.provider == "deepseek":
        key = env.get("DEEPSEEK_API_KEY", "")
        return OpenAICompatibleChatTransport(
            api_key=key,
            base_url=profile.capability.endpoint_base_url,
        )
    if profile.provider == "kimi":
        key = env.get("MOONSHOT_API_KEY", "") or env.get("KIMI_API_KEY", "")
        return OpenAICompatibleChatTransport(
            api_key=key,
            base_url=profile.capability.endpoint_base_url,
        )
    if profile.provider == "openai":
        return OpenAIResponsesTransport(api_key=env.get("OPENAI_API_KEY", ""))
    raise ValueError(f"Unsupported provider: {profile.provider}")


def _estimate_cost_usd(
    profile: ResolvedProviderProfile,
    result: ProviderTransportResult,
) -> float:
    capability = profile.capability
    input_cost = (
        (result.input_tokens or 0) * (capability.input_price_per_million or 0.0)
        / 1_000_000
    )
    output_cost = (
        (result.output_tokens or 0) * (capability.output_price_per_million or 0.0)
        / 1_000_000
    )
    return round(input_cost + output_cost, 12)


def _usable_api_key(value: str) -> bool:
    normalized = value.strip().casefold()
    return bool(normalized) and normalized not in {
        "test",
        "dummy",
        "placeholder",
        "changeme",
    }


def _openai_client_factory(**kwargs: Any):
    from openai import OpenAI

    return OpenAI(**kwargs)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)
