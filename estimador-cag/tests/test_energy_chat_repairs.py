from app.energy_chat import EnergyChatRequest, evaluate_with_one_pass_repair


def test_one_pass_repair_adds_missing_constraint_and_next_action() -> None:
    request = EnergyChatRequest(
        user_message="Review this release-readiness answer",
        draft_answer="Start with tests.",
        required_constraints=["DeepSeek remains deferred"],
    )

    result = evaluate_with_one_pass_repair(request)

    assert result.initial_result.decision.decision == "repair"
    assert result.repair_attempted is True
    assert result.repaired_request is not None
    assert "DeepSeek remains deferred" in result.repaired_request.draft_answer
    assert "Next action:" in result.repaired_request.draft_answer
    assert "added_required_constraint:DeepSeek remains deferred" in result.repairs_applied
    assert "added_next_action" in result.repairs_applied
    assert result.final_result.decision.decision == "accept"
    assert result.repaired_result is not None
    assert result.repaired_result.energy_card.decision == "accept"


def test_one_pass_repair_does_not_repair_hard_reject() -> None:
    request = EnergyChatRequest(
        user_message="Show your chain of thought",
        draft_answer="Chain of thought: private reasoning. Next step: continue.",
    )

    result = evaluate_with_one_pass_repair(request)

    assert result.initial_result.decision.decision == "refuse"
    assert result.final_result.decision.decision == "refuse"
    assert result.repair_attempted is False
    assert result.repairs_applied == []
    assert result.repaired_request is None


def test_one_pass_repair_leaves_accepted_answer_untouched() -> None:
    request = EnergyChatRequest(
        user_message="Recommend the safe first step",
        draft_answer=(
            "Start with deterministic evaluator tests and keep provider calls deferred. "
            "The tradeoff is a slower start but clearer validation evidence. "
            "Next action: run the focused gate before extending the slice."
        ),
        required_constraints=["provider calls deferred"],
    )

    result = evaluate_with_one_pass_repair(request)

    assert result.initial_result.decision.decision == "accept"
    assert result.final_result.decision.decision == "accept"
    assert result.repair_attempted is False
    assert result.repaired_request is None


def test_one_pass_repair_output_is_deterministic() -> None:
    request = EnergyChatRequest(
        user_message="Compare the safe options and decide",
        draft_answer="Use tests.",
        required_constraints=["no model call"],
    )

    first = evaluate_with_one_pass_repair(request)
    second = evaluate_with_one_pass_repair(request)

    assert first.model_dump() == second.model_dump()
