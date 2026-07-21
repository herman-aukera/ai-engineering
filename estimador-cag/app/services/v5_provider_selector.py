"""Provider-route preview for Session 13 Plus V5.

The resolver is deterministic policy preview unless supplied an explicitly
promoted registry. It does not claim live reachability or price optimality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.v3_routing import ComplexityLevel, ReasoningEffort
from app.schemas.v5_provider_selection import ProviderOption, ProviderSelection

if TYPE_CHECKING:
    from app.services.v3_model_registry import ModelRegistry

_VALID_STAGES = {"complexity", "structure", "recovery", "reliability", "proposal"}

_DEFAULTS: dict[ProviderOption, tuple[str, list[dict[str, str]]]] = {
    "auto": ("deepseek", [{"model": "deepseek-v4-flash", "tier": "flash"}, {"model": "deepseek-v4-pro", "tier": "pro"}]),
    "deepseek": ("deepseek", [{"model": "deepseek-v4-flash", "tier": "flash"}, {"model": "deepseek-v4-pro", "tier": "pro"}]),
    "kimi": ("moonshot", [{"model": "kimi-for-coding", "tier": "pro"}, {"model": "kimi-for-coding-highspeed", "tier": "pro"}, {"model": "k3", "tier": "max"}]),
    "openai": ("openai", [{"model": "gpt-5.6-luna", "tier": "flash"}, {"model": "gpt-5.6-terra", "tier": "pro"}, {"model": "gpt-5.6-sol", "tier": "max"}]),
}

_TIER_FOR_COMPLEXITY = {"C0": "flash", "C1": "flash", "C2": "flash", "C3": "pro", "C4": "pro", "C5": "max"}


def _select(candidates: list[dict[str, str]], preferred_tier: str) -> dict[str, str] | None:
    for tier in (preferred_tier, "pro", "flash", "max"):
        for candidate in candidates:
            if candidate.get("tier") == tier:
                return dict(candidate)
    return None


def _effort(provider: str, model: str, intent: str) -> ReasoningEffort:
    if provider == "moonshot":
        if model == "k3":
            return {"minimal": "low", "medium": "high", "max": "max"}[intent]
        return "high"
    return {"minimal": "none", "medium": "high", "max": "max"}[intent]


def resolve_provider_route(
    *,
    selection: ProviderSelection,
    complexity_level: ComplexityLevel,
    stage: str,
    registry: ModelRegistry | None = None,
) -> dict[str, str]:
    """Resolve an eligible route or fail closed when a registry has no promotion."""
    if stage not in _VALID_STAGES:
        raise ValueError(f"Unknown stage: {stage!r}. Valid stages: {', '.join(sorted(_VALID_STAGES))}")

    preferred_tier = _TIER_FOR_COMPLEXITY[complexity_level]
    if registry is not None:
        records = registry.list_enabled() if selection.provider == "auto" else registry.list_by_provider(_provider_name(selection.provider))
        candidates = [
            {"provider": record.provider, "model": record.provider_model_id, "tier": record.capability_tier}
            for record in records
            if record.calibration_status == "enabled" and record.availability == "available"
        ]
        chosen = _select(candidates, preferred_tier)
        if chosen is None:
            raise ValueError(
                f"No eligible promoted route for provider={selection.provider}, "
                f"complexity={complexity_level}, stage={stage}"
            )
    else:
        provider, raw = _DEFAULTS[selection.provider]
        chosen = _select(
            [{"provider": provider, "model": item["model"], "tier": item["tier"]} for item in raw],
            preferred_tier,
        )
        if chosen is None:
            raise ValueError(f"No policy preview route for provider={selection.provider}")

    chosen["effort"] = _effort(chosen["provider"], chosen["model"], selection.reasoning)
    chosen["routing_status"] = "promoted" if registry is not None else "preview"
    chosen["stage"] = stage
    return chosen


def _provider_name(option: ProviderOption) -> str:
    return {"deepseek": "deepseek", "kimi": "moonshot", "openai": "openai", "auto": "deepseek"}[option]
