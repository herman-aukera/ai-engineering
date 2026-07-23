"""Pure, serializable provider circuit-breaker transitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

CircuitStatus = Literal["closed", "open", "half_open"]


@dataclass(frozen=True)
class ProviderCircuit:
    status: CircuitStatus = "closed"
    failure_count: int = 0
    opened_at_ms: int | None = None
    threshold: int = 3
    cooldown_ms: int = 30_000

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def before_provider_call(circuit: ProviderCircuit, *, now_ms: int) -> ProviderCircuit:
    """Reject open calls or allow one deterministic half-open probe."""

    if circuit.status != "open":
        return circuit
    if circuit.opened_at_ms is None or now_ms - circuit.opened_at_ms < circuit.cooldown_ms:
        raise RuntimeError("provider circuit is open")
    return ProviderCircuit(
        status="half_open",
        failure_count=circuit.failure_count,
        opened_at_ms=circuit.opened_at_ms,
        threshold=circuit.threshold,
        cooldown_ms=circuit.cooldown_ms,
    )


def record_provider_success(circuit: ProviderCircuit) -> ProviderCircuit:
    return ProviderCircuit(threshold=circuit.threshold, cooldown_ms=circuit.cooldown_ms)


def record_provider_failure(
    circuit: ProviderCircuit, *, now_ms: int
) -> ProviderCircuit:
    failures = circuit.failure_count + 1
    opened = failures >= circuit.threshold or circuit.status == "half_open"
    return ProviderCircuit(
        status="open" if opened else "closed",
        failure_count=failures,
        opened_at_ms=now_ms if opened else None,
        threshold=circuit.threshold,
        cooldown_ms=circuit.cooldown_ms,
    )
