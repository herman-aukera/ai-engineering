from app.energy_chat.contracts import EnergyChatRequest, EvaluationResult
from app.energy_chat.critics import run_chat_lite_critics
from app.energy_chat.decider import decide
from app.energy_chat.energy_card import build_energy_card
from app.energy_chat.scorer import score_findings


def evaluate_answer(request: EnergyChatRequest) -> EvaluationResult:
    """Evaluate one draft answer with deterministic critics and a visible Energy Card."""

    findings = run_chat_lite_critics(request)
    score = score_findings(findings)
    decision = decide(score, findings)

    return EvaluationResult(
        request=request,
        score=score,
        decision=decision,
        energy_card=build_energy_card(decision),
    )
