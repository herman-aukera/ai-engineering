"""Opt-in live provider adapters for EACODE.

Requires explicit opt-in and valid API keys. Never called in deterministic CI.
Produces served-model evidence with exact provider, model, effort, tokens,
latency, and cost. Falls back gracefully when keys are missing.

Spec 0010 Slice E — live adapter infrastructure.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from decimal import Decimal

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
    ProviderSelector,
    ResolvedProvider,
)


class LiveAdapterConfig(EnergyModel):
    """Configuration for a live provider adapter.

    enabled defaults to False — must be explicitly opted into.
    api_key_env_var names the environment variable for the provider key.
    """

    model_config = {"arbitrary_types_allowed": True, "extra": "forbid"}

    enabled: bool = False
    provider: str = ""
    api_key_env_var: str = ""
    api_base_url: str = ""
    registry: CapabilityRegistry | None = None


class BaseLiveAdapter:
    """Base class for live provider adapters.

    Subclass for each provider. Requires enabled=True and a valid API key.
    Falls back to FakeProviderAdapter when disabled or key is missing.
    """

    def __init__(self, config: LiveAdapterConfig) -> None:
        self.config = config
        self._registry = config.registry or CapabilityRegistry()
        self._selector = ProviderSelector(self._registry)
        self._fake = FakeProviderAdapter(registry=self._registry)
        self.calls = 0

    def invoke(
        self,
        selection: ProviderSelection,
        *,
        messages: list[dict[str, str]] | None = None,
    ) -> ProviderExecutionEvidence:
        """Call the provider if enabled and key is available.

        Returns fake evidence when disabled or key is missing.
        """
        self.calls += 1

        if not self.config.enabled:
            return self._fake.invoke(selection, messages=messages)

        api_key = os.environ.get(self.config.api_key_env_var, "")
        if not api_key:
            return ProviderExecutionEvidence(
                requested_provider=selection.provider,
                requested_profile=selection.profile,
                served_provider="",
                attempts=(
                    ProviderAttempt(
                        attempt_index=0,
                        provider=self.config.provider,
                        status="failed",
                        error_message=f"API key not found: {self.config.api_key_env_var}",
                    ),
                ),
                circuit_state="open",
                execution_performed=False,
            )

        try:
            planned = self._selector.select(selection)
        except ValueError as exc:
            return ProviderExecutionEvidence(
                requested_provider=selection.provider,
                requested_profile=selection.profile,
                attempts=(
                    ProviderAttempt(
                        attempt_index=0,
                        provider=self.config.provider,
                        status="failed",
                        error_message=str(exc),
                    ),
                ),
                circuit_state="open",
                execution_performed=False,
            )

        return self._call_provider(planned, selection, messages, api_key)

    def _call_provider(
        self,
        planned: ResolvedProvider,
        selection: ProviderSelection,
        messages: list[dict[str, str]] | None,
        api_key: str,
    ) -> ProviderExecutionEvidence:
        """Override in subclass to make the actual API call."""
        raise NotImplementedError("Subclass must implement _call_provider")


class DeepSeekAdapter(BaseLiveAdapter):
    """Opt-in DeepSeek API adapter. Requires DEEPSEEK_API_KEY and enabled=True."""

    def _call_provider(
        self,
        planned: ResolvedProvider,
        selection: ProviderSelection,
        messages: list[dict[str, str]] | None,
        api_key: str,
    ) -> ProviderExecutionEvidence:
        base_url = self.config.api_base_url or "https://api.deepseek.com"
        return _openai_compatible_call(
            planned, selection, messages, api_key, base_url, self._registry
        )


class KimiCodeAdapter(BaseLiveAdapter):
    """Opt-in Kimi Code adapter. Requires KIMI_API_KEY and enabled=True.

    Membership-based billing — registry pricing may be zero for entitled users.
    Model/effort switches invalidate prompt-cache; start a fresh session.
    """

    def _call_provider(
        self,
        planned: ResolvedProvider,
        selection: ProviderSelection,
        messages: list[dict[str, str]] | None,
        api_key: str,
    ) -> ProviderExecutionEvidence:
        base_url = self.config.api_base_url or "https://api.moonshot.cn"
        return _openai_compatible_call(
            planned, selection, messages, api_key, base_url, self._registry
        )


class OpenAIAdapter(BaseLiveAdapter):
    """Opt-in OpenAI GPT-5.6 adapter. Requires OPENAI_API_KEY and enabled=True.

    Budget-gated premium escalation — max/escalation profiles require
    explicit premium_reason on the ProviderSelection.
    """

    def _call_provider(
        self,
        planned: ResolvedProvider,
        selection: ProviderSelection,
        messages: list[dict[str, str]] | None,
        api_key: str,
    ) -> ProviderExecutionEvidence:
        base_url = self.config.api_base_url or "https://api.openai.com"
        return _openai_compatible_call(
            planned, selection, messages, api_key, base_url, self._registry
        )


# ------------------------------------------------------------------
# Shared OpenAI-compatible HTTP call helper
# ------------------------------------------------------------------


def _openai_compatible_call(
    planned: ResolvedProvider,
    selection: ProviderSelection,
    messages: list[dict[str, str]] | None,
    api_key: str,
    base_url: str,
    registry: CapabilityRegistry,
) -> ProviderExecutionEvidence:
    """Make an OpenAI-compatible chat completions call and return evidence."""
    msgs = messages or [{"role": "user", "content": "Hello"}]
    body = json.dumps({
        "model": planned.model_id,
        "messages": msgs,
        "max_tokens": min(selection.expected_output_tokens, 4096),
        "temperature": 0.0 if planned.reasoning_mode == "non-thinking" else 0.7,
    }).encode("utf-8")

    url = f"{base_url}/v1/chat/completions"
    started = time.monotonic()

    try:
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req, timeout=selection.max_latency_ms or 60000)
        raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        elapsed_ms = int((time.monotonic() - started) * 1000)

        usage = data.get("usage", {})
        tokens = TokenUsage(
            input_tokens=usage.get("prompt_tokens", 0),
            cached_input_tokens=usage.get("prompt_cache_hit_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )

        cap = registry.get(planned.model_id)
        cost = Decimal("0.0")
        if cap is not None:
            uncached = max(0, tokens.input_tokens - tokens.cached_input_tokens)
            cost = (
                Decimal(str(uncached)) * cap.pricing.input_price_per_1k_tokens
                + Decimal(str(tokens.cached_input_tokens)) * cap.pricing.cached_input_price_per_1k_tokens
                + Decimal(str(tokens.output_tokens)) * cap.pricing.output_price_per_1k_tokens
            ) / 1000

        served_model = data.get("model", planned.model_id)

        return ProviderExecutionEvidence(
            requested_provider=selection.provider,
            requested_profile=selection.profile,
            planned_provider=planned.provider,
            planned_model_id=planned.model_id,
            planned_effort=planned.reasoning_effort,
            served_provider=planned.provider,
            served_model_id=served_model,
            served_effort=planned.reasoning_effort,
            safe_provider_request_ref=data.get("id", ""),
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

    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return ProviderExecutionEvidence(
            requested_provider=selection.provider,
            requested_profile=selection.profile,
            planned_provider=planned.provider,
            planned_model_id=planned.model_id,
            attempts=(
                ProviderAttempt(
                    attempt_index=0,
                    provider=planned.provider,
                    model_id=planned.model_id,
                    status="failed",
                    latency_ms=elapsed_ms,
                    error_message=str(exc),
                ),
            ),
            circuit_state="open",
            execution_performed=False,
        )
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return ProviderExecutionEvidence(
            requested_provider=selection.provider,
            requested_profile=selection.profile,
            planned_provider=planned.provider,
            planned_model_id=planned.model_id,
            attempts=(
                ProviderAttempt(
                    attempt_index=0,
                    provider=planned.provider,
                    model_id=planned.model_id,
                    status="timed_out" if "timeout" in str(exc).lower() else "failed",
                    latency_ms=elapsed_ms,
                    error_message=str(exc),
                ),
            ),
            circuit_state="open",
            execution_performed=False,
        )
