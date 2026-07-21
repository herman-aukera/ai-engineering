"""Evidence-backed graph-stage routing and matched benchmark selection policy."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.schemas.provider_readiness import (
    BenchmarkSnapshot,
    ExecutionKind,
    GraphStage,
    ModelBenchmarkSummary,
    ProviderName,
    StageRouteDecision,
)
from app.schemas.v3_routing import ComplexityLevel, ReasoningEffort
from app.schemas.v5_provider_selection import ProviderSelection

_MODEL_STAGES = frozenset(
    {
        "semantic_classify",
        "extract_requirements",
        "classify_components",
        "selective_recovery",
        "human_requested_recovery",
    }
)
_RETRIEVAL_STAGES = frozenset(
    {
        "search_budgets",
        "parallel_retrieval_dispatch",
        "parallel_retrieval_worker",
        "parallel_retrieval_merge",
    }
)
_HUMAN_STAGES = frozenset({"structure_review", "final_estimate_review"})
_ALL_STAGES: tuple[GraphStage, ...] = (
    "reformulate_request",
    "semantic_classify",
    "extract_requirements",
    "classify_components",
    "structure_review",
    "search_budgets",
    "parallel_retrieval_dispatch",
    "parallel_retrieval_worker",
    "parallel_retrieval_merge",
    "generate_estimate",
    "validate_initial",
    "selective_recovery",
    "recalculate_estimate",
    "validate_final",
    "reliability_analyst",
    "deterministic_critic",
    "deterministic_boss",
    "boss_action",
    "final_estimate_review",
    "human_requested_recovery",
    "human_requested_recalculation",
    "human_requested_validation",
    "final_consolidation",
    "proposal",
)

_TIER_BY_COMPLEXITY: dict[ComplexityLevel, str] = {
    "C0": "flash",
    "C1": "flash",
    "C2": "flash",
    "C3": "pro",
    "C4": "pro",
    "C5": "max",
}

_DEFAULT_MODELS: dict[ProviderName, dict[str, str]] = {
    "deepseek": {
        "flash": "deepseek-v4-flash",
        "pro": "deepseek-v4-pro",
        "max": "deepseek-v4-pro",
    },
    "openai": {
        "flash": "gpt-5.6-luna",
        "pro": "gpt-5.6-terra",
        "max": "gpt-5.6-sol",
    },
    # Moonshot product model IDs must be supplied by runtime configuration or
    # a verified benchmark snapshot. Kimi Code membership IDs are not assumed
    # to be valid product API routes.
    "moonshot": {},
    "deterministic": {"flash": "python", "pro": "python", "max": "python"},
}


class ProviderRouteUnavailable(RuntimeError):
    """Raised when policy cannot prove an eligible route."""


def graph_stage_inventory() -> tuple[GraphStage, ...]:
    """Return the complete, stable leaf-stage inventory used by route tests."""

    return _ALL_STAGES


def execution_kind_for_stage(stage: GraphStage) -> ExecutionKind:
    if stage in _MODEL_STAGES:
        return "model"
    if stage in _RETRIEVAL_STAGES:
        return "retrieval"
    if stage in _HUMAN_STAGES:
        return "human"
    return "deterministic"


def _provider_name(selection: ProviderSelection) -> ProviderName:
    return {
        "deepseek": "deepseek",
        "kimi": "moonshot",
        "openai": "openai",
        "auto": "deterministic",
    }[selection.provider]


def _effort(provider: ProviderName, model: str, intent: str) -> ReasoningEffort:
    if provider == "moonshot":
        if model == "k3":
            return {"minimal": "low", "medium": "high", "max": "max"}[intent]
        return "high"
    if provider == "deterministic":
        return "none"
    return {"minimal": "none", "medium": "high", "max": "max"}[intent]


def _normalized_inverse(value: float | None, *, maximum: float) -> float:
    if value is None:
        return 0.0
    if maximum <= 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (value / maximum)))


def _eligible_summaries(snapshot: BenchmarkSnapshot) -> list[ModelBenchmarkSummary]:
    return [
        summary
        for summary in snapshot.summaries
        if summary.status == "benchmark_calibrated"
        and summary.sample_count > 0
        and summary.failure_count == 0
        and summary.schema_pass_rate >= 0.95
        and summary.tool_pass_rate >= 0.95
    ]


def _choose_auto(
    *,
    snapshot: BenchmarkSnapshot,
    selection: ProviderSelection,
) -> ModelBenchmarkSummary:
    if not snapshot.has_complete_provider_coverage():
        raise ProviderRouteUnavailable(
            "Auto routing requires complete benchmark coverage for every required provider."
        )

    eligible = _eligible_summaries(snapshot)
    if not eligible:
        raise ProviderRouteUnavailable("No benchmark-calibrated route satisfies contract gates.")

    if selection.reasoning == "minimal":
        costed = [
            summary
            for summary in eligible
            if summary.median_cost_usd is not None and summary.quality_score >= 0.75
        ]
        if not costed:
            raise ProviderRouteUnavailable(
                "Cost-first Auto requires comparable measured cost and quality >= 0.75."
            )
        return min(
            costed,
            key=lambda item: (
                float(item.median_cost_usd or 0.0),
                -item.quality_score,
                float(item.median_latency_ms or 0.0),
                item.route_key,
            ),
        )

    if selection.reasoning == "max":
        return max(
            eligible,
            key=lambda item: (
                item.quality_score,
                item.schema_pass_rate,
                item.tool_pass_rate,
                -(item.median_cost_usd or float("inf")),
                -(item.median_latency_ms or float("inf")),
                item.route_key,
            ),
        )

    max_cost = max((item.median_cost_usd or 0.0) for item in eligible)
    max_latency = max((item.median_latency_ms or 0.0) for item in eligible)

    def utility(item: ModelBenchmarkSummary) -> tuple[float, str]:
        score = (
            0.65 * item.quality_score
            + 0.15 * item.schema_pass_rate
            + 0.10 * item.tool_pass_rate
            + 0.05 * _normalized_inverse(item.median_latency_ms, maximum=max_latency)
            + 0.05 * _normalized_inverse(item.median_cost_usd, maximum=max_cost)
        )
        return score, item.route_key

    return max(eligible, key=utility)


@dataclass(frozen=True)
class StageRoutingPolicy:
    """Resolve every graph stage with explicit evidence and fail-closed Auto."""

    benchmark_snapshot: BenchmarkSnapshot | None = None
    model_catalog: Mapping[ProviderName, Mapping[str, str]] = field(
        default_factory=lambda: _DEFAULT_MODELS
    )

    def resolve(
        self,
        *,
        stage: GraphStage,
        selection: ProviderSelection,
        complexity_level: ComplexityLevel,
    ) -> StageRouteDecision:
        kind = execution_kind_for_stage(stage)
        if kind != "model":
            return StageRouteDecision(
                stage=stage,
                execution_kind=kind,
                provider="deterministic",
                model={"retrieval": "pgvector", "human": "human_gate"}.get(kind, "python"),
                effort="none",
                complexity_level=complexity_level,
                source="deterministic",
                reason_codes=[f"execution_kind:{kind}", "provider_not_applicable"],
            )

        if selection.provider == "auto":
            if self.benchmark_snapshot is None:
                raise ProviderRouteUnavailable(
                    "Auto routing has no matched benchmark snapshot."
                )
            summary = _choose_auto(
                snapshot=self.benchmark_snapshot,
                selection=selection,
            )
            return StageRouteDecision(
                stage=stage,
                execution_kind="model",
                provider=summary.provider,
                model=summary.model,
                effort=summary.effort,
                complexity_level=complexity_level,
                source="benchmark",
                reason_codes=[
                    "auto:matched_benchmark",
                    f"intent:{selection.reasoning}",
                    f"stage:{stage}",
                ],
                benchmark_version=self.benchmark_snapshot.version,
                quality_score=summary.quality_score,
                expected_cost_usd=summary.median_cost_usd,
            )

        provider = _provider_name(selection)
        tier = _TIER_BY_COMPLEXITY[complexity_level]
        provider_models = self.model_catalog.get(provider, {})
        model = provider_models.get(tier) or provider_models.get("pro")
        if not model:
            raise ProviderRouteUnavailable(
                f"No configured product model for provider={provider}, tier={tier}."
            )
        return StageRouteDecision(
            stage=stage,
            execution_kind="model",
            provider=provider,
            model=model,
            effort=_effort(provider, model, selection.reasoning),
            complexity_level=complexity_level,
            source="explicit",
            reason_codes=[
                f"provider:{selection.provider}",
                f"tier:{tier}",
                f"stage:{stage}",
                "explicit_route_requires_live_verification",
            ],
        )
