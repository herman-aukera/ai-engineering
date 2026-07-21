"""Selector API — FastAPI router for provider selection and capability queries.

Exposes the deterministic registry and selector as HTTP endpoints.
Zero live API calls. Works with the curated capability manifest.
Disabled-by-default live adapter endpoints require explicit opt-in.

Spec 0010 Slice G — additive module.
"""

from __future__ import annotations  # noqa: I001

from decimal import Decimal

from pydantic import BaseModel, Field

from energy_core.provider_registry import (
    CapabilityRegistry,
    ProviderSelection,
    ProviderSelector,
)


# ------------------------------------------------------------------
# API response models
# ------------------------------------------------------------------


class ModelSummary(BaseModel):
    provider: str
    surface: str
    model_id: str
    aliases: list[str]
    model_family: str
    context_window: int
    max_output_tokens: int
    reasoning_efforts: list[str]
    speed_class: str
    supports_prompt_cache: bool
    availability_state: str
    entitlement_state: str
    freshness_state: str


class ResolvedRoute(BaseModel):
    provider: str
    resolved_surface: str
    model_id: str
    reasoning_mode: str
    reasoning_effort: str
    profile: str
    capability_snapshot_hash: str
    fallback_used: bool
    fallback_reason: str | None


class SelectRequest(BaseModel):
    provider: str = "auto"
    profile: str = "medium"
    context_profile: str = "medium"
    fallback_policy: str = "none"
    expected_input_tokens: int = Field(default=50_000, ge=1)
    expected_output_tokens: int = Field(default=4_000, ge=1)
    max_cost_usd: Decimal = Field(default=Decimal("1.00"), ge=0)
    premium_reason: str | None = None


class SelectResponse(BaseModel):
    status: str  # ok, error
    route: ResolvedRoute | None = None
    available_models: list[ModelSummary] = Field(default_factory=list)
    error: str | None = None


class CapabilityDetail(BaseModel):
    provider: str
    surface: str
    model_id: str
    aliases: list[str]
    model_family: str
    context_window: int
    max_output_tokens: int
    reasoning_modes: list[str]
    reasoning_efforts: list[str]
    speed_class: str
    supports_tools: bool
    supports_structured_output: bool
    supports_vision: bool
    supports_prompt_cache: bool
    pricing: dict[str, str]
    availability_state: str
    entitlement_state: str
    freshness_state: str
    source_id: str
    source_version: str


# ------------------------------------------------------------------
# Selector API
# ------------------------------------------------------------------


class SelectorAPI:
    """HTTP-friendly wrapper around the deterministic provider selector.

    Exposes capability queries and route resolution. Does not make live
    provider calls — returns planned routes only.
    """

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self._registry = registry or CapabilityRegistry()
        self._selector = ProviderSelector(self._registry)

    def list_models(self) -> list[ModelSummary]:
        return [
            ModelSummary(
                provider=m.provider,
                surface=m.surface,
                model_id=m.model_id,
                aliases=list(m.aliases),
                model_family=m.model_family,
                context_window=m.context_window,
                max_output_tokens=m.max_output_tokens,
                reasoning_efforts=list(m.reasoning_efforts),
                speed_class=m.speed_class,
                supports_prompt_cache=m.supports_prompt_cache,
                availability_state=m.availability_state,
                entitlement_state=m.entitlement_state,
                freshness_state=m.freshness_state,
            )
            for m in self._registry.list_available_models()
        ]

    def get_model(self, model_id: str) -> CapabilityDetail | None:
        cap = self._registry.get(model_id)
        if cap is None:
            return None
        return CapabilityDetail(
            provider=cap.provider,
            surface=cap.surface,
            model_id=cap.model_id,
            aliases=list(cap.aliases),
            model_family=cap.model_family,
            context_window=cap.context_window,
            max_output_tokens=cap.max_output_tokens,
            reasoning_modes=list(cap.reasoning_modes),
            reasoning_efforts=list(cap.reasoning_efforts),
            speed_class=cap.speed_class,
            supports_tools=cap.supports_tools,
            supports_structured_output=cap.supports_structured_output,
            supports_vision=cap.supports_vision,
            supports_prompt_cache=cap.supports_prompt_cache,
            pricing={
                "input_per_1k": str(cap.pricing.input_price_per_1k_tokens),
                "cached_input_per_1k": str(cap.pricing.cached_input_price_per_1k_tokens),
                "output_per_1k": str(cap.pricing.output_price_per_1k_tokens),
                "unit": cap.pricing.price_unit,
            },
            availability_state=cap.availability_state,
            entitlement_state=cap.entitlement_state,
            freshness_state=cap.freshness_state,
            source_id=cap.source_id,
            source_version=cap.source_version,
        )

    def select(self, request: SelectRequest) -> SelectResponse:
        try:
            selection = ProviderSelection(
                provider=request.provider,
                profile=request.profile,
                context_profile=request.context_profile,
                fallback_policy=request.fallback_policy,
                expected_input_tokens=request.expected_input_tokens,
                expected_output_tokens=request.expected_output_tokens,
                max_cost_usd=request.max_cost_usd,
                premium_reason=request.premium_reason,
            )
            planned = self._selector.select(selection)
            route = ResolvedRoute(
                provider=planned.provider,
                resolved_surface=planned.resolved_surface,
                model_id=planned.model_id,
                reasoning_mode=planned.reasoning_mode,
                reasoning_effort=planned.reasoning_effort,
                profile=planned.profile,
                capability_snapshot_hash=planned.capability_snapshot_hash,
                fallback_used=planned.fallback_used,
                fallback_reason=planned.fallback_reason,
            )
            return SelectResponse(
                status="ok",
                route=route,
                available_models=self.list_models(),
            )
        except ValueError as exc:
            return SelectResponse(
                status="error",
                error=str(exc),
                available_models=self.list_models(),
            )
