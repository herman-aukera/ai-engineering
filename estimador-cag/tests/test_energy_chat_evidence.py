from fastapi.testclient import TestClient

from app.energy_chat.contracts import EnergyChatRequest, EvidenceBundleRequest
from app.energy_chat.evaluator import evaluate_answer
from app.energy_chat.evidence import build_evidence_bundle, build_evidence_item
from app.main import app

client = TestClient(app)


def test_evidence_item_marks_supported_prefixes_as_trusted() -> None:
    item = build_evidence_item("git:status-clean")

    assert item.source_type == "git"
    assert item.trusted is True
    assert "Trusted git evidence" in item.summary


def test_evidence_item_marks_unknown_prefix_as_untrusted() -> None:
    item = build_evidence_item("random-note-without-prefix")

    assert item.source_type == "unknown"
    assert item.trusted is False
    assert "Untrusted evidence ref" in item.summary


def test_project_evidence_bundle_extracts_git_and_test_command_refs() -> None:
    result = build_evidence_bundle(
        EvidenceBundleRequest(
            mode="project",
            evidence_refs=["file:docs/energy_aware_chat_demo.md", "file:docs/energy_aware_chat_demo.md"],
            command_outputs={
                "git status --short": "",
                "energy chat validation gate": "325 passed in 5.02s",
            },
        )
    )

    assert result.trusted_refs == [
        "file:docs/energy_aware_chat_demo.md",
        "git:status-clean",
        "test:pytest-passed",
    ]
    assert result.can_support_project_claim is True
    assert result.missing_required_kinds == []
    assert result.next_action == "Use the trusted refs as evidence_refs on the evaluation request."


def test_project_evidence_bundle_reports_missing_validation_evidence() -> None:
    result = build_evidence_bundle(
        EvidenceBundleRequest(
            mode="project",
            evidence_refs=["git:status-clean"],
        )
    )

    assert result.can_support_project_claim is False
    assert result.missing_required_kinds == ["project_state_and_validation_evidence"]


def test_research_evidence_bundle_accepts_web_or_source_refs() -> None:
    result = build_evidence_bundle(
        EvidenceBundleRequest(
            mode="research",
            evidence_refs=["web:official-docs", "source:release-notes"],
        )
    )

    assert result.can_support_current_claim is True
    assert result.missing_required_kinds == []


def test_project_evaluation_accepts_refs_from_evidence_bundle() -> None:
    bundle = build_evidence_bundle(
        EvidenceBundleRequest(
            mode="project",
            evidence_refs=["git:status-clean", "test:325-passed"],
        )
    )

    result = evaluate_answer(
        EnergyChatRequest(
            user_message="Does this branch satisfy the validation gate?",
            draft_answer=(
                "The branch has validation evidence and the tradeoff is keeping "
                "the gate strict. Next action: attach the git and test evidence "
                "before claiming success."
            ),
            mode="project",
            evidence_refs=bundle.trusted_refs,
        )
    )

    assert result.decision.decision == "accept"
    assert result.score.hard_repair_violations == []


def test_evidence_bundle_route_is_registered_and_returns_trusted_refs() -> None:
    schema = client.get("/openapi.json").json()
    assert "/energy-chat/evidence/bundle" in schema["paths"]

    response = client.post(
        "/energy-chat/evidence/bundle",
        json={
            "mode": "project",
            "evidence_refs": ["git:status-clean"],
            "command_outputs": {
                "energy chat validation gate": "325 passed in 5.02s",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["can_support_project_claim"] is True
    assert body["trusted_refs"] == ["git:status-clean", "test:pytest-passed"]
