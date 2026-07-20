"""Provider capability registry and selector for EACODE.

Provider-neutral model selection behind fake adapters in deterministic CI.
No live API calls. No provider keys required. Resolves provider/profile
combinations through a versioned capability manifest.

Spec 0010 runtime — additive module. Does not modify existing contracts.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from energy_core.models import EnergyModel

ProviderName = Literal["auto", "deepseek", "kimi", "openai"]
Profile = Literal["minimal", "medium", "max"]
FallbackPolicy = Literal["none", "same_provider", "governed_cross_provider"]
AvailabilityState = Literal["available", "degraded", "unavailable"]


class PricingSnapshot(EnergyModel):
    input_price_per_1k_tokens: Decimal = Field(default=Decimal("0.0"), ge=0)
    cached_input_price_per_1k_tokens: Decimal = Field(default=Decimal("0.0"), ge=0)
    output_price_per_1k_tokens: Decimal = Field(default=Decimal("0.0"), ge=0)


class ModelCapability(EnergyModel):
    """Versioned capability entry for one provider model."""

    provider: str = Field(min_length=1, max_length=80)
    surface: str = Field(default="api", min_length=1, max_length=80)
    model_id: str = Field(min_length=1, max_length=160)
    model_family: str = Field(min_length=1, max_length=160)
    context_window: int = Field(ge=1)
    max_output_tokens: int = Field(ge=1)
    reasoning_modes: tuple[str, ...] = Field(default_factory=tuple)
    reasoning_efforts: tuple[str, ...] = Field(default_factory=tuple)
    speed_class: str = Field(default="medium")
    supports_tools: bool = False
    supports_structured_output: bool = False
    supports_vision: bool = False
    supports_prompt_cache: bool = False
    pricing: PricingSnapshot = Field(default_factory=PricingSnapshot)
    availability_state: AvailabilityState = "available"
    verified_at: datetime = Field(default_factory=lambda: datetime(2026, 7, 19))
    source_version: str = Field(default="1.0.0")


class ProviderSelection(EnergyModel):
    """Provider-neutral model selection request."""

    provider: ProviderName = "auto"
    profile: Profile = "medium"
    context_profile: Profile = "medium"
    fallback_policy: FallbackPolicy = "none"
    max_cost_usd: Decimal = Field(default=Decimal("1.00"), ge=0)
    max_latency_ms: int | None = None


class ResolvedProvider(EnergyModel):
    """Deterministically resolved provider/model/effort result."""

    provider: str
    model_id: str
    reasoning_mode: str
    reasoning_effort: str
    profile: Profile
    estimated_cost_ceiling_usd: Decimal
    capability_snapshot_hash: str
    fallback_used: bool = False
    fallback_reason: str | None = None


# ------------------------------------------------------------------
# Curated capability registry (2026-07-19 verified)
# ------------------------------------------------------------------

_DEFAULT_REGISTRY: dict[str, ModelCapability] = {}


def _build_default_registry() -> dict[str, ModelCapability]:
    """Build the curated capability manifest from verified provider documentation.

    Fact-based entries only. No invented capabilities. Unknown/unsupported
    combinations fail closed.
    """

    def _add(cap: ModelCapability) -> None:
        _DEFAULT_REGISTRY[cap.model_id] = cap

    # --- DeepSeek ---

    _add(ModelCapability(
        provider="deepseek",
        model_id="deepseek-v4-flash",
        model_family="deepseek-v4",
        context_window=128_000,
        max_output_tokens=8_192,
        reasoning_modes=("thinking", "non-thinking"),
        reasoning_efforts=("high", "max"),
        speed_class="fast",
        supports_tools=True,
        supports_structured_output=True,
        supports_prompt_cache=False,
        pricing=PricingSnapshot(
            input_price_per_1k_tokens=Decimal("0.00014"),
            output_price_per_1k_tokens=Decimal("0.00028"),
        ),
        verified_at=datetime(2026, 7, 19),
    ))

    _add(ModelCapability(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        model_family="deepseek-v4",
        context_window=128_000,
        max_output_tokens=8_192,
        reasoning_modes=("thinking", "non-thinking"),
        reasoning_efforts=("high", "max"),
        speed_class="balanced",
        supports_tools=True,
        supports_structured_output=True,
        supports_prompt_cache=False,
        pricing=PricingSnapshot(
            input_price_per_1k_tokens=Decimal("0.00055"),
            output_price_per_1k_tokens=Decimal("0.00219"),
        ),
        verified_at=datetime(2026, 7, 19),
    ))

    # --- Kimi ---

    _add(ModelCapability(
        provider="kimi",
        model_id="kimi-k3",
        model_family="kimi-k3",
        context_window=1_000_000,
        max_output_tokens=8_192,
        reasoning_modes=("thinking",),
        reasoning_efforts=("max",),
        speed_class="balanced",
        supports_tools=True,
        supports_structured_output=True,
        supports_vision=True,
        supports_prompt_cache=False,
        pricing=PricingSnapshot(
            input_price_per_1k_tokens=Decimal("0.00060"),
            output_price_per_1k_tokens=Decimal("0.00240"),
        ),
        verified_at=datetime(2026, 7, 19),
    ))

    _add(ModelCapability(
        provider="kimi",
        model_id="kimi-for-coding",
        model_family="kimi-coding",
        context_window=128_000,
        max_output_tokens=8_192,
        reasoning_modes=("thinking", "non-thinking"),
        reasoning_efforts=("medium", "high"),
        speed_class="fast",
        supports_tools=True,
        supports_structured_output=True,
        supports_prompt_cache=False,
        pricing=PricingSnapshot(
            input_price_per_1k_tokens=Decimal("0.00030"),
            output_price_per_1k_tokens=Decimal("0.00120"),
        ),
        verified_at=datetime(2026, 7, 19),
    ))

    # --- OpenAI ---

    _add(ModelCapability(
        provider="openai",
        model_id="gpt-5.6-luna",
        model_family="gpt-5.6",
        context_window=128_000,
        max_output_tokens=16_384,
        reasoning_modes=("thinking", "non-thinking"),
        reasoning_efforts=("none", "low", "medium", "high", "xhigh", "max"),
        speed_class="fast",
        supports_tools=True,
        supports_structured_output=True,
        supports_vision=True,
        supports_prompt_cache=True,
        pricing=PricingSnapshot(
            input_price_per_1k_tokens=Decimal("0.00015"),
            cached_input_price_per_1k_tokens=Decimal("0.00008"),
            output_price_per_1k_tokens=Decimal("0.00060"),
        ),
        verified_at=datetime(2026, 7, 19),
    ))

    _add(ModelCapability(
        provider="openai",
        model_id="gpt-5.6-terra",
        model_family="gpt-5.6",
        context_window=128_000,
        max_output_tokens=16_384,
        reasoning_modes=("thinking", "non-thinking"),
        reasoning_efforts=("none", "low", "medium", "high", "xhigh", "max"),
        speed_class="balanced",
        supports_tools=True,
        supports_structured_output=True,
        supports_vision=True,
        supports_prompt_cache=True,
        pricing=PricingSnapshot(
            input_price_per_1k_tokens=Decimal("0.00150"),
            cached_input_price_per_1k_tokens=Decimal("0.00075"),
            output_price_per_1k_tokens=Decimal("0.00600"),
        ),
        verified_at=datetime(2026, 7, 19),
    ))

    _add(ModelCapability(
        provider="openai",
        model_id="gpt-5.6-sol",
        model_family="gpt-5.6",
        context_window=128_000,
        max_output_tokens=16_384,
        reasoning_modes=("thinking", "non-thinking"),
        reasoning_efforts=("none", "low", "medium", "high", "xhigh", "max"),
        speed_class="premium",
        supports_tools=True,
        supports_structured_output=True,
        supports_vision=True,
        supports_prompt_cache=True,
        pricing=PricingSnapshot(
            input_price_per_1k_tokens=Decimal("0.00300"),
            cached_input_price_per_1k_tokens=Decimal("0.00150"),
            output_price_per_1k_tokens=Decimal("0.01200"),
        ),
        verified_at=datetime(2026, 7, 19),
    ))

    return dict(_DEFAULT_REGISTRY)


# ------------------------------------------------------------------
# Profile-to-model mapping (deterministic)
# ------------------------------------------------------------------

_PROFILE_MAP: dict[tuple[str, Profile], str] = {
    ("deepseek", "minimal"): "deepseek-v4-flash",
    ("deepseek", "medium"): "deepseek-v4-flash",
    ("deepseek", "max"): "deepseek-v4-pro",
    ("kimi", "minimal"): "kimi-for-coding",
    ("kimi", "medium"): "kimi-for-coding",
    ("kimi", "max"): "kimi-k3",
    ("openai", "minimal"): "gpt-5.6-luna",
    ("openai", "medium"): "gpt-5.6-terra",
    ("openai", "max"): "gpt-5.6-sol",
}

_EFFORT_MAP: dict[tuple[str, Profile], str] = {
    ("deepseek", "minimal"): "high",
    ("deepseek", "medium"): "high",
    ("deepseek", "max"): "max",
    ("kimi", "minimal"): "medium",
    ("kimi", "medium"): "high",
    ("kimi", "max"): "max",
    ("openai", "minimal"): "low",
    ("openai", "medium"): "medium",
    ("openai", "max"): "max",
}

_MODE_MAP: dict[tuple[str, Profile], str] = {
    ("deepseek", "minimal"): "non-thinking",
    ("deepseek", "medium"): "thinking",
    ("deepseek", "max"): "thinking",
    ("kimi", "minimal"): "thinking",
    ("kimi", "medium"): "thinking",
    ("kimi", "max"): "thinking",
    ("openai", "minimal"): "non-thinking",
    ("openai", "medium"): "thinking",
    ("openai", "max"): "thinking",
}

_DEFAULT_PROVIDER = "deepseek"


# ------------------------------------------------------------------
# Capability registry
# ------------------------------------------------------------------


class CapabilityRegistry:
    """Versioned capability registry with deterministic resolution.

    Does not call any live API. Capabilities are curated from verified
    provider documentation. Unknown or unsupported combinations fail closed.
    """

    def __init__(self, capabilities: dict[str, ModelCapability] | None = None) -> None:
        self._capabilities = capabilities or _build_default_registry()

    def get(self, model_id: str) -> ModelCapability | None:
        """Get one capability entry by model_id. Returns None if unknown."""
        return self._capabilities.get(model_id)

    def list_provider_models(self, provider: str) -> list[ModelCapability]:
        """List all registered capability entries for a provider."""
        return sorted(
            (c for c in self._capabilities.values() if c.provider == provider),
            key=lambda c: c.model_id,
        )

    def list_available_models(self) -> list[ModelCapability]:
        """List all registered models with availability_state=available."""
        return sorted(
            (c for c in self._capabilities.values()
             if c.availability_state == "available"),
            key=lambda c: (c.provider, c.model_id),
        )

    # ------------------------------------------------------------------
    # Profile resolution
    # ------------------------------------------------------------------

    def resolve_profile(
        self,
        provider: str,
        profile: Profile,
    ) -> tuple[str, str, str]:
        """Resolve provider+profile to (model_id, reasoning_mode, reasoning_effort).

        Raises ValueError if the combination is unsupported.
        """
        key = (provider, profile)
        model_id = _PROFILE_MAP.get(key)
        if model_id is None:
            raise ValueError(
                f"Unsupported provider/profile combination: {provider}/{profile}"
            )

        cap = self.get(model_id)
        if cap is None or cap.availability_state == "unavailable":
            raise ValueError(
                f"Model {model_id} is unavailable for provider {provider}"
            )

        effort = _EFFORT_MAP.get(key, "medium")
        mode = _MODE_MAP.get(key, "thinking")

        # Validate effort is in the capability's supported efforts
        if effort not in cap.reasoning_efforts:
            raise ValueError(
                f"Effort '{effort}' not supported by {model_id}. "
                f"Supported: {cap.reasoning_efforts}"
            )

        if mode not in cap.reasoning_modes and cap.reasoning_modes:
            raise ValueError(
                f"Mode '{mode}' not supported by {model_id}. "
                f"Supported: {cap.reasoning_modes}"
            )

        return model_id, mode, effort


# ------------------------------------------------------------------
# Provider selector
# ------------------------------------------------------------------


class ProviderSelector:
    """Deterministic provider selector with budget-aware auto-routing.

    Does not make live API calls. Produces a ResolvedProvider from a
    ProviderSelection using the capability registry.
    """

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self._registry = registry or CapabilityRegistry()

    def select(self, selection: ProviderSelection) -> ResolvedProvider:
        """Resolve a ProviderSelection to a specific model/effort.

        In 'auto' mode, follows the default routing policy:
        1. DeepSeek for normal cost-sensitive work
        2. Kimi for quality-sensitive / open-frontier preference
        3. OpenAI only for explicit premium escalation
        """
        provider = selection.provider
        fallback_used = False
        fallback_reason: str | None = None

        if provider == "auto":
            # Default routing: DeepSeek first
            provider = _DEFAULT_PROVIDER

        try:
            model_id, mode, effort = self._registry.resolve_profile(
                provider, selection.profile
            )
        except ValueError:
            if selection.fallback_policy == "none":
                raise
            # Try fallback
            if selection.fallback_policy == "same_provider":
                raise ValueError(
                    f"Cannot resolve {provider}/{selection.profile} "
                    "and fallback_policy=same_provider"
                )
            # governed_cross_provider: try next in routing order
            fallback_order = _FALLBACK_ORDER.get(provider, [_DEFAULT_PROVIDER])
            resolved = False
            for fb_provider in fallback_order:
                try:
                    model_id, mode, effort = self._registry.resolve_profile(
                        fb_provider, selection.profile
                    )
                    provider = fb_provider
                    fallback_used = True
                    fallback_reason = (
                        f"Primary provider {selection.provider} could not resolve "
                        f"profile {selection.profile}; fell back to {fb_provider}"
                    )
                    resolved = True
                    break
                except ValueError:
                    continue
            if not resolved:
                raise ValueError(
                    f"Cannot resolve any provider for profile {selection.profile}"
                )

        # Cost ceiling: check if the resolved model exceeds budget
        cap = self._registry.get(model_id)
        if cap is not None:
            # Rough estimate: model cost per call
            est_cost = cap.pricing.input_price_per_1k_tokens * 100  # assume ~100k tokens
            if est_cost > selection.max_cost_usd and provider == "openai":
                raise ValueError(
                    f"OpenAI escalation exceeds budget ceiling "
                    f"(${est_cost:.4f} > ${selection.max_cost_usd:.4f})"
                )

        import hashlib
        import json
        cap_hash = hashlib.sha256(
            json.dumps(
                {
                    "provider": provider,
                    "model_id": model_id,
                    "mode": mode,
                    "effort": effort,
                    "profile": selection.profile,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

        return ResolvedProvider(
            provider=provider,
            model_id=model_id,
            reasoning_mode=mode,
            reasoning_effort=effort,
            profile=selection.profile,
            estimated_cost_ceiling_usd=selection.max_cost_usd,
            capability_snapshot_hash=cap_hash,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )


_FALLBACK_ORDER: dict[str, list[str]] = {
    "deepseek": ["kimi", "openai"],
    "kimi": ["deepseek", "openai"],
    "openai": ["deepseek", "kimi"],
}
