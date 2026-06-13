import pytest
from pydantic import ValidationError

from app.energy_chat.contracts import (
    ChatMode,
    ConstraintType,
    DecisionType,
    EnergyCard,
    EnergyChatRequest,
)


def test_energy_chat_request_serializes_mode_and_evidence_refs():
    request = EnergyChatRequest(
        user_message="Explain the mandatory final project deliverables.",
        draft_answer="The final project needs a README, RAG, agents, evals, and deployment evidence.",
        mode=ChatMode.CHAT_LITE,
        evidence_refs=["source:final_project_requirements"],
    )

    payload = request.model_dump(mode="json")

    assert payload["mode"] == "chat_lite"
    assert payload["evidence_refs"] == ["source:final_project_requirements"]


def test_energy_chat_request_rejects_empty_user_message_or_answer():
    with pytest.raises(ValidationError):
        EnergyChatRequest(user_message="", draft_answer="Useful answer")

    with pytest.raises(ValidationError):
        EnergyChatRequest(user_message="Useful question", draft_answer="")


def test_energy_card_is_visible_decision_contract():
    card = EnergyCard(
        decision=DecisionType.REPAIR,
        energy=700,
        hard_constraints_passed=False,
        repairs=1,
        evidence=["critic:no_answer"],
        remaining_caveats=["The draft answer is empty."],
    )

    assert card.model_dump(mode="json") == {
        "decision": "repair",
        "energy": 700,
        "hard_constraints_passed": False,
        "repairs": 1,
        "evidence": ["critic:no_answer"],
        "remaining_caveats": ["The draft answer is empty."],
    }


def test_constraint_type_enum_values_are_stable_for_reports():
    assert ConstraintType.HARD_REJECT == "hard_reject"
    assert ConstraintType.HARD_REPAIR == "hard_repair"
    assert ConstraintType.SOFT == "soft"
