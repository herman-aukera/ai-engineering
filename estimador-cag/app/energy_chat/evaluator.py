"""Evaluation orchestration for Energy Aware Chat."""

from __future__ import annotations

from app.energy_chat.contracts import (
    EnergyChatRequest,
    EnergyPolicy,
    EvaluationResult,
    RepairEvaluationResult,
)
from app.energy_chat.critics import run_chat_lite_critics
from app.energy_chat.decider import decide
from app.energy_chat.energy_card import build_energy_card
from app.energy_chat.policies import default_chat_lite_policy
from app.energy_chat.repairs import build_repaired_request
from app.energy_chat.scorer import score_findings
from app.energy_chat.source_guard import source_need_findings


def run_evaluation(
    request: EnergyChatRequest,
    policy: EnergyPolicy | None = None,
) -> EvaluationResult:
    active_policy = policy or default_chat_lite_policy()
    findings = [
        *run_chat_lite_critics(request, active_policy),
        *source_need_findings(request, active_policy),
    ]
    energy_score = score_findings(findings)
    decision = decide(energy_score, active_policy, request.evidence_refs)
    card = build_energy_card(decision, energy_score)
    return EvaluationResult(
        request=request,
        policy=active_policy,
        score=energy_score,
        decision=decision,
        energy_card=card,
    )


def evaluate_with_one_pass_repair(
    request: EnergyChatRequest,
    policy: EnergyPolicy | None = None,
) -> RepairEvaluationResult:
    """
    Evaluate a draft and apply one deterministic repair when the decider asks for repair.

    This Slice 4 seam is intentionally provider-free. It does not call a model;
    it only applies explicit repair text for known deterministic critic findings.
    """

    active_policy = policy or default_chat_lite_policy()
    initial_result = run_evaluation(request, active_policy)
    if initial_result.decision.decision != "repair" or active_policy.max_repairs_mvp < 1:
        return RepairEvaluationResult(
            initial_result=initial_result,
            final_result=initial_result,
            repair_attempted=False,
        )

    repaired_request, repairs_applied = build_repaired_request(request, initial_result)
    if repaired_request is None:
        return RepairEvaluationResult(
            initial_result=initial_result,
            final_result=initial_result,
            repair_attempted=False,
        )

    repaired_result = run_evaluation(repaired_request, active_policy)
    return RepairEvaluationResult(
        initial_result=initial_result,
        repaired_request=repaired_request,
        repaired_result=repaired_result,
        final_result=repaired_result,
        repair_attempted=True,
        repairs_applied=repairs_applied,
    )


evaluate_answer = run_evaluation
