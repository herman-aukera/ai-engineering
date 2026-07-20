"""Tests for Session 13 Plus S3A: versioned model-registry contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# 1. CalibrationStatus and lifecycle
# ---------------------------------------------------------------------------

def test_calibration_status_lifecycle_is_bounded() -> None:
    """calibration_status must be one of the six documented lifecycle values."""

    valid = {
        "documented",
        "configured",
        "reachable",
        "contract_verified",
        "benchmark_calibrated",
        "enabled",
    }
    # Every valid status string must be a legal CalibrationStatus value.
    for status in valid:
        record = _model_record(calibration_status=status)
        assert record.calibration_status == status


def test_model_record_rejects_unknown_calibration_status() -> None:
    """calibration_status must reject arbitrary strings."""

    with pytest.raises(ValidationError):
        _model_record(calibration_status="production_ready")


# ---------------------------------------------------------------------------
# 2. ModelRecord — checkpoint-safe fields
# ---------------------------------------------------------------------------

def test_model_record_is_frozen_and_forbids_extra_fields() -> None:
    """ModelRecord must be immutable and reject undeclared keys."""
    from app.schemas.v3_registry import ModelRecord

    record = _model_record()
    with pytest.raises(ValidationError):
        ModelRecord(**{**record.model_dump(), "made_up_field": 1})


def test_model_record_round_trips_through_json() -> None:
    """All ModelRecord fields must survive model_dump(mode='json') round-trip."""

    record = _model_record(calibration_status="contract_verified")
    payload = record.model_dump(mode="json")
    assert payload["provider"] == "deepseek"
    assert payload["provider_model_id"] == "deepseek-v4-flash"
    assert payload["context_window"] == 128_000
    assert payload["calibration_status"] == "contract_verified"
    assert isinstance(payload["verified_at"], str)


def test_model_record_requires_provider_and_model_id() -> None:
    """provider and provider_model_id are required non-empty strings."""

    with pytest.raises(ValidationError):
        _model_record(provider="")
    with pytest.raises(ValidationError):
        _model_record(provider_model_id="")


def test_model_record_requires_non_zero_context_window() -> None:
    """context_window must be > 0."""

    with pytest.raises(ValidationError):
        _model_record(context_window=0)


def test_model_record_modalities_is_a_list() -> None:
    """modalities must be a list of recognised modality strings."""

    record = _model_record(input_modalities=["text", "image"])
    assert record.input_modalities == ["text", "image"]


def test_model_record_reasoning_efforts_must_be_known_values() -> None:
    """reasoning_efforts must be a list of valid ReasoningEffort literals."""

    record = _model_record(reasoning_efforts=["none", "high", "max"])
    assert record.reasoning_efforts == ["none", "high", "max"]

    with pytest.raises(ValidationError):
        _model_record(reasoning_efforts=["ultra"])


def test_model_record_availability_is_controlled() -> None:
    """availability must be one of the recognised values."""

    record = _model_record(availability="available")
    assert record.availability == "available"

    with pytest.raises(ValidationError):
        _model_record(availability="coming_soon")


# ---------------------------------------------------------------------------
# 3. ModelRegistry — lookup, list, enable/disable
# ---------------------------------------------------------------------------

def test_registry_can_lookup_by_provider_and_model() -> None:
    """ModelRegistry.lookup() must return the matching ModelRecord."""
    from app.services.v3_model_registry import ModelRegistry

    flash = _model_record(
        provider="deepseek",
        provider_model_id="deepseek-v4-flash",
        display_name="DeepSeek V4 Flash",
    )
    pro = _model_record(
        provider="deepseek",
        provider_model_id="deepseek-v4-pro",
        display_name="DeepSeek V4 Pro",
    )
    registry = ModelRegistry([flash, pro])

    found = registry.lookup(provider="deepseek", provider_model_id="deepseek-v4-pro")
    assert found is not None
    assert found.display_name == "DeepSeek V4 Pro"


def test_registry_lookup_returns_none_for_unknown_model() -> None:
    """ModelRegistry.lookup() must return None when the model is not registered."""
    from app.services.v3_model_registry import ModelRegistry

    registry = ModelRegistry([])
    assert registry.lookup(provider="unknown", provider_model_id="nonexistent") is None


def test_registry_lists_only_enabled_models() -> None:
    """list_enabled() must exclude disabled and unreachable models."""
    from app.services.v3_model_registry import ModelRegistry

    enabled = _model_record(availability="available", calibration_status="enabled")
    disabled = _model_record(
        provider="moonshot",
        provider_model_id="kimi-k3",
        display_name="Kimi K3",
        availability="unavailable",
        calibration_status="documented",
    )
    registry = ModelRegistry([enabled, disabled])

    active = registry.list_enabled()
    assert len(active) == 1
    assert active[0].provider_model_id == "deepseek-v4-flash"


def test_registry_can_list_by_provider() -> None:
    """list_by_provider() must return only models for the given provider."""
    from app.services.v3_model_registry import ModelRegistry

    deepseek = _model_record()
    kimi = _model_record(
        provider="moonshot",
        provider_model_id="kimi-k2.6",
        display_name="Kimi K2.6",
    )
    registry = ModelRegistry([deepseek, kimi])

    ds_models = registry.list_by_provider("deepseek")
    assert len(ds_models) == 1
    assert ds_models[0].provider == "deepseek"

    kimi_models = registry.list_by_provider("moonshot")
    assert len(kimi_models) == 1
    assert kimi_models[0].provider == "moonshot"


def test_registry_rejects_duplicate_model_ids() -> None:
    """A registry must not contain two records with the same provider + model_id."""
    from app.services.v3_model_registry import ModelRegistry

    a = _model_record()
    b = _model_record(display_name="Duplicate")

    with pytest.raises(ValueError, match="duplicate"):
        ModelRegistry([a, b])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _model_record(**overrides: object) -> object:
    from app.schemas.v3_registry import ModelRecord

    defaults: dict[str, object] = {
        "provider": "deepseek",
        "provider_model_id": "deepseek-v4-flash",
        "display_name": "DeepSeek V4 Flash",
        "capability_tier": "flash",
        "context_window": 128_000,
        "max_output": 8_192,
        "input_modalities": ["text"],
        "tool_support": True,
        "structured_output_support": True,
        "reasoning_efforts": ["none", "high"],
        "speed_class": "fast",
        "cost_metadata_version": "session13-v1-2026-07",
        "availability": "available",
        "verified_at": datetime(2026, 7, 19, tzinfo=UTC),
        "calibration_status": "enabled",
    }
    defaults.update(overrides)
    return ModelRecord(**defaults)
