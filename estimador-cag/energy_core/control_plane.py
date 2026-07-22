"""Provider-neutral Energy-Aware control plane for EACODE.

This service sits between providers/tools and downstream actions. Provider or tool
adapters return evidence; deterministic critics and the boss own disposition. A
control-plane decision never grants process authority by itself.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol

from pydantic import Field

from energy_core.models import EnergyModel
from energy_core.multi_agent import DeterministicBoss, MultiAgentRun
from energy_core.provider_adapter import ProviderExecutionEvidence
from energy_core.provider_registry import ProviderSelection, ResolvedProvider
from energy_core.provider_verified import VerifiedProviderSelector
from energy_core.secure_execution_service import LiveExecutionEvidence


class ProviderPort(Protocol):
    def invoke(
        self,
        selection: ProviderSelection,
        *,
        messages: list[dict[str, str]] | None = None,
    ) -> ProviderExecutionEvidence:
        """Return provider execution evidence without deciding acceptance."""


class GovernedProviderRequest(EnergyModel):
    """One provider request plus candidate findings for deterministic review."""

    request_id: str = Field(min_length=1)
    selection: ProviderSelection
    messages: tuple[dict[str, str], ...] = Field(default_factory=tuple)
    candidate_findings: tuple[dict[str, Any], ...] = Field(default_factory=tuple)


class ControlPlaneDecision(EnergyModel):
    """Deterministic decision over provider or tool evidence."""

    request_id: str = Field(min_length=1)
    evidence_type: str
    requested: dict[str, Any] = Field(default_factory=dict)
    planned: dict[str, Any] | None = None
    served: dict[str, Any] | None = None
    evidence_status: str
    findings: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    disposition: str
    decided_by: str = "deterministic-boss"
    downstream_action_authorized: bool = False
    claim_boundary: str = (
        "This decision evaluates evidence. It does not create process authority "
        "or allow a model, provider, or tool to approve itself."
    )


class EnergyAwareControlPlane:
    """Evaluate provider and secure-tool evidence through critics and boss."""

    def __init__(
        self,
        *,
        selector: VerifiedProviderSelector | None = None,
        boss: DeterministicBoss | None = None,
    ) -> None:
        self._selector = selector or VerifiedProviderSelector()
        self._boss = boss or DeterministicBoss()

    def evaluate_provider(
        self,
        request: GovernedProviderRequest,
        adapter: ProviderPort,
    ) -> ControlPlaneDecision:
        """Call one provider adapter and reevaluate its evidence deterministically."""

        planned = self._selector.select(request.selection)
        evidence = adapter.invoke(
            request.selection,
            messages=[dict(message) for message in request.messages],
        )
        findings = list(request.candidate_findings)
        findings.extend(_provider_critic_findings(request.selection, planned, evidence))
        governed = self._boss.aggregate(
            MultiAgentRun(run_id=f"provider-{request.request_id}"),
            findings=findings,
        )

        return ControlPlaneDecision(
            request_id=request.request_id,
            evidence_type="provider_execution",
            requested=request.selection.model_dump(mode="json"),
            planned=planned.model_dump(mode="json"),
            served={
                "provider": evidence.served_provider,
                "model_id": evidence.served_model_id,
                "effort": evidence.served_effort,
                "request_ref": evidence.safe_provider_request_ref,
            }
            if evidence.execution_performed
            else None,
            evidence_status="pass" if evidence.execution_performed else "missing",
            findings=tuple(findings),
            disposition=governed.final_disposition or "escalate",
            decided_by=governed.decided_by,
            downstream_action_authorized=False,
        )

    def evaluate_tool_evidence(
        self,
        evidence: LiveExecutionEvidence,
        *,
        candidate_findings: tuple[dict[str, Any], ...] = (),
    ) -> ControlPlaneDecision:
        """Reevaluate normalized tool evidence after secure execution."""

        findings = list(candidate_findings)
        findings.extend(_tool_critic_findings(evidence))
        governed = self._boss.aggregate(
            MultiAgentRun(run_id=f"tool-{evidence.run_id}"),
            findings=findings,
        )
        return ControlPlaneDecision(
            request_id=evidence.run_id,
            evidence_type="live_tool_execution",
            requested={"live_plan_hash": evidence.live_plan_hash},
            planned={
                "repository_snapshot_hash": evidence.repository_snapshot_hash,
                "authorization_receipt_id": evidence.authorization_receipt_id,
            },
            served={
                "execution_performed": evidence.execution_performed,
                "exit_code": evidence.exit_code,
                "cleanup_verified": evidence.cleanup_verified,
            },
            evidence_status=evidence.status,
            findings=tuple(findings),
            disposition=governed.final_disposition or "escalate",
            decided_by=governed.decided_by,
            downstream_action_authorized=False,
        )


def _provider_critic_findings(
    selection: ProviderSelection,
    planned: ResolvedProvider,
    evidence: ProviderExecutionEvidence,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    if not evidence.execution_performed:
        return [
            {
                "owner": "provider-evidence-critic",
                "disposition": "escalate",
                "reason": "provider_execution_missing",
            }
        ]

    if not evidence.served_provider or not evidence.served_model_id:
        findings.append(
            {
                "owner": "provider-evidence-critic",
                "disposition": "repair",
                "reason": "served_identity_missing",
            }
        )
    elif (
        evidence.served_provider != planned.provider
        and not evidence.fallback_used
    ):
        findings.append(
            {
                "owner": "provider-route-critic",
                "disposition": "repair",
                "reason": "unexplained_provider_mismatch",
            }
        )

    if evidence.cost_usd > selection.max_cost_usd:
        findings.append(
            {
                "owner": "provider-budget-critic",
                "disposition": "reject",
                "reason": "cost_budget_exceeded",
                "hard_constraint_violation": True,
            }
        )
    if (
        selection.max_latency_ms is not None
        and evidence.latency_ms > selection.max_latency_ms
    ):
        findings.append(
            {
                "owner": "provider-budget-critic",
                "disposition": "repair",
                "reason": "latency_budget_exceeded",
            }
        )

    if not findings:
        findings.append(
            {
                "owner": "provider-evidence-critic",
                "disposition": "accept",
                "reason": "provider_evidence_sufficient",
            }
        )
    return findings


def _tool_critic_findings(
    evidence: LiveExecutionEvidence,
) -> list[dict[str, Any]]:
    if not evidence.execution_performed:
        return [
            {
                "owner": "tool-evidence-critic",
                "disposition": "escalate",
                "reason": "process_not_started",
            }
        ]
    if not evidence.authority_completion_verified:
        return [
            {
                "owner": "tool-authority-critic",
                "disposition": "reject",
                "reason": "authority_completion_unverified",
                "hard_constraint_violation": True,
            }
        ]
    if not evidence.cleanup_verified or evidence.status == "conflict":
        return [
            {
                "owner": "tool-cleanup-critic",
                "disposition": "reject",
                "reason": "cleanup_unverified",
                "hard_constraint_violation": True,
            }
        ]
    if evidence.status == "fail" or evidence.exit_code not in (0, None):
        return [
            {
                "owner": "tool-result-critic",
                "disposition": "repair",
                "reason": "tool_execution_failed",
            }
        ]
    return [
        {
            "owner": "tool-evidence-critic",
            "disposition": "accept",
            "reason": "tool_evidence_sufficient",
        }
    ]
