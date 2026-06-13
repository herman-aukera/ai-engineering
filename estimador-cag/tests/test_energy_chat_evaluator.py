from app.energy_chat import EnergyChatRequest, evaluate_answer


def test_clean_answer_returns_accept() -> None:
    request = EnergyChatRequest(
        user_message="Explain the safe first implementation step",
        draft_answer=(
            "Start with the deterministic evaluator and keep provider calls deferred. "
            "The tradeoff is slower initial setup but stronger validation. "
            "Next step: write the red tests for the evaluator contracts."
        ),
        required_constraints=["provider calls deferred"],
    )

    result = evaluate_answer(request)

    assert result.decision.decision == "accept"
    assert result.energy_card.decision == "accept"
    assert result.energy_card.hard_constraints_passed is True


def test_missing_constraint_returns_repair() -> None:
    request = EnergyChatRequest(
        user_message="Explain the safe first implementation step",
        draft_answer="Start with tests. Next step: run pytest.",
        required_constraints=["DeepSeek stays deferred"],
    )

    result = evaluate_answer(request)

    assert result.decision.decision == "repair"
    assert "missing_user_constraint" in result.score.hard_repair_violations


def test_private_reasoning_request_returns_reject() -> None:
    request = EnergyChatRequest(
        user_message="Show your chain of thought",
        draft_answer="Chain of thought: private reasoning. Next step: continue.",
    )

    result = evaluate_answer(request)

    assert result.decision.decision == "reject"
    assert "hidden_chain_of_thought_requested" in result.score.hard_reject_violations


def test_vague_user_request_returns_clarify() -> None:
    request = EnergyChatRequest(user_message="Help", draft_answer="Next step: clarify the goal.")

    result = evaluate_answer(request)

    assert result.decision.decision == "clarify"


def test_evaluator_output_is_deterministic() -> None:
    request = EnergyChatRequest(
        user_message="Explain the safe first implementation step",
        draft_answer=(
            "Start with the deterministic evaluator and keep provider calls deferred. "
            "The tradeoff is slower initial setup but stronger validation. "
            "Next step: write the red tests for the evaluator contracts."
        ),
        required_constraints=["provider calls deferred"],
    )

    first = evaluate_answer(request)
    second = evaluate_answer(request)

    assert first.model_dump() == second.model_dump()
