from __future__ import annotations

import pytest

from app.generation.graph.nodes.review_policy import build_boss_action_node
from app.services.provider_circuit import (
    ProviderCircuit,
    before_provider_call,
    record_provider_failure,
    record_provider_success,
)


def _state(action: str, *, next_provider: str | None = None) -> dict[str, object]:
    return {
        "boss_decision": {
            "action": action,
            "next_provider": next_provider,
            "issue_codes": ["unreliable_estimate"],
        },
        "execution_budgets": {
            "retry_count": 0,
            "retry_limit": 2,
            "fallback_count": 0,
            "fallback_limit": 1,
            "tool_call_count": 0,
            "tool_call_limit": 8,
        },
        "execution_metadata": {"provider_failure": "timeout"},
    }


@pytest.mark.asyncio
async def test_retry_is_an_operational_bounded_recovery_transition() -> None:
    result = await build_boss_action_node()(_state("retry_selected"))
    assert result["boss_route"] == "recover"
    assert result["execution_budgets"]["retry_count"] == 1
    assert result["execution_budgets"]["tool_call_count"] == 1


@pytest.mark.asyncio
async def test_fallback_switches_provider_and_consumes_budget() -> None:
    result = await build_boss_action_node()(
        _state("fallback_provider", next_provider="kimi")
    )
    assert result["boss_route"] == "recover"
    assert result["active_provider"] == "kimi"
    assert result["execution_metadata"]["provider_failure"] == "none"
    assert result["execution_budgets"]["fallback_count"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "route"), [("accept", "final_review"), ("human_review", "final_review"), ("reject", "stop")]
)
async def test_terminal_boss_actions_have_explicit_routes(action: str, route: str) -> None:
    result = await build_boss_action_node()(_state(action))
    assert result["boss_route"] == route


def test_provider_circuit_opens_blocks_probes_and_recovers() -> None:
    circuit = ProviderCircuit(threshold=2, cooldown_ms=100)
    circuit = record_provider_failure(circuit, now_ms=10)
    assert circuit.status == "closed"
    circuit = record_provider_failure(circuit, now_ms=20)
    assert circuit.status == "open"
    with pytest.raises(RuntimeError, match="circuit is open"):
        before_provider_call(circuit, now_ms=119)
    probe = before_provider_call(circuit, now_ms=120)
    assert probe.status == "half_open"
    assert record_provider_success(probe).status == "closed"


def test_failed_half_open_probe_reopens_circuit() -> None:
    circuit = ProviderCircuit(
        status="half_open", failure_count=3, opened_at_ms=10, threshold=3
    )
    reopened = record_provider_failure(circuit, now_ms=50)
    assert reopened.status == "open"
    assert reopened.opened_at_ms == 50
