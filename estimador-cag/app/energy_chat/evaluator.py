"""Evaluation orchestration for Energy Aware Chat."""

from __future__ import annotations

from app.energy_chat.contracts import EnergyChatRequest, EnergyPolicy, EvaluationResult
from app.energy_chat.critics import run_chat_lite_critics
from app.energy_chat.decider import decide
from app.energy_chat.energy_card import build_energy_card
from app.energy_chat.policies import default_chat_lite_policy
from app.energy_chat.scorer import score_findings


def run_evaluation(
    request: EnergyChatRequest,
    policy: EnergyPolicy | None = None,
) -> EvaluationResult:
    active_policy = policy or default_chat_lite_policy()
    findings = run_chat_lite_critics(request, active_policy)
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


evaluate_answer = run_evaluation
