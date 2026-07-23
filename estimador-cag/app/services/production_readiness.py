"""Fail-closed production readiness projection without secret disclosure."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings, settings
from app.schemas.provider_readiness import BenchmarkSnapshot

_PLACEHOLDERS = frozenset({"", "test", "dummy", "fake", "placeholder", "example"})


class ReadinessCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ready: bool
    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class ProductionReadinessReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    ready: bool
    checks: dict[str, ReadinessCheck]
    configured_providers: list[str]
    benchmark_version: str | None = None
    auto_eligible: bool = False


@dataclass(frozen=True)
class RuntimeAvailability:
    graph_runtime: bool
    reviewed_graph_runtime: bool
    graph_runtime_error: str | None = None
    reviewed_graph_runtime_error: str | None = None


def _real_key(value: str) -> bool:
    return value.strip().lower() not in _PLACEHOLDERS


def _safe_error_type(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 120:
        return None
    return value if value.isidentifier() else None


def configured_providers(config: Settings = settings) -> list[str]:
    providers: list[str] = []
    if _real_key(config.deepseek_api_key):
        providers.append("deepseek")
    if _real_key(config.kimi_api_key):
        providers.append("moonshot")
    if _real_key(config.openai_api_key):
        providers.append("openai")
    return providers


def _benchmark(path: str) -> tuple[BenchmarkSnapshot | None, ReadinessCheck]:
    normalized = path.strip()
    if not normalized:
        return None, ReadinessCheck(
            ready=False,
            code="benchmark_not_configured",
            detail="Matched benchmark snapshot is not configured; Auto remains disabled.",
        )
    snapshot_path = Path(normalized)
    try:
        snapshot = BenchmarkSnapshot.model_validate_json(
            snapshot_path.read_text(encoding="utf-8")
        )
    except Exception:
        return None, ReadinessCheck(
            ready=False,
            code="benchmark_invalid",
            detail="Configured benchmark snapshot is missing or invalid.",
        )
    eligible = snapshot.has_complete_provider_coverage()
    return snapshot, ReadinessCheck(
        ready=eligible,
        code=("benchmark_complete" if eligible else "benchmark_incomplete"),
        detail=(
            "Matched provider coverage satisfies the Auto eligibility contract."
            if eligible
            else "Matched provider coverage is incomplete; Auto remains disabled."
        ),
    )


def _runtime_detail(*, label: str, ready: bool, error_type: str | None) -> str:
    if ready:
        return f"{label} is initialized."
    if error_type:
        return f"{label} is unavailable; initialization error type: {error_type}."
    return f"{label} is unavailable."


def build_production_readiness_report(
    *,
    runtime: RuntimeAvailability,
    config: Settings = settings,
) -> ProductionReadinessReport:
    """Return process readiness and independent Auto/benchmark evidence."""

    providers = configured_providers(config)
    snapshot, benchmark_check = _benchmark(config.provider_benchmark_snapshot_path)
    checks = {
        "graph_runtime": ReadinessCheck(
            ready=runtime.graph_runtime,
            code=("graph_runtime_ready" if runtime.graph_runtime else "graph_runtime_unavailable"),
            detail=_runtime_detail(
                label="Mandatory graph runtime",
                ready=runtime.graph_runtime,
                error_type=runtime.graph_runtime_error,
            ),
        ),
        "reviewed_graph_runtime": ReadinessCheck(
            ready=runtime.reviewed_graph_runtime,
            code=(
                "reviewed_graph_runtime_ready"
                if runtime.reviewed_graph_runtime
                else "reviewed_graph_runtime_unavailable"
            ),
            detail=_runtime_detail(
                label="Reviewed graph runtime",
                ready=runtime.reviewed_graph_runtime,
                error_type=runtime.reviewed_graph_runtime_error,
            ),
        ),
        "provider_configuration": ReadinessCheck(
            ready=bool(providers),
            code=("provider_configured" if providers else "provider_unavailable"),
            detail=(
                f"Configured providers: {', '.join(providers)}."
                if providers
                else "No non-placeholder provider credential is configured."
            ),
        ),
        "matched_benchmark": benchmark_check,
    }
    process_ready = all(
        checks[name].ready
        for name in ("graph_runtime", "reviewed_graph_runtime", "provider_configuration")
    )
    return ProductionReadinessReport(
        status="ready" if process_ready else "not_ready",
        ready=process_ready,
        checks=checks,
        configured_providers=providers,
        benchmark_version=snapshot.version if snapshot is not None else None,
        auto_eligible=benchmark_check.ready,
    )


def _state_values(state: object) -> Mapping[str, object]:
    if isinstance(state, Mapping):
        return state
    attributes = vars(state)
    nested = attributes.get("_state")
    return nested if isinstance(nested, Mapping) else attributes


def runtime_availability_from_app_state(state: object) -> RuntimeAvailability:
    """Inspect service presence and allow-listed exception class names only."""

    values = _state_values(state)
    return RuntimeAvailability(
        graph_runtime=values.get("graph_estimation_service") is not None,
        reviewed_graph_runtime=values.get("reviewed_graph_estimation_service") is not None,
        graph_runtime_error=_safe_error_type(values.get("graph_runtime_error")),
        reviewed_graph_runtime_error=_safe_error_type(
            values.get("reviewed_graph_runtime_error")
        ),
    )
