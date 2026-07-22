"""Runtime tests proving stage routes control provider execution and evidence."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from langgraph.types import Command

from app.generation.graph.observability import (
    NOOP_GRAPH_TRACER,
    instrument_reviewed_graph_node,
)
from app.schemas.provider_readiness import (
    BenchmarkSnapshot,
    ModelBenchmarkSummary,
)
from app.services.provider_readiness import StageRoutingPolicy, graph_stage_inventory
from app.services.stage_routing_runtime import (
    ProviderCredentialUnavailableError,
    ProviderRuntimeConfig,
    StageRoutedLiteLLMProvider,
    StageRoutingRuntime,
    current_stage_route,
)


def _runtime_config() -> ProviderRuntimeConfig:
    return ProviderRuntimeConfig(
        deepseek_api_key="deepseek-secret-for-test",
        deepseek_base_url="https://deepseek.invalid/v1",
        deepseek_models={
            "flash": "deepseek-v4-flash",
            "pro": "deepseek-v4-pro",
            "max": "deepseek-v4-pro",
        },
        kimi_api_key="kimi-secret-for-test",
        kimi_base_url="https://kimi.invalid/v1",
        kimi_models={"flash": "k3", "pro": "k3", "max": "k3"},
        openai_api_key="openai-secret-for-test",
        openai_base_url="https://openai.invalid/v1",
        openai_models={
            "flash": "gpt-5.6-luna",
            "pro": "gpt-5.6-terra",
            "max": "gpt-5.6-sol",
        },
    )


def _runtime() -> StageRoutingRuntime:
    config = _runtime_config()
    return StageRoutingRuntime(
        StageRoutingPolicy(model_catalog=config.model_catalog())
    )


@pytest.mark.asyncio
async def test_instrumentation_records_route_for_every_leaf_stage() -> None:
    runtime = _runtime()

    async def node(state):
        route = current_stage_route()
        assert route is not None
        return {"execution_metadata": {"visited": route.stage}}

    for stage in graph_stage_inventory():
        wrapped = instrument_reviewed_graph_node(
            graph_name="test_graph",
            node_name=stage,
            node=node,
            tracer=NOOP_GRAPH_TRACER,
            routing_runtime=runtime,
        )
        update = await wrapped(
            {
                "provider_selection": {
                    "provider": "deepseek",
                    "reasoning": "medium",
                    "context_detail": "medium",
                },
                "arbitrated_assessment": {"arbitrated_level": "C3"},
            }
        )
        assert not isinstance(update, Command)
        event = update["stage_route_events"][0]
        assert event["stage"] == stage
        assert event["complexity_level"] == "C3"


@pytest.mark.asyncio
async def test_command_handover_preserves_goto_and_adds_route_evidence() -> None:
    runtime = _runtime()

    async def node(state):
        return Command(update={"status": "pending"}, goto="structure_phase")

    wrapped = instrument_reviewed_graph_node(
        graph_name="test_graph",
        node_name="semantic_classify",
        node=node,
        tracer=NOOP_GRAPH_TRACER,
        routing_runtime=runtime,
    )
    update = await wrapped(
        {
            "provider_selection": {
                "provider": "openai",
                "reasoning": "max",
                "context_detail": "medium",
            },
            "v3_complexity": {"level": "C5"},
        }
    )
    assert isinstance(update, Command)
    assert update.goto == "structure_phase"
    assert update.update["stage_route_events"][0]["provider"] == "openai"
    assert update.update["stage_route_events"][0]["model"] == "gpt-5.6-sol"


def test_bound_route_changes_actual_resolved_provider_and_model() -> None:
    runtime = _runtime()
    provider = StageRoutedLiteLLMProvider(runtime_config=_runtime_config())
    route = runtime.resolve(
        stage="extract_requirements",
        state={
            "provider_selection": {
                "provider": "openai",
                "reasoning": "max",
                "context_detail": "minimal",
            },
            "arbitrated_assessment": {"arbitrated_level": "C5"},
        },
    )
    with runtime.bind(route):
        resolved = provider.resolve_model("flash")
    assert resolved.provider == "openai"
    assert resolved.model == "gpt-5.6-sol"
    assert resolved.api_key == "openai-secret-for-test"
    assert "openai-secret-for-test" not in route.model_dump_json()


def test_bound_kimi_route_uses_configured_product_model_not_code_membership_alias() -> None:
    runtime = _runtime()
    provider = StageRoutedLiteLLMProvider(runtime_config=_runtime_config())
    route = runtime.resolve(
        stage="semantic_classify",
        state={
            "provider_selection": {
                "provider": "kimi",
                "reasoning": "minimal",
                "context_detail": "medium",
            },
            "arbitrated_assessment": {"arbitrated_level": "C4"},
        },
    )
    with runtime.bind(route):
        resolved = provider.resolve_model("flash")
    assert route.model == "k3"
    assert route.effort == "low"
    assert resolved.model == "moonshot/k3"
    assert "kimi-for-coding" not in resolved.model


def test_selected_provider_with_placeholder_key_fails_before_network_call() -> None:
    config = _runtime_config()
    invalid = ProviderRuntimeConfig(
        deepseek_api_key=config.deepseek_api_key,
        deepseek_base_url=config.deepseek_base_url,
        deepseek_models=config.deepseek_models,
        kimi_api_key=config.kimi_api_key,
        kimi_base_url=config.kimi_base_url,
        kimi_models=config.kimi_models,
        openai_api_key="test",
        openai_base_url=config.openai_base_url,
        openai_models=config.openai_models,
    )
    runtime = StageRoutingRuntime(
        StageRoutingPolicy(model_catalog=invalid.model_catalog())
    )
    provider = StageRoutedLiteLLMProvider(runtime_config=invalid)
    route = runtime.resolve(
        stage="classify_components",
        state={
            "provider_selection": {
                "provider": "openai",
                "reasoning": "medium",
                "context_detail": "medium",
            }
        },
    )
    with runtime.bind(route), pytest.raises(
        ProviderCredentialUnavailableError,
        match="Credential unavailable",
    ):
        provider.resolve_model("flash")


def test_auto_route_binds_benchmark_selected_provider() -> None:
    snapshot = BenchmarkSnapshot(
        version="matched-v1",
        source_commit="9139d54e5ba56f51b964e8df908b07c0cc667ae3",
        cases_hash="fedcba0987654321fedcba0987654321",
        created_at=datetime(2026, 7, 21, tzinfo=UTC),
        required_providers=["deepseek", "moonshot", "openai"],
        summaries=[
            ModelBenchmarkSummary(
                provider="deepseek",
                model="deepseek-v4-pro",
                effort="high",
                status="benchmark_calibrated",
                sample_count=5,
                quality_score=0.8,
                schema_pass_rate=1.0,
                tool_pass_rate=1.0,
                median_latency_ms=500,
                median_cost_usd=0.01,
                failure_count=0,
            ),
            ModelBenchmarkSummary(
                provider="moonshot",
                model="k3",
                effort="high",
                status="benchmark_calibrated",
                sample_count=5,
                quality_score=0.9,
                schema_pass_rate=1.0,
                tool_pass_rate=1.0,
                median_latency_ms=800,
                median_cost_usd=0.02,
                failure_count=0,
            ),
            ModelBenchmarkSummary(
                provider="openai",
                model="gpt-5.6-sol",
                effort="max",
                status="benchmark_calibrated",
                sample_count=5,
                quality_score=0.95,
                schema_pass_rate=1.0,
                tool_pass_rate=1.0,
                median_latency_ms=1500,
                median_cost_usd=0.05,
                failure_count=0,
            ),
        ],
    )
    runtime = StageRoutingRuntime(StageRoutingPolicy(benchmark_snapshot=snapshot))
    route = runtime.resolve(
        stage="selective_recovery",
        state={
            "provider_selection": {
                "provider": "auto",
                "reasoning": "max",
                "context_detail": "max",
            },
            "arbitrated_assessment": {"arbitrated_level": "C5"},
        },
    )
    assert route.source == "benchmark"
    assert route.provider == "openai"
    assert route.model == "gpt-5.6-sol"
