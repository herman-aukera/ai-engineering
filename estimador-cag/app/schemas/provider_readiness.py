"""Strict contracts for provider verification, benchmarking, and stage routing."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.v3_routing import ComplexityLevel, ReasoningEffort, StrictV3Model

ProviderName = Literal["deepseek", "moonshot", "openai", "deterministic"]
ExecutionKind = Literal["model", "deterministic", "retrieval", "human"]
RouteSource = Literal["deterministic", "explicit", "benchmark"]
BenchmarkStatus = Literal[
    "unavailable",
    "reachable",
    "contract_verified",
    "benchmark_calibrated",
]
GraphStage = Literal[
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
]


class ProviderPrice(StrictV3Model):
    """Versioned public price metadata, never a live billing assertion."""

    provider: ProviderName
    model: str = Field(min_length=1)
    input_usd_per_million: float | None = Field(default=None, ge=0)
    cached_input_usd_per_million: float | None = Field(default=None, ge=0)
    output_usd_per_million: float | None = Field(default=None, ge=0)
    pricing_mode: Literal["token", "subscription_quota", "unknown"] = "token"
    source_url: str = Field(min_length=1)
    version: str = Field(min_length=1)


class ModelBenchmarkSummary(StrictV3Model):
    """Matched benchmark aggregate for one exact provider/model/effort route."""

    provider: ProviderName
    model: str = Field(min_length=1)
    effort: ReasoningEffort
    status: BenchmarkStatus
    sample_count: int = Field(ge=0)
    quality_score: float = Field(ge=0, le=1)
    schema_pass_rate: float = Field(ge=0, le=1)
    tool_pass_rate: float = Field(ge=0, le=1)
    median_latency_ms: float | None = Field(default=None, ge=0)
    median_cost_usd: float | None = Field(default=None, ge=0)
    failure_count: int = Field(ge=0)

    @property
    def route_key(self) -> str:
        return f"{self.provider}:{self.model}:{self.effort}"


class BenchmarkSnapshot(StrictV3Model):
    """Immutable matched-benchmark snapshot used by evidence-backed Auto routing."""

    version: str = Field(min_length=1)
    source_commit: str = Field(min_length=7, max_length=64)
    cases_hash: str = Field(min_length=16, max_length=128)
    created_at: datetime
    required_providers: list[ProviderName] = Field(default_factory=list)
    summaries: list[ModelBenchmarkSummary] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_routes(self) -> BenchmarkSnapshot:
        keys = [summary.route_key for summary in self.summaries]
        if len(keys) != len(set(keys)):
            raise ValueError("benchmark route keys must be unique")
        return self

    def summary_by_key(self) -> dict[str, ModelBenchmarkSummary]:
        return {summary.route_key: summary for summary in self.summaries}

    def has_complete_provider_coverage(self) -> bool:
        calibrated = {
            summary.provider
            for summary in self.summaries
            if summary.status == "benchmark_calibrated"
            and summary.sample_count > 0
            and summary.failure_count == 0
        }
        return set(self.required_providers).issubset(calibrated)


class StageRouteDecision(StrictV3Model):
    """Checkpoint-safe route selected for one exact graph stage."""

    stage: GraphStage
    execution_kind: ExecutionKind
    provider: ProviderName
    model: str = Field(min_length=1)
    effort: ReasoningEffort
    complexity_level: ComplexityLevel
    source: RouteSource
    reason_codes: list[str] = Field(min_length=1)
    benchmark_version: str | None = None
    quality_score: float | None = Field(default=None, ge=0, le=1)
    expected_cost_usd: float | None = Field(default=None, ge=0)
