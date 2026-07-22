"""Production readiness tests separated from basic process liveness."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.routers.readiness import router
from app.schemas.provider_readiness import (
    BenchmarkSnapshot,
    ModelBenchmarkSummary,
)
from app.services.production_readiness import (
    RuntimeAvailability,
    build_production_readiness_report,
    runtime_availability_from_app_state,
)


def _settings(**updates) -> Settings:
    values = {
        "stress_fake_provider": True,
        "deepseek_api_key": "dummy",
        "kimi_api_key": "dummy",
        "openai_api_key": "dummy",
    }
    values.update(updates)
    return Settings(**values)


def test_readiness_requires_both_graph_runtimes_and_real_provider() -> None:
    report = build_production_readiness_report(
        runtime=RuntimeAvailability(
            graph_runtime=True,
            reviewed_graph_runtime=False,
        ),
        config=_settings(deepseek_api_key="configured-deepseek-key"),
    )
    assert report.ready is False
    assert report.status == "not_ready"
    assert report.checks["graph_runtime"].ready is True
    assert report.checks["reviewed_graph_runtime"].ready is False
    assert report.checks["provider_configuration"].ready is True


def test_process_can_be_ready_while_auto_remains_disabled() -> None:
    report = build_production_readiness_report(
        runtime=RuntimeAvailability(
            graph_runtime=True,
            reviewed_graph_runtime=True,
        ),
        config=_settings(openai_api_key="configured-openai-key"),
    )
    assert report.ready is True
    assert report.status == "ready"
    assert report.configured_providers == ["openai"]
    assert report.auto_eligible is False
    assert report.checks["matched_benchmark"].code == "benchmark_not_configured"


def test_complete_matched_snapshot_enables_auto_without_exposing_keys(tmp_path) -> None:
    summaries = [
        ModelBenchmarkSummary(
            provider=provider,
            model=model,
            effort="high",
            status="benchmark_calibrated",
            sample_count=3,
            quality_score=1.0,
            schema_pass_rate=1.0,
            tool_pass_rate=1.0,
            median_latency_ms=100,
            median_cost_usd=0.01,
            failure_count=0,
        )
        for provider, model in (
            ("deepseek", "deepseek-v4-pro"),
            ("moonshot", "verified-kimi-model"),
            ("openai", "gpt-5.6-sol"),
        )
    ]
    snapshot = BenchmarkSnapshot(
        version="matched-ready-v1",
        source_commit="139b190f2ad88c71c6e59eb252542827f31c483e",
        cases_hash="1234567890abcdef1234567890abcdef",
        created_at=datetime(2026, 7, 21, tzinfo=UTC),
        required_providers=["deepseek", "moonshot", "openai"],
        summaries=summaries,
    )
    path = tmp_path / "benchmark.json"
    path.write_text(snapshot.model_dump_json(), encoding="utf-8")
    secret = "configured-provider-secret"
    report = build_production_readiness_report(
        runtime=RuntimeAvailability(
            graph_runtime=True,
            reviewed_graph_runtime=True,
        ),
        config=_settings(
            deepseek_api_key=secret,
            provider_benchmark_snapshot_path=str(path),
        ),
    )
    assert report.ready is True
    assert report.auto_eligible is True
    assert report.benchmark_version == "matched-ready-v1"
    assert secret not in report.model_dump_json()


def test_runtime_diagnostics_allow_only_exception_class_names() -> None:
    secret = "postgresql://user:password@database/private"
    runtime = runtime_availability_from_app_state(
        SimpleNamespace(
            graph_estimation_service=None,
            reviewed_graph_estimation_service=None,
            graph_runtime_error="OperationalError",
            reviewed_graph_runtime_error=secret,
        )
    )
    report = build_production_readiness_report(
        runtime=runtime,
        config=_settings(deepseek_api_key="configured-deepseek-key"),
    )
    serialized = report.model_dump_json()
    assert "OperationalError" in report.checks["graph_runtime"].detail
    assert secret not in serialized
    assert "password" not in serialized
    assert report.checks["reviewed_graph_runtime"].detail == (
        "Reviewed graph runtime is unavailable."
    )


def test_ready_endpoint_returns_503_with_uninitialized_runtime_and_placeholder_keys() -> None:
    application = FastAPI()
    application.include_router(router)
    application.state.graph_estimation_service = None
    application.state.reviewed_graph_estimation_service = None
    response = TestClient(application).get("/ready")
    assert response.status_code == 503
    payload = response.json()
    assert payload["ready"] is False
    assert payload["status"] == "not_ready"
    assert payload["configured_providers"] == []
