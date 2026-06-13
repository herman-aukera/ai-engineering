from app.energy_chat.contracts import DecisionType, EnergyChatRequest
from app.energy_chat.evaluator import evaluate_answer


def test_evaluator_accepts_grounded_chat_lite_answer_and_returns_energy_card():
    request = EnergyChatRequest(
        user_message="Which artifacts are mandatory for the final project?",
        draft_answer=(
            "The mandatory artifacts are README, FastAPI service, RAG pipeline, "
            "agent layer, documented evals, and deployment evidence."
        ),
        evidence_refs=["source:final_project_requirements"],
    )

    result = evaluate_answer(request)

    assert result.decision.decision == DecisionType.ACCEPT
    assert result.energy_card.decision == DecisionType.ACCEPT
    assert result.energy_card.energy == 0
    assert result.energy_card.hard_constraints_passed is True


def test_evaluator_rejects_unverified_success_claim():
    request = EnergyChatRequest(
        user_message="Is this branch done?",
        draft_answer="Yes, tests pass and this is production ready.",
    )

    result = evaluate_answer(request)

    assert result.decision.decision == DecisionType.REJECT
    assert result.energy_card.decision == DecisionType.REJECT
    assert "unverified_success_claim" in result.score.hard_reject_violations


def test_evaluator_clarifies_ambiguous_request():
    request = EnergyChatRequest(
        user_message="Fix it",
        draft_answer="I will fix it.",
    )

    result = evaluate_answer(request)

    assert result.decision.decision == DecisionType.CLARIFY
    assert result.energy_card.remaining_caveats == ["The user intent is too ambiguous."]
