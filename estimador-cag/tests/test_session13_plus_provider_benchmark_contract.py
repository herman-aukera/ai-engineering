"""Deterministic contracts for the matched live-provider benchmark."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _benchmark_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "provider_readiness_benchmark.py"
    spec = importlib.util.spec_from_file_location("provider_readiness_benchmark", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_error_sanitizer_removes_api_key_material() -> None:
    benchmark = _benchmark_module()
    code, detail = benchmark._sanitize_error(
        RuntimeError(
            "Bad request Authorization: Bearer secret-provider-token-123456789 "
            "and sk-example12345678901234567890 tool_choice invalid"
        )
    )
    assert code == "invalid_tool_choice"
    assert "secret-provider-token" not in detail
    assert "sk-example" not in detail
    assert "[redacted" in detail


def test_kimi_k3_cost_fallback_uses_versioned_cache_miss_price() -> None:
    benchmark = _benchmark_module()
    route = benchmark.Route(
        provider="moonshot",
        model="kimi-k3",
        effort="max",
        api_key="not-used",
        base_url="https://example.invalid/v1",
    )
    response = SimpleNamespace(_hidden_params={})
    cost, source = benchmark._response_cost(
        route=route,
        response=response,
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    assert cost == 18.0
    assert source == "official_kimi_k3_cache_miss_2026-07"


def test_unknown_model_without_catalogue_price_remains_unpriced() -> None:
    benchmark = _benchmark_module()
    route = benchmark.Route(
        provider="moonshot",
        model="unknown-model",
        effort="high",
        api_key="not-used",
        base_url="https://example.invalid/v1",
    )
    response = SimpleNamespace(_hidden_params={})
    cost, source = benchmark._response_cost(
        route=route,
        response=response,
        input_tokens=100,
        output_tokens=50,
    )
    assert cost is None
    assert source is None
