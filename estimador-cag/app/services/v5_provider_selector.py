"""Provider-route resolution service for Session 13 Plus V5.

Maps the user-facing :class:`ProviderSelection` to a concrete provider,
model, and reasoning effort for a given complexity level and graph stage.
"""

from __future__ import annotations

from app.schemas.v3_routing import ComplexityLevel, ReasoningEffort
from app.schemas.v5_provider_selection import (
    ProviderOption,
    ProviderSelection,
    ReasoningIntent,
)

_VALID_STAGES: set[str] = {
    "complexity",
    "structure",
    "recovery",
    "reliability",
    "proposal",
}

_EFFORT_MAP: dict[ReasoningIntent, ReasoningEffort] = {
    "minimal": "none",
    "medium": "high",
    "max": "max",
}


def _is_high_complexity(level: ComplexityLevel) -> bool:
    return level in {"C3", "C4", "C5"}


def _is_max_complexity(level: ComplexityLevel) -> bool:
    return level == "C5"


def _auto_route(level: ComplexityLevel) -> dict[str, str]:
    """Auto: least expensive verified route for the complexity level."""
    if _is_max_complexity(level):
        return {"provider": "deepseek", "model": "deepseek-v4-pro"}
    if _is_high_complexity(level):
        return {"provider": "deepseek", "model": "deepseek-v4-pro"}
    return {"provider": "deepseek", "model": "deepseek-v4-flash"}


def _deepseek_route(level: ComplexityLevel) -> dict[str, str]:
    if _is_high_complexity(level):
        return {"provider": "deepseek", "model": "deepseek-v4-pro"}
    return {"provider": "deepseek", "model": "deepseek-v4-flash"}


def _kimi_route(level: ComplexityLevel) -> dict[str, str]:
    if _is_max_complexity(level):
        return {"provider": "moonshot", "model": "kimi-k3"}
    if _is_high_complexity(level):
        return {"provider": "moonshot", "model": "kimi-k2.7-code"}
    return {"provider": "moonshot", "model": "kimi-k2.6"}


def _openai_route(level: ComplexityLevel) -> dict[str, str]:
    if _is_max_complexity(level):
        return {"provider": "openai", "model": "gpt-5.6-sol"}
    if _is_high_complexity(level):
        return {"provider": "openai", "model": "gpt-5.6-terra"}
    return {"provider": "openai", "model": "gpt-5.6-luna"}


_PROVIDER_ROUTES: dict[ProviderOption, object] = {
    "auto": _auto_route,
    "deepseek": _deepseek_route,
    "kimi": _kimi_route,
    "openai": _openai_route,
}


def resolve_provider_route(
    *,
    selection: ProviderSelection,
    complexity_level: ComplexityLevel,
    stage: str,
) -> dict[str, str]:
    """Resolve a concrete provider, model, and effort for one graph stage.

    Returns a dict with keys ``provider``, ``model``, and ``effort``.
    """
    if stage not in _VALID_STAGES:
        raise ValueError(
            f"Unknown stage: {stage!r}.  Valid stages: {', '.join(sorted(_VALID_STAGES))}"
        )

    route_fn = _PROVIDER_ROUTES[selection.provider]
    route = route_fn(complexity_level)
    route["effort"] = _EFFORT_MAP[selection.reasoning]
    return route
