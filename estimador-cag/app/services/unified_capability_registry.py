"""Evidence-backed adapter from Session 13 benchmark routes to Plus capabilities."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from app.schemas.provider_readiness import BenchmarkSnapshot
from app.schemas.session14_plus_policy import (
    ModelCapabilityRecord,
    ModelCapabilityRegistry,
)
from app.schemas.v3_routing import ReasoningEffort
from app.services.session14_plus_policy import build_capability_registry

_DEFAULT_SNAPSHOT = (
    Path(__file__).parents[2]
    / "artifacts"
    / "provider-readiness"
    / "provider-benchmark-snapshot.json"
)
_EFFORT_ORDER: tuple[ReasoningEffort, ...] = (
    "none",
    "low",
    "medium",
    "high",
    "max",
    "xhigh",
)
_MODEL_METADATA: dict[tuple[str, str], dict[str, object]] = {
    ("deepseek", "deepseek-v4-flash"): {
        "display_name": "DeepSeek V4 Flash",
        "capability_tier": "flash",
        "context_window_tokens": 128_000,
        "max_output_tokens": 8_192,
        "modalities": ["text"],
        "speed_class": "fast",
    },
    ("deepseek", "deepseek-v4-pro"): {
        "display_name": "DeepSeek V4 Pro",
        "capability_tier": "pro",
        "context_window_tokens": 128_000,
        "max_output_tokens": 8_192,
        "modalities": ["text"],
        "speed_class": "balanced",
    },
    ("moonshot", "kimi-k3"): {
        "display_name": "Kimi K3",
        "capability_tier": "max",
        "context_window_tokens": 1_000_000,
        "max_output_tokens": 8_192,
        "modalities": ["text", "image"],
        "speed_class": "balanced",
    },
    ("openai", "gpt-5.6-luna"): {
        "display_name": "GPT-5.6 Luna",
        "capability_tier": "flash",
        "context_window_tokens": 128_000,
        "max_output_tokens": 16_384,
        "modalities": ["text"],
        "speed_class": "fast",
    },
    ("openai", "gpt-5.6-terra"): {
        "display_name": "GPT-5.6 Terra",
        "capability_tier": "pro",
        "context_window_tokens": 128_000,
        "max_output_tokens": 16_384,
        "modalities": ["text"],
        "speed_class": "balanced",
    },
    ("openai", "gpt-5.6-sol"): {
        "display_name": "GPT-5.6 Sol",
        "capability_tier": "max",
        "context_window_tokens": 200_000,
        "max_output_tokens": 16_384,
        "modalities": ["text", "image"],
        "speed_class": "slow",
    },
}


def load_benchmark_snapshot(
    path: str | Path | None = None,
) -> BenchmarkSnapshot:
    """Load the immutable sanitized benchmark snapshot used by the runtime."""

    snapshot_path = Path(path) if path else _DEFAULT_SNAPSHOT
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return BenchmarkSnapshot.model_validate(payload)


def build_unified_capability_registry(
    snapshot: BenchmarkSnapshot,
) -> ModelCapabilityRegistry:
    """Enable only exact model routes that passed matched benchmark gates."""

    efforts_by_model: dict[tuple[str, str], set[ReasoningEffort]] = defaultdict(set)
    for summary in snapshot.summaries:
        if (
            summary.status == "benchmark_calibrated"
            and summary.sample_count > 0
            and summary.failure_count == 0
            and summary.schema_pass_rate >= 0.95
            and summary.tool_pass_rate >= 0.95
        ):
            key = (summary.provider, summary.model)
            if key not in _MODEL_METADATA:
                raise ValueError(
                    "benchmark contains a calibrated model without capability metadata: "
                    f"{summary.provider}/{summary.model}"
                )
            efforts_by_model[key].add(summary.effort)

    records: list[ModelCapabilityRecord] = []
    for (provider, model), efforts in sorted(efforts_by_model.items()):
        metadata = _MODEL_METADATA[(provider, model)]
        ordered_efforts = [effort for effort in _EFFORT_ORDER if effort in efforts]
        records.append(
            ModelCapabilityRecord(
                record_id=f"benchmark:{snapshot.version}:{provider}:{model}",
                provider=provider,
                provider_model_id=model,
                display_name=str(metadata["display_name"]),
                capability_tier=str(metadata["capability_tier"]),
                context_window_tokens=int(metadata["context_window_tokens"]),
                max_output_tokens=int(metadata["max_output_tokens"]),
                modalities=list(metadata["modalities"]),
                supports_tools=True,
                supports_structured_output=True,
                reasoning_efforts=ordered_efforts,
                speed_class=metadata["speed_class"],
                cost_metadata_version=f"benchmark:{snapshot.version}",
                lifecycle="benchmark_calibrated",
                verified_at=snapshot.created_at,
                calibration_status="matched",
                enabled=True,
            )
        )

    records.append(
        ModelCapabilityRecord(
            record_id="contract:python:deterministic-recovery",
            provider="python",
            provider_model_id="deterministic-recovery",
            display_name="Deterministic Python recovery",
            capability_tier="deterministic",
            context_window_tokens=1,
            max_output_tokens=0,
            modalities=["text"],
            supports_tools=False,
            supports_structured_output=True,
            reasoning_efforts=["none"],
            speed_class="deterministic",
            cost_metadata_version="deterministic-v1",
            lifecycle="contract_verified",
            verified_at=snapshot.created_at,
            calibration_status="baseline",
            enabled=True,
        )
    )
    return build_capability_registry(
        records,
        registry_version=f"unified:{snapshot.version}",
        generated_at=snapshot.created_at,
    )
