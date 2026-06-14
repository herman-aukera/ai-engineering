from fastapi.testclient import TestClient

from app.energy_chat.contracts import EnergyChatRequest, SourceNeedRequest
from app.energy_chat.evaluator import evaluate_answer
from app.energy_chat.source_guard import classify_source_need
from app.main import app

client = TestClient(app)


def test_chat_lite_stable_request_does_not_require_sources() -> None:
    result = classify_source_need(
        SourceNeedRequest(
            user_message="Review this deterministic local answer.",
            draft_answer="Next action: keep the evaluator scoped and run tests.",
        )
    )

    assert result.decision == "sources_not_required"
    assert result.requires_current_sources is False
    assert result.requires_project_sources is False
    assert result.missing_evidence is False


def test_research_version_claim_requires_sources_without_evidence() -> None:
    result = classify_source_need(
        SourceNeedRequest(
            user_message="Which current API version should the project mention?",
            draft_answer="The current API version should be checked before publishing.",
            mode="research",
        )
    )

    assert result.decision == "sources_required"
    assert result.requires_current_sources is True
    assert result.missing_evidence is True
    assert "current" in result.detected_markers


def test_research_version_claim_with_evidence_is_recommended_not_required() -> None:
    result = classify_source_need(
        SourceNeedRequest(
            user_message="Which current API version should the project mention?",
            draft_answer="The answer cites retrieved official docs.",
            mode="research",
            evidence_refs=["web:official_docs"],
        )
    )

    assert result.decision == "sources_recommended"
    assert result.missing_evidence is False
    assert result.evidence_refs == ["web:official_docs"]


def test_project_mode_requires_project_evidence() -> None:
    result = classify_source_need(
        SourceNeedRequest(
            user_message="Does this branch satisfy the validation gate?",
            draft_answer="The repo is clean and pytest passed.",
            mode="project",
        )
    )

    assert result.decision == "sources_required"
    assert result.requires_project_sources is True
    assert result.missing_evidence is True
    assert "branch" in result.detected_markers


def test_project_mode_with_git_evidence_is_not_missing_evidence() -> None:
    result = classify_source_need(
        SourceNeedRequest(
            user_message="Does this branch satisfy the validation gate?",
            draft_answer="The branch has git and test evidence.",
            mode="project",
            evidence_refs=["git:status-clean", "test:304-passed"],
        )
    )

    assert result.decision == "sources_recommended"
    assert result.missing_evidence is False


def test_evaluator_repairs_research_answer_without_current_sources() -> None:
    result = evaluate_answer(
        EnergyChatRequest(
            user_message="Which current API version should the project mention?",
            draft_answer=(
                "The current API version should be checked. "
                "The tradeoff is precision versus speed. "
                "Next action: verify the official docs."
            ),
            mode="research",
        )
    )

    assert result.decision.decision == "repair"
    assert "unsupported_current_claim" in result.score.hard_repair_violations


def test_evaluator_accepts_project_answer_with_evidence_refs() -> None:
    result = evaluate_answer(
        EnergyChatRequest(
            user_message="Does this branch satisfy the validation gate?",
            draft_answer=(
                "The branch has test evidence and the tradeoff is keeping the gate strict. "
                "Next action: keep the validation output attached before claiming success."
            ),
            mode="project",
            evidence_refs=["git:status-clean", "test:304-passed"],
        )
    )

    assert result.decision.decision == "accept"
    assert result.score.hard_repair_violations == []


def test_source_needed_route_is_registered_and_classifies_request() -> None:
    schema = client.get("/openapi.json").json()
    assert "/energy-chat/source-needed" in schema["paths"]

    response = client.post(
        "/energy-chat/source-needed",
        json={
            "user_message": "Which current API version should the project mention?",
            "draft_answer": "The current API version should be verified.",
            "mode": "research",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "sources_required"
    assert body["requires_current_sources"] is True
    assert body["missing_evidence"] is True
