"""Tests for provider adapters — deterministic CI only.

No live API calls. No provider keys required.
"""

from __future__ import annotations  # noqa: I001

from decimal import Decimal

from energy_core.provider_adapter import (
    FakeProviderAdapter,
    ProviderAttempt,
    ProviderExecutionEvidence,
    TokenUsage,
)
from energy_core.provider_registry import ProviderSelection


def _selection(**overrides) -> ProviderSelection:
    payload: dict = {"provider": "deepseek", "profile": "medium"}
    payload.update(overrides)
    return ProviderSelection.model_validate(payload)


# ------------------------------------------------------------------
# Fake adapter basic behavior
# ------------------------------------------------------------------


def test_fake_adapter_returns_evidence() -> None:
    adapter = FakeProviderAdapter()
    result = adapter.invoke(_selection())
    assert result.execution_performed is False
    assert result.served_provider == "deepseek"
    assert result.served_model_id != ""
    assert result.circuit_state == "closed"


def test_fake_adapter_increments_call_count() -> None:
    adapter = FakeProviderAdapter()
    assert adapter.calls == 0
    adapter.invoke(_selection())
    assert adapter.calls == 1
    adapter.invoke(_selection())
    assert adapter.calls == 2


def test_fake_adapter_records_planned_and_served() -> None:
    adapter = FakeProviderAdapter()
    result = adapter.invoke(_selection(provider="kimi", profile="max"))
    assert result.requested_provider == "kimi"
    assert result.requested_profile == "max"
    assert result.planned_provider == "kimi"
    assert result.planned_model_id == "k3"
    assert result.served_provider == "kimi"


def test_fake_adapter_uses_custom_served_model() -> None:
    adapter = FakeProviderAdapter(
        served_model_id="custom-model",
        served_effort="custom-effort",
    )
    result = adapter.invoke(_selection())
    assert result.served_model_id == "custom-model"
    assert result.served_effort == "custom-effort"


def test_fake_adapter_injects_failure() -> None:
    adapter = FakeProviderAdapter(inject_failure=True)
    result = adapter.invoke(_selection())
    assert len(result.attempts) == 1
    assert result.attempts[0].status == "failed"
    assert result.circuit_state == "open"


def test_fake_adapter_injects_token_counts() -> None:
    adapter = FakeProviderAdapter(inject_input_tokens=1000, inject_output_tokens=500)
    result = adapter.invoke(_selection())
    assert result.tokens.input_tokens == 1000
    assert result.tokens.output_tokens == 500


def test_fake_adapter_handles_unresolvable_selection() -> None:
    """Fake adapter must produce failure evidence when provider selection fails.

    Uses an unavailable model by creating a custom registry where the resolved
    model is unavailable, causing the selector to fail.
    """
    from energy_core.provider_registry import CapabilityRegistry
    caps = {
        "deepseek-v4-flash": CapabilityRegistry().get("deepseek-v4-flash").model_copy(
            update={"availability_state": "unavailable"}
        ),
        "deepseek-v4-pro": CapabilityRegistry().get("deepseek-v4-pro").model_copy(
            update={"availability_state": "unavailable"}
        ),
    }
    registry = CapabilityRegistry(caps)
    adapter = FakeProviderAdapter(registry=registry)
    result = adapter.invoke(_selection(provider="deepseek", profile="medium"))
    assert result.served_model_id == ""
    assert len(result.attempts) > 0
    assert result.attempts[0].status == "failed"


# ------------------------------------------------------------------
# Serialization round-trips
# ------------------------------------------------------------------


def test_provider_execution_evidence_round_trips() -> None:
    evidence = ProviderExecutionEvidence(
        requested_provider="deepseek",
        requested_profile="medium",
        served_provider="deepseek",
        served_model_id="deepseek-v4-flash",
        served_effort="high",
        safe_provider_request_ref="ref-abc",
        tokens=TokenUsage(input_tokens=500, output_tokens=200),
        latency_ms=150,
        cost_usd=Decimal("0.00035"),
    )
    dumped = evidence.model_dump(mode="json")
    reloaded = ProviderExecutionEvidence.model_validate(dumped)
    assert reloaded.served_model_id == "deepseek-v4-flash"
    assert reloaded.tokens.input_tokens == 500


def test_provider_attempt_round_trips() -> None:
    attempt = ProviderAttempt(
        attempt_index=0,
        provider="kimi",
        model_id="k3",
        status="success",
        latency_ms=200,
    )
    dumped = attempt.model_dump(mode="json")
    reloaded = ProviderAttempt.model_validate(dumped)
    assert reloaded.model_id == "k3"
    assert reloaded.status == "success"


# ------------------------------------------------------------------
# Defaults
# ------------------------------------------------------------------


def test_token_usage_defaults() -> None:
    tu = TokenUsage()
    assert tu.input_tokens == 0
    assert tu.output_tokens == 0
    assert tu.cached_input_tokens == 0
