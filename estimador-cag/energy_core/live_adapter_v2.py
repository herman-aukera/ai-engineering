"""Hardened opt-in provider adapters for EACODE.

Provider calls remain disabled by default and absent from deterministic CI. This
module normalizes endpoints, timeout units, reasoning controls, cost evidence,
and sanitized failures while preserving requested/planned/served distinctions.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any

from energy_core.models import EnergyModel
from energy_core.provider_adapter import (
    FakeProviderAdapter,
    ProviderAttempt,
    ProviderExecutionEvidence,
    TokenUsage,
)
from energy_core.provider_registry import (
    CapabilityRegistry,
    ProviderSelection,
    ResolvedProvider,
)
from energy_core.provider_verified import (
    VerifiedCapabilityRegistry,
    VerifiedProviderSelector,
)


class LiveAdapterConfig(EnergyModel):
    """Configuration for one explicitly enabled live provider adapter."""

    model_config = {"arbitrary_types_allowed": True, "extra": "forbid"}

    enabled: bool = False
    provider: str = ""
    api_key_env_var: str = ""
    api_base_url: str = ""
    registry: CapabilityRegistry | None = None


class BaseLiveAdapter:
    """Base adapter with fail-closed selection and fake-only disabled mode."""

    def __init__(self, config: LiveAdapterConfig) -> None:
        self.config = config
        self._registry = config.registry or VerifiedCapabilityRegistry()
        self._selector = VerifiedProviderSelector(self._registry)
        self._fake = FakeProviderAdapter(registry=self._registry)
        self.calls = 0

    def invoke(
        self,
        selection: ProviderSelection,
        *,
        messages: list[dict[str, str]] | None = None,
    ) -> ProviderExecutionEvidence:
        self.calls += 1

        if not self.config.enabled:
            return self._fake.invoke(selection, messages=messages)

        api_key = os.environ.get(self.config.api_key_env_var, "")
        if not api_key:
            return _failure_evidence(
                selection,
                provider=self.config.provider,
                error_message=f"API key not found: {self.config.api_key_env_var}",
            )

        try:
            planned = self._selector.select(selection)
        except ValueError as exc:
            return _failure_evidence(
                selection,
                provider=self.config.provider,
                error_message=f"selection_failed:{type(exc).__name__}",
            )

        return self._call_provider(planned, selection, messages, api_key)

    def _call_provider(
        self,
        planned: ResolvedProvider,
        selection: ProviderSelection,
        messages: list[dict[str, str]] | None,
        api_key: str,
    ) -> ProviderExecutionEvidence:
        raise NotImplementedError


class DeepSeekAdapter(BaseLiveAdapter):
    """Opt-in DeepSeek OpenAI-compatible adapter."""

    def _call_provider(
        self,
        planned: ResolvedProvider,
        selection: ProviderSelection,
        messages: list[dict[str, str]] | None,
        api_key: str,
    ) -> ProviderExecutionEvidence:
        return _openai_compatible_call(
            planned,
            selection,
            messages,
            api_key,
            self.config.api_base_url or "https://api.deepseek.com",
            self._registry,
        )


class KimiCodeAdapter(BaseLiveAdapter):
    """Opt-in Kimi Code membership adapter, distinct from Kimi Platform."""

    def _call_provider(
        self,
        planned: ResolvedProvider,
        selection: ProviderSelection,
        messages: list[dict[str, str]] | None,
        api_key: str,
    ) -> ProviderExecutionEvidence:
        return _openai_compatible_call(
            planned,
            selection,
            messages,
            api_key,
            self.config.api_base_url or "https://api.kimi.com/coding/v1",
            self._registry,
        )


class OpenAIAdapter(BaseLiveAdapter):
    """Opt-in OpenAI GPT-5.6 adapter."""

    def _call_provider(
        self,
        planned: ResolvedProvider,
        selection: ProviderSelection,
        messages: list[dict[str, str]] | None,
        api_key: str,
    ) -> ProviderExecutionEvidence:
        return _openai_compatible_call(
            planned,
            selection,
            messages,
            api_key,
            self.config.api_base_url or "https://api.openai.com/v1",
            self._registry,
        )


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _request_body(
    planned: ResolvedProvider,
    selection: ProviderSelection,
    messages: list[dict[str, str]] | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": planned.model_id,
        "messages": messages or [{"role": "user", "content": "Hello"}],
        "max_tokens": min(selection.expected_output_tokens, 4096),
    }

    if planned.provider == "deepseek":
        thinking_enabled = planned.reasoning_mode == "thinking"
        body["thinking"] = {"type": "enabled" if thinking_enabled else "disabled"}
        if thinking_enabled:
            body["reasoning_effort"] = planned.reasoning_effort
        else:
            body["temperature"] = 0.0
    elif planned.provider == "kimi":
        # K3 supports low/high/max. K2.7 Code keeps Thinking on without a
        # provider-native effort claim in the verified registry.
        if planned.model_id == "k3":
            body["reasoning_effort"] = planned.reasoning_effort
    elif planned.provider == "openai":
        body["reasoning_effort"] = planned.reasoning_effort

    return body


def _openai_compatible_call(
    planned: ResolvedProvider,
    selection: ProviderSelection,
    messages: list[dict[str, str]] | None,
    api_key: str,
    base_url: str,
    registry: CapabilityRegistry,
) -> ProviderExecutionEvidence:
    body = json.dumps(_request_body(planned, selection, messages)).encode("utf-8")
    url = _chat_completions_url(base_url)
    timeout_seconds = max(0.001, (selection.max_latency_ms or 60_000) / 1000)
    started = time.monotonic()

    try:
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Authorization", f"Bearer {api_key}")
        request.add_header("Content-Type", "application/json")
        response = urllib.request.urlopen(request, timeout=timeout_seconds)
        raw = response.read().decode("utf-8")
        data = json.loads(raw)
        elapsed_ms = int((time.monotonic() - started) * 1000)

        usage = data.get("usage", {})
        cached_tokens = usage.get("prompt_cache_hit_tokens", 0)
        if not cached_tokens:
            cached_tokens = (
                usage.get("prompt_tokens_details", {}) or {}
            ).get("cached_tokens", 0)
        tokens = TokenUsage(
            input_tokens=usage.get("prompt_tokens", usage.get("input_tokens", 0)),
            cached_input_tokens=cached_tokens,
            output_tokens=usage.get("completion_tokens", usage.get("output_tokens", 0)),
        )

        capability = registry.get(planned.model_id)
        cost = _calculate_cost(tokens, capability)
        served_model = str(data.get("model", planned.model_id))
        served_effort = _served_effort(data)

        return ProviderExecutionEvidence(
            requested_provider=selection.provider,
            requested_profile=selection.profile,
            planned_provider=planned.provider,
            planned_model_id=planned.model_id,
            planned_effort=planned.reasoning_effort,
            served_provider=planned.provider,
            served_model_id=served_model,
            # Empty means the provider did not echo verifiable effort evidence.
            served_effort=served_effort,
            safe_provider_request_ref=str(data.get("id", "")),
            attempts=(
                ProviderAttempt(
                    attempt_index=0,
                    provider=planned.provider,
                    model_id=served_model,
                    status="success",
                    latency_ms=elapsed_ms,
                    tokens=tokens,
                    cost_usd=cost,
                ),
            ),
            circuit_state="closed",
            tokens=tokens,
            latency_ms=elapsed_ms,
            cost_usd=cost,
            capability_snapshot_hash=planned.capability_snapshot_hash,
            fallback_used=planned.fallback_used,
            execution_performed=True,
        )
    except urllib.error.HTTPError as exc:
        return _provider_call_failure(
            planned,
            selection,
            started,
            f"http_error:{exc.code}",
        )
    except urllib.error.URLError as exc:
        reason = type(exc.reason).__name__ if exc.reason is not None else "unknown"
        return _provider_call_failure(
            planned,
            selection,
            started,
            f"network_error:{reason}",
        )
    except TimeoutError:
        return _provider_call_failure(planned, selection, started, "timeout")
    except Exception as exc:  # defensive boundary; never persist raw exception text
        return _provider_call_failure(
            planned,
            selection,
            started,
            f"provider_error:{type(exc).__name__}",
        )


def _calculate_cost(
    tokens: TokenUsage,
    capability: Any,
) -> Decimal:
    if capability is None:
        return Decimal("0.0")
    uncached = max(0, tokens.input_tokens - tokens.cached_input_tokens)
    return (
        Decimal(uncached) * capability.pricing.input_price_per_1k_tokens
        + Decimal(tokens.cached_input_tokens)
        * capability.pricing.cached_input_price_per_1k_tokens
        + Decimal(tokens.output_tokens) * capability.pricing.output_price_per_1k_tokens
    ) / Decimal("1000")


def _served_effort(data: dict[str, Any]) -> str:
    direct = data.get("reasoning_effort") or data.get("effort")
    if isinstance(direct, str):
        return direct
    reasoning = data.get("reasoning")
    if isinstance(reasoning, dict) and isinstance(reasoning.get("effort"), str):
        return reasoning["effort"]
    return ""


def _provider_call_failure(
    planned: ResolvedProvider,
    selection: ProviderSelection,
    started: float,
    error_message: str,
) -> ProviderExecutionEvidence:
    elapsed_ms = int((time.monotonic() - started) * 1000)
    status = "timed_out" if error_message == "timeout" else "failed"
    return ProviderExecutionEvidence(
        requested_provider=selection.provider,
        requested_profile=selection.profile,
        planned_provider=planned.provider,
        planned_model_id=planned.model_id,
        planned_effort=planned.reasoning_effort,
        attempts=(
            ProviderAttempt(
                attempt_index=0,
                provider=planned.provider,
                model_id=planned.model_id,
                status=status,
                latency_ms=elapsed_ms,
                error_message=error_message,
            ),
        ),
        circuit_state="open",
        execution_performed=False,
    )


def _failure_evidence(
    selection: ProviderSelection,
    *,
    provider: str,
    error_message: str,
) -> ProviderExecutionEvidence:
    return ProviderExecutionEvidence(
        requested_provider=selection.provider,
        requested_profile=selection.profile,
        served_provider="",
        attempts=(
            ProviderAttempt(
                attempt_index=0,
                provider=provider,
                status="failed",
                error_message=error_message,
            ),
        ),
        circuit_state="open",
        execution_performed=False,
    )
