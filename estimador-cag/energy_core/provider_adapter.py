"""Provider adapters for EACODE.

Fake adapter for deterministic CI. Opt-in live adapters for manual evidence.
No live API calls in CI. No provider keys required for deterministic tests.

Spec 0010 Slice E — additive module.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal, Protocol

from pydantic import Field

from energy_core.models import EnergyModel
from energy_core.provider_registry import (
    CapabilityRegistry,
    ModelCapability,
    ProviderSelection,
    ProviderSelector,
    ResolvedProvider,
)

ProviderAttemptStatus = Literal["success", "failed", "timed_out", "circuit_open"]


class TokenUsage(EnergyModel):
    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)


class ProviderAttempt(EnergyModel):
    attempt_index: int = Field(default=0, ge=0)
    provider: str = ""
    model_id: str = ""
    status: ProviderAttemptStatus = "success"
    latency_ms: int = Field(default=0, ge=0)
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    cost_usd: Decimal = Field(default=Decimal("0.0"), ge=0)
    error_message: str | None = None


class ProviderExecutionEvidence(EnergyModel):
    """Evidence that a provider was actually called and what was served.

    This is served-model proof, distinct from a planned ResolvedProvider.
    """

    requested_provider: str = ""
    requested_profile: str = ""
    planned_provider: str = ""
    planned_model_id: str = ""
    planned_effort: str = ""
    served_provider: str = ""
    served_model_id: str = ""
    served_effort: str = ""
    safe_provider_request_ref: str | None = None
    attempts: tuple[ProviderAttempt, ...] = Field(default_factory=tuple)
    circuit_state: str = "closed"
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: int = Field(default=0, ge=0)
    cost_usd: Decimal = Field(default=Decimal("0.0"), ge=0)
    capability_snapshot_hash: str = ""
    fallback_used: bool = False
    execution_performed: bool = False


class ProviderAdapter(Protocol):
    """Provider-neutral adapter protocol.

    Live adapters implement this. Fake adapters implement a subset.
    """

    def invoke(
        self,
        selection: ProviderSelection,
        *,
        messages: list[dict[str, str]] | None = None,
    ) -> ProviderExecutionEvidence:
        """Call the provider and return served-model evidence."""
        ...


class FakeProviderAdapter:
    """Deterministic fake provider adapter for CI.

    Produces synthetic ProviderExecutionEvidence without calling any API.
    Records the planned route as if it were served (for testing).
    Zero live API calls. Zero provider keys.
    """

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        *,
        served_model_id: str | None = None,
        served_effort: str | None = None,
        inject_failure: bool = False,
        inject_latency_ms: int = 100,
        inject_input_tokens: int = 500,
        inject_output_tokens: int = 200,
    ) -> None:
        self._registry = registry or CapabilityRegistry()
        self._selector = ProviderSelector(self._registry)
        self._served_model_id = served_model_id
        self._served_effort = served_effort
        self._inject_failure = inject_failure
        self._inject_latency_ms = inject_latency_ms
        self._inject_input_tokens = inject_input_tokens
        self._inject_output_tokens = inject_output_tokens
        self.calls = 0

    def invoke(
        self,
        selection: ProviderSelection,
        *,
        messages: list[dict[str, str]] | None = None,
    ) -> ProviderExecutionEvidence:
        """Produce deterministic fake served-model evidence."""
        self.calls += 1

        if self._inject_failure:
            return ProviderExecutionEvidence(
                requested_provider=selection.provider,
                requested_profile=selection.profile,
                served_provider="",
                served_model_id="",
                attempts=(
                    ProviderAttempt(
                        attempt_index=0,
                        provider=selection.provider,
                        status="failed",
                        error_message="Injected failure for deterministic CI",
                    ),
                ),
                circuit_state="open",
                execution_performed=False,
            )

        try:
            planned = self._selector.select(selection)
        except ValueError:
            return ProviderExecutionEvidence(
                requested_provider=selection.provider,
                requested_profile=selection.profile,
                served_provider="",
                served_model_id="",
                attempts=(
                    ProviderAttempt(
                        attempt_index=0,
                        provider=selection.provider,
                        status="failed",
                        error_message="Provider selection failed",
                    ),
                ),
                circuit_state="open",
                execution_performed=False,
            )

        served_model = self._served_model_id or planned.model_id
        served_effort = self._served_effort or planned.reasoning_effort

        cap = self._registry.get(served_model)
        total_cost = Decimal("0.0")
        if cap is not None:
            uncached = self._inject_input_tokens
            total_cost = (
                Decimal(str(uncached)) * cap.pricing.input_price_per_1k_tokens
                + Decimal(str(self._inject_output_tokens)) * cap.pricing.output_price_per_1k_tokens
            ) / 1000

        return ProviderExecutionEvidence(
            requested_provider=selection.provider,
            requested_profile=selection.profile,
            planned_provider=planned.provider,
            planned_model_id=planned.model_id,
            planned_effort=planned.reasoning_effort,
            served_provider=planned.provider,
            served_model_id=served_model,
            served_effort=served_effort,
            safe_provider_request_ref=f"fake-{_hash_ref(served_model)}",
            attempts=(
                ProviderAttempt(
                    attempt_index=0,
                    provider=planned.provider,
                    model_id=served_model,
                    status="success",
                    latency_ms=self._inject_latency_ms,
                    tokens=TokenUsage(
                        input_tokens=self._inject_input_tokens,
                        output_tokens=self._inject_output_tokens,
                    ),
                    cost_usd=total_cost,
                ),
            ),
            circuit_state="closed",
            tokens=TokenUsage(
                input_tokens=self._inject_input_tokens,
                output_tokens=self._inject_output_tokens,
            ),
            latency_ms=self._inject_latency_ms,
            cost_usd=total_cost,
            capability_snapshot_hash=planned.capability_snapshot_hash,
            fallback_used=planned.fallback_used,
            execution_performed=False,
        )


def _hash_ref(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]
