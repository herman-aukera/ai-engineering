from app.energy_chat.contracts import ConstraintType, EnergyChatRequest
from app.energy_chat.critics import run_chat_lite_critics


def test_chat_lite_critics_accept_useful_grounded_answer_without_findings():
    request = EnergyChatRequest(
        user_message="Which artifacts are mandatory for the final project?",
        draft_answer=(
            "The mandatory artifacts are README, FastAPI service, RAG pipeline, "
            "agent layer, documented evals, and deployment evidence."
        ),
        evidence_refs=["source:final_project_requirements"],
    )

    findings = run_chat_lite_critics(request)

    assert findings == []


def test_chat_lite_critics_flag_unverified_success_claim_as_hard_reject():
    request = EnergyChatRequest(
        user_message="Is the implementation done?",
        draft_answer="Yes, all tests pass and the branch is production ready.",
    )

    findings = run_chat_lite_critics(request)

    assert any(f.finding_id == "unverified_success_claim" for f in findings)
    assert any(f.constraint_type == ConstraintType.HARD_REJECT for f in findings)


def test_chat_lite_critics_flag_secret_like_output_as_hard_reject():
    request = EnergyChatRequest(
        user_message="Show me the API key example.",
        draft_answer="Use Bearer abcdefghijklmnopqrstuvwxyz1234567890 in the header.",
    )

    findings = run_chat_lite_critics(request)

    assert [f.finding_id for f in findings] == ["secret_leak"]
    assert findings[0].constraint_type == ConstraintType.HARD_REJECT


def test_chat_lite_critics_request_clarification_for_ambiguous_user_intent():
    request = EnergyChatRequest(
        user_message="Fix it",
        draft_answer="I will fix the system.",
    )

    findings = run_chat_lite_critics(request)

    assert any(f.finding_id == "insufficient_user_intent" for f in findings)
    assert any(f.suggested_decision == "clarify" for f in findings)


def test_chat_lite_critics_repair_unverified_production_claim_without_evidence():
    request = EnergyChatRequest(
        user_message="Can I present this as final?",
        draft_answer="This is production ready and fully validated.",
    )

    findings = run_chat_lite_critics(request)

    assert any(f.finding_id == "unverified_production_claim" for f in findings)
    assert any(f.constraint_type == ConstraintType.HARD_REPAIR for f in findings)
