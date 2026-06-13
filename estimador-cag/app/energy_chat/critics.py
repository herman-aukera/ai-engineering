from app.energy_chat.contracts import (
    ConstraintType,
    CriticFinding,
    DecisionType,
    EnergyChatRequest,
)


def run_chat_lite_critics(request: EnergyChatRequest) -> list[CriticFinding]:
    """Run deterministic Slice 1 critics for normal assistant answers."""

    findings: list[CriticFinding] = []
    user_message = request.user_message.lower()
    draft_answer = request.draft_answer.lower()

    if _is_ambiguous_intent(user_message):
        findings.append(
            CriticFinding(
                critic="instruction_critic",
                finding_id="insufficient_user_intent",
                constraint_type=ConstraintType.HARD_REPAIR,
                energy=400,
                message="The user intent is too ambiguous.",
                repair_hint="Ask a focused clarification question.",
                suggested_decision=DecisionType.CLARIFY,
            )
        )

    if _contains_credential_exposure(draft_answer):
        findings.append(
            CriticFinding(
                critic="credential_critic",
                finding_id="credential_exposure",
                constraint_type=ConstraintType.HARD_REJECT,
                energy=1000,
                message="The answer appears to expose a credential or private token.",
                repair_hint="Remove the credential-like content and use a safe placeholder.",
            )
        )

    if _claims_tests_or_validation_passed(draft_answer) and not request.evidence_refs:
        findings.append(
            CriticFinding(
                critic="evidence_critic",
                finding_id="unverified_success_claim",
                constraint_type=ConstraintType.HARD_REJECT,
                energy=900,
                message="The answer claims validation success without evidence references.",
                repair_hint="Remove the success claim or attach trusted validation evidence.",
            )
        )

    if _claims_production_ready(draft_answer) and not request.evidence_refs:
        findings.append(
            CriticFinding(
                critic="evidence_critic",
                finding_id="unverified_production_claim",
                constraint_type=ConstraintType.HARD_REPAIR,
                energy=700,
                message="The answer claims production readiness without evidence.",
                repair_hint="Add evidence or remove the claim.",
            )
        )

    return findings


def _is_ambiguous_intent(user_message: str) -> bool:
    words = [word for word in user_message.split() if word]
    return len(words) <= 2


def _contains_credential_exposure(draft_answer: str) -> bool:
    credential_phrases = (
        "private token",
        "real api key",
        "access token",
        "credential value",
    )
    return any(phrase in draft_answer for phrase in credential_phrases)


def _claims_tests_or_validation_passed(draft_answer: str) -> bool:
    success_phrases = (
        "tests pass",
        "all tests pass",
        "validation passed",
        "gates passed",
    )
    return any(phrase in draft_answer for phrase in success_phrases)


def _claims_production_ready(draft_answer: str) -> bool:
    return "production ready" in draft_answer or "fully validated" in draft_answer
