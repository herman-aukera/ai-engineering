"""End-to-end deterministic control-plane contract tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from energy_core.control_plane import (
    EnergyAwareControlPlane,
    GovernedProviderRequest,
)
from energy_core.provider_adapter import ProviderExecutionEvidence
from energy_core.provider_registry import ProviderSelection
from energy_core.secure_execution_service import LiveExecutionEvidence


class StubProvider:
    def __init__(self, evidence: ProviderExecutionEvidence) -> None:
        self.evidence = evidence

    def invoke(
        self,
        selection: ProviderSelection,
        *,
        messages: list[dict[str, str]] | None = None,
    ) -> ProviderExecutionEvidence:
        del selection, messages
        return self.evidence


def _provider_evidence(**updates: object) -> ProviderExecutionEvidence:
    payload: dict[str, object] = {
        "requested_provider": "deepseek",
        "requested_profile": "medium",
        "planned_provider": "deepseek",
        "planned_model_id": "deepseek-v4-flash",
        "planned_effort": "high",
        "served_provider": "deepseek",
        "served_model_id": "deepseek-v4-flash",
        "served_effort": "high",
        "latency_ms": 100,
        "cost_usd": Decimal("0.01"),
        "execution_performed": True,
    }
    payload.update(updates)
    return ProviderExecutionEvidence.model_validate(payload)


def _tool_evidence(**updates: object) -> LiveExecutionEvidence:
    payload: dict[str, object] = {
        "evidence_id": "tool-evidence-1",
        "run_id": "run-control-plane",
        "recorded_at": datetime.now(UTC),
        "status": "pass",
        "summary": "Secure live execution evidence recorded.",
        "live_plan_hash": "a" * 64,
        "base_plan_hash": "b" * 64,
        "repository_snapshot_hash": "c" * 64,
        "authorization_receipt_id": "receipt-control-plane",
        "authorization_record_hash": "d" * 64,
        "accepted_revision": 1,
        "authority_reserved": True,
        "authority_completion_verified": True,
        "execution_performed": True,
        "cleanup_verified": True,
        "exit_code": 0,
        "artifact_hash": "0" * 64,
        "trust_classification": "trusted",
    }
    payload.update(updates)
    draft = LiveExecutionEvidence.model_construct(**payload)
    payload["artifact_hash"] = draft.calculate_artifact_hash()
    return LiveExecutionEvidence.model_validate(payload)


def test_successful_provider_evidence_is_accepted_but_never_authorizes_action() -> None:
    request = GovernedProviderRequest(
        request_id="provider-success",
        selection=ProviderSelection(provider="deepseek", profile="medium"),
    )

    decision = EnergyAwareControlPlane().evaluate_provider(
        request,
        StubProvider(_provider_evidence()),
    )

    assert decision.disposition == "accept"
    assert decision.served is not None
    assert decision.downstream_action_authorized is False
    assert decision.decided_by == "deterministic-boss"


def test_missing_provider_execution_escalates() -> None:
    request = GovernedProviderRequest(
        request_id="provider-missing",
        selection=ProviderSelection(provider="deepseek", profile="medium"),
    )

    decision = EnergyAwareControlPlane().evaluate_provider(
        request,
        StubProvider(_provider_evidence(execution_performed=False)),
    )

    assert decision.disposition == "escalate"
    assert decision.served is None


def test_provider_cost_overrun_is_hard_reject() -> None:
    request = GovernedProviderRequest(
        request_id="provider-cost",
        selection=ProviderSelection(
            provider="deepseek",
            profile="medium",
            max_cost_usd=Decimal("0.01"),
        ),
    )

    decision = EnergyAwareControlPlane().evaluate_provider(
        request,
        StubProvider(_provider_evidence(cost_usd=Decimal("0.02"))),
    )

    assert decision.disposition == "reject"
    assert any(
        finding.get("hard_constraint_violation") is True
        for finding in decision.findings
    )


def test_unexplained_served_provider_mismatch_requires_repair() -> None:
    request = GovernedProviderRequest(
        request_id="provider-mismatch",
        selection=ProviderSelection(provider="deepseek", profile="medium"),
    )

    decision = EnergyAwareControlPlane().evaluate_provider(
        request,
        StubProvider(_provider_evidence(served_provider="kimi")),
    )

    assert decision.disposition == "repair"


def test_successful_tool_evidence_reenters_boss_without_granting_authority() -> None:
    decision = EnergyAwareControlPlane().evaluate_tool_evidence(_tool_evidence())

    assert decision.disposition == "accept"
    assert decision.evidence_type == "live_tool_execution"
    assert decision.downstream_action_authorized is False


def test_unverified_tool_cleanup_is_hard_reject() -> None:
    decision = EnergyAwareControlPlane().evaluate_tool_evidence(
        _tool_evidence(cleanup_verified=False, status="conflict")
    )

    assert decision.disposition == "reject"
    assert any(
        finding.get("hard_constraint_violation") is True
        for finding in decision.findings
    )
