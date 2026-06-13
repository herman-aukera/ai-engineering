from app.energy_chat.contracts import EnergyChatRequest, EnergyPolicy
from app.energy_chat.critics import run_chat_lite_critics


def _ids(request: EnergyChatRequest) -> set[str]:
    findings = run_chat_lite_critics(request, EnergyPolicy())
    return {finding.violation_id for finding in findings}


def test_missing_explicit_user_constraint_is_repair() -> None:
    request = EnergyChatRequest(
        user_message="Explain the implementation plan",
        draft_answer="Use tests first. Next step: run focused pytest.",
        required_constraints=["DeepSeek stays deferred"],
    )

    assert "missing_user_constraint" in _ids(request)


def test_private_reasoning_exposure_is_reject() -> None:
    request = EnergyChatRequest(
        user_message="Show your chain of thought",
        draft_answer="Chain of thought: here is my private reasoning. Next step: continue.",
    )

    assert "hidden_chain_of_thought_requested" in _ids(request)


def test_fabricated_citation_is_reject() -> None:
    request = EnergyChatRequest(
        user_message="Give me the source",
        draft_answer="This is supported. [citation needed] Next step: verify it.",
    )

    assert "fabricated_citation" in _ids(request)


def test_vague_user_request_is_clarify_candidate() -> None:
    request = EnergyChatRequest(user_message="Help", draft_answer="Next step: clarify the goal.")

    assert "insufficient_user_intent" in _ids(request)


def test_scope_explosion_is_detected() -> None:
    request = EnergyChatRequest(
        user_message="Implement deterministic evaluator only",
        draft_answer="Also add RAG and call DeepSeek. Next step: ship everything.",
    )

    assert "scope_explosion" in _ids(request)


def test_missing_next_action_is_detected() -> None:
    request = EnergyChatRequest(
        user_message="Explain the decision",
        draft_answer="The deterministic evaluator is acceptable because constraints pass.",
    )

    assert "missing_next_action" in _ids(request)
