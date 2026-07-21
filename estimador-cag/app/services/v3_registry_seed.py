"""Seed the model registry with documented provider entries.

These entries represent documented capability, not verified reachability.
Lifecycle advancement requires live capability probes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.v3_registry import ModelRecord
from app.services.v3_model_registry import ModelRegistry


def build_seeded_registry() -> ModelRegistry:
    """Return a registry seeded with the documented provider family entries."""
    now = datetime.now(UTC)
    return ModelRegistry(
        [
            # DeepSeek family
            ModelRecord(
                provider="deepseek",
                provider_model_id="deepseek-v4-flash",
                display_name="DeepSeek V4 Flash",
                capability_tier="flash",
                context_window=128_000,
                max_output=8_192,
                input_modalities=["text"],
                tool_support=True,
                structured_output_support=True,
                reasoning_efforts=["none", "high"],
                speed_class="fast",
                cost_metadata_version="session13-v1",
                availability="available",
                verified_at=now,
                calibration_status="enabled",
            ),
            ModelRecord(
                provider="deepseek",
                provider_model_id="deepseek-v4-pro",
                display_name="DeepSeek V4 Pro",
                capability_tier="pro",
                context_window=128_000,
                max_output=8_192,
                input_modalities=["text"],
                tool_support=True,
                structured_output_support=True,
                reasoning_efforts=["none", "high", "max"],
                speed_class="fast",
                cost_metadata_version="session13-v1",
                availability="available",
                verified_at=now,
                calibration_status="enabled",
            ),
            # Kimi family
            ModelRecord(
                provider="moonshot",
                provider_model_id="kimi-k2.6",
                display_name="Kimi K2.6",
                capability_tier="flash",
                context_window=128_000,
                max_output=4_096,
                input_modalities=["text"],
                tool_support=True,
                structured_output_support=True,
                reasoning_efforts=["none", "high"],
                speed_class="medium",
                cost_metadata_version="session13-v1",
                availability="available",
                verified_at=now,
                calibration_status="enabled",
            ),
            ModelRecord(
                provider="moonshot",
                provider_model_id="kimi-k2.7-code",
                display_name="Kimi K2.7 Code",
                capability_tier="pro",
                context_window=128_000,
                max_output=8_192,
                input_modalities=["text"],
                tool_support=True,
                structured_output_support=True,
                reasoning_efforts=["none", "high"],
                speed_class="medium",
                cost_metadata_version="session13-v1",
                availability="available",
                verified_at=now,
                calibration_status="enabled",
            ),
            ModelRecord(
                provider="moonshot",
                provider_model_id="kimi-k3",
                display_name="Kimi K3",
                capability_tier="max",
                context_window=1_000_000,
                max_output=8_192,
                input_modalities=["text", "image"],
                tool_support=True,
                structured_output_support=True,
                reasoning_efforts=["max"],
                speed_class="slow",
                cost_metadata_version="session13-v1",
                availability="available",
                calibration_status="documented",
            ),
            # OpenAI GPT-5.6 family
            ModelRecord(
                provider="openai",
                provider_model_id="gpt-5.6-luna",
                display_name="GPT-5.6 Luna",
                capability_tier="flash",
                context_window=128_000,
                max_output=16_384,
                input_modalities=["text"],
                tool_support=True,
                structured_output_support=True,
                reasoning_efforts=["none", "high"],
                speed_class="fast",
                cost_metadata_version="session13-v1",
                availability="available",
                calibration_status="documented",
            ),
            ModelRecord(
                provider="openai",
                provider_model_id="gpt-5.6-terra",
                display_name="GPT-5.6 Terra",
                capability_tier="pro",
                context_window=128_000,
                max_output=16_384,
                input_modalities=["text"],
                tool_support=True,
                structured_output_support=True,
                reasoning_efforts=["none", "high", "max"],
                speed_class="medium",
                cost_metadata_version="session13-v1",
                availability="available",
                calibration_status="documented",
            ),
            ModelRecord(
                provider="openai",
                provider_model_id="gpt-5.6-sol",
                display_name="GPT-5.6 Sol",
                capability_tier="max",
                context_window=200_000,
                max_output=16_384,
                input_modalities=["text", "image"],
                tool_support=True,
                structured_output_support=True,
                reasoning_efforts=["none", "high", "max"],
                speed_class="slow",
                cost_metadata_version="session13-v1",
                availability="available",
                calibration_status="documented",
            ),
        ]
    )
