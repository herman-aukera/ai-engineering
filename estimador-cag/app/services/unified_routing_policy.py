"""Evidence-aligned route-plan adaptation for the consolidated graph."""

from __future__ import annotations

import hashlib
import json

from app.schemas.session14_plus_policy import ModelCapabilityRegistry
from app.schemas.v3_routing import (
    ComplexityAssessment,
    ExecutionProfileV3,
    ModelRoute,
    ModelRoutingPlan,
    ReasoningEffort,
    RoutingStage,
)
from app.services.session14_plus_policy import (
    resolve_capability,
    validate_routing_plan_capabilities,
)
from app.services.v3_complexity_router import build_model_routing_plan

UNIFIED_ROUTING_POLICY_VERSION = "session13_14_plus.unified-routing.v1"
UNIFIED_CALIBRATION_VERSION = "session13-plus-live-v1"


def _route_reference_id(
    *,
    stage: RoutingStage,
    provider: str,
    model: str,
    effort: ReasoningEffort,
    fallback: bool,
) -> str:
    payload = {
        "stage": stage,
        "provider": provider,
        "model": model,
        "effort": effort,
        "fallback": fallback,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:20]
    return f"route:{digest}"


def _primary_route(route: ModelRoute) -> ModelRoute:
    provider = route.provider
    model = route.model
    effort = route.effort

    if provider == "moonshot":
        model = "kimi-k3"
        effort = "high" if route.effort != "max" else "max"
    elif provider == "deepseek" and model == "deepseek-v4-pro":
        effort = "max" if route.mode == "thinking" else "none"

    return route.model_copy(
        update={
            "provider": provider,
            "model": model,
            "effort": effort,
            "route_id": _route_reference_id(
                stage=route.stage,
                provider=provider,
                model=model,
                effort=effort,
                fallback=False,
            ),
            "fallback_route_ids": [],
            "reason_codes": [
                *route.reason_codes,
                f"unified-policy:{UNIFIED_ROUTING_POLICY_VERSION}",
                f"calibration:{UNIFIED_CALIBRATION_VERSION}",
            ],
        }
    )


def _fallback_for(route: ModelRoute) -> dict[str, str] | None:
    if route.provider == "python":
        return None
    if route.provider == "moonshot":
        provider = "deepseek"
        model = "deepseek-v4-pro"
        effort: ReasoningEffort = "max"
    else:
        provider = "moonshot"
        model = "kimi-k3"
        effort = "max" if route.effort == "max" else "high"
    return {
        "kind": "fallback",
        "stage": route.stage,
        "route_id": _route_reference_id(
            stage=route.stage,
            provider=provider,
            model=model,
            effort=effort,
            fallback=True,
        ),
        "provider": provider,
        "model": model,
        "effort": effort,
        "max_output_tokens": str(route.max_output_tokens),
        "tool_call_limit": str(route.tool_call_limit),
    }


def build_unified_model_routing_plan(
    assessment: ComplexityAssessment,
    *,
    profile: ExecutionProfileV3 = "balanced",
) -> ModelRoutingPlan:
    """Adapt the V3 prior to exact benchmark-calibrated product routes."""

    baseline = build_model_routing_plan(assessment, profile=profile)
    routes: dict[RoutingStage, ModelRoute] = {}
    overrides: list[dict[str, str]] = []
    for stage, raw_route in baseline.routes_by_stage.items():
        route = _primary_route(raw_route)
        fallback = _fallback_for(route)
        if fallback is not None:
            route = route.model_copy(
                update={"fallback_route_ids": [fallback["route_id"]]}
            )
            overrides.append(fallback)
        routes[stage] = route

    payload = {
        "policy_version": UNIFIED_ROUTING_POLICY_VERSION,
        "calibration_dataset_version": UNIFIED_CALIBRATION_VERSION,
        "profile": profile,
        "complexity": assessment.model_dump(mode="json"),
        "routes": {
            stage: route.model_dump(mode="json")
            for stage, route in routes.items()
        },
        "overrides": overrides,
    }
    plan_id = "route-plan:" + hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()[:24]
    return ModelRoutingPlan(
        plan_id=plan_id,
        policy_version=UNIFIED_ROUTING_POLICY_VERSION,
        calibration_dataset_version=UNIFIED_CALIBRATION_VERSION,
        profile=profile,
        project_complexity=assessment,
        routes_by_stage=routes,
        overrides=overrides,
    )


def validate_unified_routing_plan_capabilities(
    plan: ModelRoutingPlan,
    registry: ModelCapabilityRegistry,
) -> dict[str, str]:
    """Authorize every primary and fallback route against exact capabilities."""

    authorized = validate_routing_plan_capabilities(plan, registry)
    fallback_ids = {
        route_id
        for route in plan.routes_by_stage.values()
        for route_id in route.fallback_route_ids
    }
    fallback_overrides = {
        item.get("route_id", ""): item
        for item in plan.overrides
        if item.get("kind") == "fallback"
    }
    if set(fallback_overrides) != fallback_ids:
        raise ValueError(
            "routing plan fallback IDs must match explicit fallback contracts"
        )

    for stage, route in plan.routes_by_stage.items():
        for route_id in route.fallback_route_ids:
            fallback = fallback_overrides[route_id]
            if fallback.get("stage") != stage:
                raise ValueError(f"fallback stage mismatch: {route_id}")
            provider = fallback.get("provider", "")
            model = fallback.get("model", "")
            effort = fallback.get("effort", "")
            record = resolve_capability(
                registry,
                provider=provider,
                model=model,
            )
            if not record.enabled:
                raise ValueError(
                    f"fallback route is not enabled: {provider}/{model}"
                )
            max_output_tokens = int(fallback.get("max_output_tokens", "0"))
            if max_output_tokens > record.max_output_tokens:
                raise ValueError(
                    f"fallback output exceeds capability: {provider}/{model}"
                )
            if effort not in record.reasoning_efforts:
                raise ValueError(
                    f"unsupported fallback effort: {provider}/{model}/{effort}"
                )
            tool_call_limit = int(fallback.get("tool_call_limit", "0"))
            if tool_call_limit > 0 and not record.supports_tools:
                raise ValueError(
                    f"fallback requires unsupported tools: {provider}/{model}"
                )
            authorized[f"{stage}:fallback:{route_id}"] = record.record_id
    return authorized
