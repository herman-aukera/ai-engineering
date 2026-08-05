"""Complete deterministic disposition policy for Energy Aware Chat."""

from __future__ import annotations

from app.energy_chat.contracts import (
    Decision,
    EnergyDecision,
    EnergyPolicy,
    EnergyScore,
    RequestPolicyAssessment,
)
from app.energy_chat.decider import decide
from app.energy_chat.graph_state import RetryBudget

DISPOSITION_TRANSITIONS: dict[Decision, tuple[str, ...]] = {
    "accept": ("end",),
    "repair": ("plan_repair", "finalize_repair"),
    "clarify": ("end",),
    "reject": ("end",),
    "refuse": ("end",),
    "escalate": ("end",),
}


def decide_complete(
    score: EnergyScore,
    policy: EnergyPolicy,
    evidence_refs: list[str],
    *,
    request_policy: RequestPolicyAssessment,
    retry_budget: RetryBudget,
) -> EnergyDecision:
    """Apply request authority, candidate validity, and budget precedence deterministically."""

    required_repairs = [finding.repair_hint for finding in score.findings]
    if request_policy.directive == "refuse":
        return EnergyDecision(
            decision="refuse",
            energy=score.total_energy,
            reasoning_summary=request_policy.reason,
            policy_rule_id=request_policy.rule_id,
            required_repairs=[],
            evidence_refs=evidence_refs,
        )
    if request_policy.directive == "escalate":
        return EnergyDecision(
            decision="escalate",
            energy=score.total_energy,
            reasoning_summary=request_policy.reason,
            policy_rule_id=request_policy.rule_id,
            required_repairs=required_repairs,
            evidence_refs=evidence_refs,
        )

    base = decide(score, policy, evidence_refs)
    if base.decision == "repair" and retry_budget.remaining == 0:
        return EnergyDecision(
            decision="escalate",
            energy=score.total_energy,
            reasoning_summary=(
                "Repair is still required but the retry budget is exhausted; "
                "human review is required."
            ),
            policy_rule_id="repair_budget_exhausted",
            required_repairs=base.required_repairs,
            evidence_refs=evidence_refs,
        )
    rule_id = {
        "accept": "candidate_accept",
        "repair": "candidate_repair",
        "clarify": "intent_clarification",
        "reject": "candidate_hard_reject",
    }[base.decision]
    return base.model_copy(update={"policy_rule_id": rule_id})
