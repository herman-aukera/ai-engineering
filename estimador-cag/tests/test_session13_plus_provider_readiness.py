"""Deterministic readiness and evidence-backed provider-routing tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.provider_readiness import (
    BenchmarkSnapshot,
    ModelBenchmarkSummary,
)
from app.schemas.v5_provider_selection import ProviderSelection
from app.services.provider_readiness import (
    ProviderRouteUnavailableError,
    StageRoutingPolicy,
    execution_kind_for_stage,
    graph_stage_inventory,
)


def _summary(
    provider: str,
    model: str,
    effort: str,
    *,
    quality: float,
    cost: float,
    latency: float,
) -> ModelBenchmarkSummary:
    return ModelBenchmarkSummary(
        provider=provider,
        model=model,
        effort=effort,
        status="benchmark_calibrated",
        sample_count=6,
        quality_score=quality,
        schema_pass_rate=1.0,
        tool_pass_rate=1.0,
        median_latency_ms=latency,
        median_cost_usd=cost,
        failure_count=0,
    )


def _snapshot() -> BenchmarkSnapshot:
    return BenchmarkSnapshot(
        version="session13-plus-benchmark-v1",
        source_commit="f193866edb9fd12d6134bdc3c1fd436c2826a5d7",
        cases_hash="1234567890abcdef1234567890abcdef",
        created_at=datetime(2026, 7, 21, tzinfo=UTC),
        required_providers=["deepseek", "moonshot", "openai"],
        summaries=[
            _summary(
                "deepseek",
                "deepseek-v4-pro",
                "high",
                quality=0.80,
                cost=0.01,
                latency=500,
            ),
            _summary(
                "moonshot",
                "verified-kimi-product-model",
                "high",
                quality=0.90,
                cost=0.02,
                latency=700,
            ),
            _summary(
                "openai",
                "gpt-5.6-sol",
                "max",
                quality=0.95,
                cost=0.05,
                latency=2_000,
            ),
        ],
    )


def test_stage_inventory_has_explicit_execution_kind_for_every_leaf_stage() -> None:
    stages = graph_stage_inventory()
    assert len(stages) == len(set(stages))
    assert "semantic_classify" in stages
    assert "proposal" in stages
    assert all(execution_kind_for_stage(stage) for stage in stages)


def test_non_model_stage_uses_truthful_deterministic_route() -> None:
    route = StageRoutingPolicy().resolve(
        stage="proposal",
        selection=ProviderSelection(provider="openai", reasoning="max"),
        complexity_level="C5",
    )
    assert route.execution_kind == "deterministic"
    assert route.provider == "deterministic"
    assert route.model == "python"
    assert route.source == "deterministic"


def test_explicit_deepseek_route_changes_model_with_complexity() -> None:
    policy = StageRoutingPolicy()
    low = policy.resolve(
        stage="extract_requirements",
        selection=ProviderSelection(provider="deepseek", reasoning="minimal"),
        complexity_level="C1",
    )
    high = policy.resolve(
        stage="extract_requirements",
        selection=ProviderSelection(provider="deepseek", reasoning="max"),
        complexity_level="C5",
    )
    assert low.model == "deepseek-v4-flash"
    assert low.effort == "none"
    assert high.model == "deepseek-v4-pro"
    assert high.effort == "max"


def test_explicit_kimi_product_route_fails_closed_without_verified_model_ids() -> None:
    with pytest.raises(
        ProviderRouteUnavailableError,
        match="No configured product model",
    ):
        StageRoutingPolicy().resolve(
            stage="semantic_classify",
            selection=ProviderSelection(provider="kimi", reasoning="max"),
            complexity_level="C4",
        )


def test_explicit_kimi_k3_effort_mapping_when_runtime_catalog_verifies_k3() -> None:
    policy = StageRoutingPolicy(
        model_catalog={
            "deepseek": {},
            "openai": {},
            "moonshot": {"flash": "k3", "pro": "k3", "max": "k3"},
            "deterministic": {"flash": "python", "pro": "python", "max": "python"},
        }
    )
    route = policy.resolve(
        stage="semantic_classify",
        selection=ProviderSelection(provider="kimi", reasoning="minimal"),
        complexity_level="C3",
    )
    assert route.provider == "moonshot"
    assert route.model == "k3"
    assert route.effort == "low"


def test_auto_fails_closed_without_complete_matched_benchmark() -> None:
    partial = _snapshot().model_copy(
        update={"required_providers": ["deepseek", "moonshot", "openai", "deterministic"]}
    )
    with pytest.raises(
        ProviderRouteUnavailableError,
        match="complete benchmark coverage",
    ):
        StageRoutingPolicy(benchmark_snapshot=partial).resolve(
            stage="semantic_classify",
            selection=ProviderSelection(provider="auto", reasoning="medium"),
            complexity_level="C3",
        )


def test_auto_minimal_selects_cheapest_route_above_quality_gate() -> None:
    route = StageRoutingPolicy(benchmark_snapshot=_snapshot()).resolve(
        stage="extract_requirements",
        selection=ProviderSelection(provider="auto", reasoning="minimal"),
        complexity_level="C2",
    )
    assert route.provider == "deepseek"
    assert route.model == "deepseek-v4-pro"
    assert route.expected_cost_usd == pytest.approx(0.01)
    assert route.source == "benchmark"


def test_auto_medium_uses_balanced_matched_utility() -> None:
    route = StageRoutingPolicy(benchmark_snapshot=_snapshot()).resolve(
        stage="classify_components",
        selection=ProviderSelection(provider="auto", reasoning="medium"),
        complexity_level="C3",
    )
    assert route.provider == "moonshot"
    assert route.model == "verified-kimi-product-model"


def test_auto_max_selects_highest_quality_contract_passing_route() -> None:
    route = StageRoutingPolicy(benchmark_snapshot=_snapshot()).resolve(
        stage="selective_recovery",
        selection=ProviderSelection(provider="auto", reasoning="max"),
        complexity_level="C5",
    )
    assert route.provider == "openai"
    assert route.model == "gpt-5.6-sol"
    assert route.quality_score == pytest.approx(0.95)


def test_auto_route_is_replay_stable_for_same_snapshot_and_input() -> None:
    policy = StageRoutingPolicy(benchmark_snapshot=_snapshot())
    selection = ProviderSelection(provider="auto", reasoning="medium")
    first = policy.resolve(
        stage="semantic_classify",
        selection=selection,
        complexity_level="C4",
    )
    second = policy.resolve(
        stage="semantic_classify",
        selection=selection,
        complexity_level="C4",
    )
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()


def test_benchmark_snapshot_rejects_duplicate_route_keys() -> None:
    duplicate = _summary(
        "deepseek",
        "deepseek-v4-pro",
        "high",
        quality=0.8,
        cost=0.01,
        latency=500,
    )
    with pytest.raises(ValidationError, match="route keys must be unique"):
        BenchmarkSnapshot(
            version="duplicate",
            source_commit="f193866",
            cases_hash="1234567890abcdef",
            created_at=datetime(2026, 7, 21, tzinfo=UTC),
            required_providers=["deepseek"],
            summaries=[duplicate, duplicate],
        )
