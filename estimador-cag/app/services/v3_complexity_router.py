"""Deterministic complexity baseline and adaptive routing policy for Session 13 V3."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from app.schemas.v3_routing import (
    ComplexityAssessment,
    ComplexityLevel,
    ComplexitySignals,
    ExecutionProfileV3,
    ModelMode,
    ModelRoute,
    ModelRoutingPlan,
    ReasoningEffort,
    RoutingStage,
)

CLASSIFIER_VERSION = "session13-v3-deterministic-features-1.0.0"
ROUTING_POLICY_VERSION = "session13-v3-routing-1.0.0"
CALIBRATION_DATASET_VERSION = "unmeasured-policy-prior-1"


@dataclass(frozen=True)
class _RouteSpec:
    provider: str
    model: str
    mode: ModelMode
    effort: ReasoningEffort
    max_output_tokens: int
    timeout_ms: int
    tool_call_limit: int
    cost_limit_usd: float
    fallback_models: tuple[str, ...] = ()


def assess_complexity(
    signals: ComplexitySignals,
    *,
    missing_information: list[str] | None = None,
    detected_languages: list[str] | None = None,
) -> ComplexityAssessment:
    """Calculate a deterministic C0-C5 baseline from explicit project signals."""

    dimensions = {
        "scope": min(
            20,
            signals.requirement_count * 2
            + signals.non_functional_requirement_count * 2
            + (4 if signals.workflow_state_complexity else 0),
        ),
        "integrations": min(20, signals.integration_count * 5),
        "risk": min(
            20,
            (12 if signals.compliance_or_security_critical else 0)
            + (8 if signals.data_migration_required else 0),
        ),
        "ambiguity": min(
            15,
            signals.ambiguous_requirement_count * 2
            + signals.missing_information_count * 2
            + signals.contradiction_count * 4,
        ),
        "evidence": min(
            15,
            (9 if signals.evidence_scarcity else 0) + (6 if signals.novel_domain else 0),
        ),
        "input": min(
            10,
            signals.attachment_count
            + max(0, signals.detected_language_count - 1) * 2
            + min(5, signals.transcript_chars // 10_000),
        ),
    }
    score = min(100, sum(dimensions.values()))
    critical_override = (
        signals.compliance_or_security_critical
        and (signals.contradiction_count > 0 or signals.missing_information_count >= 3)
    ) or (signals.data_migration_required and signals.integration_count >= 4)
    level = _level_for_score(score, critical_override=critical_override)

    uncertainty_units = (
        signals.ambiguous_requirement_count
        + signals.missing_information_count
        + signals.contradiction_count * 2
    )
    confidence = round(max(0.4, 1.0 - min(0.6, uncertainty_units * 0.05)), 2)
    reasons = _reason_codes(signals, level)
    return ComplexityAssessment(
        level=level,
        score=score,
        confidence=confidence,
        dimensions=dimensions,
        reasons=reasons,
        missing_information=list(missing_information or []),
        detected_languages=list(detected_languages or []),
        classifier_version=CLASSIFIER_VERSION,
        human_review_required=level == "C5",
    )


def build_model_routing_plan(
    assessment: ComplexityAssessment,
    *,
    profile: ExecutionProfileV3 = "balanced",
    authoritative_level: ComplexityLevel | None = None,
) -> ModelRoutingPlan:
    """Build a deterministic per-stage plan from explicit routing authority.

    ``assessment`` remains the immutable deterministic evidence record.  A
    separately arbitrated level may control routing without fabricating a
    contradictory score/dimension assessment.
    """

    effective_level = authoritative_level or assessment.level
    routes: dict[RoutingStage, ModelRoute] = {}
    for stage in ("complexity", "structure", "recovery", "reliability", "proposal"):
        spec = _route_spec(stage, effective_level, profile)
        route_id = _route_id(stage, spec)
        fallback_ids = [
            _fallback_route_id(stage, provider, model)
            for provider, model in _providers(spec.fallback_models)
        ]
        routes[stage] = ModelRoute(
            route_id=route_id,
            stage=stage,
            provider=spec.provider,
            model=spec.model,
            mode=spec.mode,
            effort=spec.effort,
            max_output_tokens=spec.max_output_tokens,
            timeout_ms=spec.timeout_ms,
            tool_call_limit=spec.tool_call_limit,
            cost_limit_usd=_profile_cost(spec.cost_limit_usd, profile),
            fallback_route_ids=fallback_ids,
            reason_codes=[
                f"complexity:{effective_level}",
                f"profile:{profile}",
                f"policy:{ROUTING_POLICY_VERSION}",
            ],
        )

    plan_payload = {
        "policy_version": ROUTING_POLICY_VERSION,
        "calibration_dataset_version": CALIBRATION_DATASET_VERSION,
        "profile": profile,
        "complexity": assessment.model_dump(mode="json"),
        "authoritative_level": effective_level,
        "routes": {stage: route.model_dump(mode="json") for stage, route in routes.items()},
    }
    plan_id = (
        "route-plan:"
        + hashlib.sha256(_canonical_json(plan_payload).encode()).hexdigest()[:24]
    )
    return ModelRoutingPlan(
        plan_id=plan_id,
        policy_version=ROUTING_POLICY_VERSION,
        calibration_dataset_version=CALIBRATION_DATASET_VERSION,
        profile=profile,
        project_complexity=assessment,
        routes_by_stage=routes,
    )


def _level_for_score(score: int, *, critical_override: bool) -> ComplexityLevel:
    if critical_override or score >= 81:
        return "C5"
    if score >= 61:
        return "C4"
    if score >= 41:
        return "C3"
    if score >= 21:
        return "C2"
    if score >= 1:
        return "C1"
    return "C0"


def _reason_codes(signals: ComplexitySignals, level: ComplexityLevel) -> list[str]:
    reasons = [f"score-band:{level}"]
    if signals.integration_count:
        reasons.append("third-party-integrations")
    if signals.compliance_or_security_critical:
        reasons.append("security-or-compliance")
    if signals.data_migration_required:
        reasons.append("data-migration")
    if signals.workflow_state_complexity:
        reasons.append("stateful-workflow")
    if signals.evidence_scarcity:
        reasons.append("evidence-scarcity")
    if signals.novel_domain:
        reasons.append("novel-domain")
    if signals.contradiction_count:
        reasons.append("contradictory-input")
    if signals.detected_language_count > 1:
        reasons.append("multilingual-input")
    return reasons


def _route_spec(
    stage: RoutingStage,
    level: ComplexityLevel,
    profile: ExecutionProfileV3,
) -> _RouteSpec:
    if stage == "complexity":
        if level in {"C0", "C1", "C2"}:
            return _RouteSpec(
                "deepseek", "deepseek-v4-flash", "instant", "none", 2_000, 20_000, 0, 0.01
            )
        return _RouteSpec(
            "deepseek",
            "deepseek-v4-flash",
            "thinking",
            "high",
            3_000,
            35_000,
            0,
            0.03,
            ("deepseek:deepseek-v4-pro",),
        )

    if stage == "structure":
        if level in {"C0", "C1"}:
            return _RouteSpec(
                "deepseek", "deepseek-v4-flash", "instant", "none", 4_000, 30_000, 0, 0.02
            )
        if level == "C2":
            return _RouteSpec(
                "deepseek",
                "deepseek-v4-flash",
                "thinking",
                "high",
                6_000,
                45_000,
                0,
                0.05,
                ("deepseek:deepseek-v4-pro",),
            )
        if level == "C3":
            return _RouteSpec(
                "deepseek",
                "deepseek-v4-pro",
                "thinking",
                "high",
                8_000,
                60_000,
                0,
                0.10,
                ("moonshot:kimi-k2.6",),
            )
        return _RouteSpec(
            "deepseek",
            "deepseek-v4-pro",
            "thinking",
            "max",
            10_000,
            90_000,
            0,
            0.20,
            ("moonshot:kimi-k2.6",),
        )

    if stage == "recovery":
        if level in {"C0", "C1"}:
            return _RouteSpec(
                "python", "deterministic-recovery", "deterministic", "none", 0, 10_000, 0, 0.0
            )
        if level == "C2":
            return _RouteSpec(
                "deepseek",
                "deepseek-v4-flash",
                "thinking",
                "high",
                4_000,
                45_000,
                4,
                0.05,
                ("deepseek:deepseek-v4-pro",),
            )
        return _RouteSpec(
            "deepseek",
            "deepseek-v4-pro",
            "thinking",
            "high",
            8_000,
            90_000,
            8,
            0.15,
            ("moonshot:kimi-k2.6",),
        )

    if stage == "reliability":
        if level in {"C0", "C1", "C2", "C3"}:
            return _RouteSpec(
                "deepseek", "deepseek-v4-flash", "instant", "none", 3_000, 30_000, 0, 0.02
            )
        return _RouteSpec(
            "moonshot",
            "kimi-k2.6",
            "thinking",
            "high",
            5_000,
            60_000,
            0,
            0.08,
            ("deepseek:deepseek-v4-pro",),
        )

    proposal_model = "deepseek-v4-flash" if profile != "quality_first" else "deepseek-v4-pro"
    proposal_mode: ModelMode = "instant" if profile != "quality_first" else "thinking"
    proposal_effort: ReasoningEffort = "none" if proposal_mode == "instant" else "high"
    return _RouteSpec(
        "deepseek",
        proposal_model,
        proposal_mode,
        proposal_effort,
        6_000,
        45_000,
        0,
        0.05,
        ("moonshot:kimi-k2.6",),
    )


def _route_id(stage: RoutingStage, spec: _RouteSpec) -> str:
    payload = {
        "stage": stage,
        "provider": spec.provider,
        "model": spec.model,
        "mode": spec.mode,
        "effort": spec.effort,
    }
    return "route:" + hashlib.sha256(_canonical_json(payload).encode()).hexdigest()[:20]


def _fallback_route_id(stage: RoutingStage, provider: str, model: str) -> str:
    payload = {"stage": stage, "provider": provider, "model": model, "fallback": True}
    return "route:" + hashlib.sha256(_canonical_json(payload).encode()).hexdigest()[:20]


def _providers(values: tuple[str, ...]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for value in values:
        provider, model = value.split(":", maxsplit=1)
        result.append((provider, model))
    return result


def _profile_cost(base: float, profile: ExecutionProfileV3) -> float:
    multiplier = {
        "cost_first": 0.65,
        "balanced": 1.0,
        "quality_first": 1.5,
        "human_controlled": 1.0,
    }[profile]
    return round(base * multiplier, 6)


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
