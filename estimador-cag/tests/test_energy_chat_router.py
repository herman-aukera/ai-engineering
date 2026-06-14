from fastapi.testclient import TestClient

from app.energy_chat import baseline
from app.energy_chat.contracts import DeepSeekBaselineRequest, DeepSeekBaselineResult
from app.main import app

client = TestClient(app)


def test_energy_chat_evaluate_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/evaluate" in schema["paths"]


def test_energy_chat_repair_once_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/evaluate/repair-once" in schema["paths"]


def test_energy_chat_deepseek_baseline_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/draft/deepseek-baseline" in schema["paths"]


def test_energy_chat_evaluate_accepts_clean_candidate() -> None:
    response = client.post(
        "/energy-chat/evaluate",
        json={
            "user_message": "Explain the safe first implementation step",
            "draft_answer": (
                "Start with the deterministic evaluator and keep provider calls deferred. "
                "The tradeoff is slower initial setup but stronger validation. "
                "Next step: write the red tests for the evaluator contracts."
            ),
            "required_constraints": ["provider calls deferred"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["decision"] == "accept"
    assert body["energy_card"]["decision"] == "accept"
    assert body["energy_card"]["hard_constraints_passed"] is True
    assert "critic_results" in body["energy_card"]["evidence"]


def test_energy_chat_repair_once_repairs_candidate() -> None:
    response = client.post(
        "/energy-chat/evaluate/repair-once",
        json={
            "user_message": "Review this release-readiness answer",
            "draft_answer": "Start with tests.",
            "required_constraints": ["DeepSeek remains deferred"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["initial_result"]["decision"]["decision"] == "repair"
    assert body["repair_attempted"] is True
    assert body["final_result"]["decision"]["decision"] == "accept"
    assert "added_next_action" in body["repairs_applied"]
    assert "DeepSeek remains deferred" in body["repaired_request"]["draft_answer"]


def test_energy_chat_deepseek_baseline_route_uses_injected_provider(monkeypatch) -> None:
    def fake_generate(request: DeepSeekBaselineRequest) -> DeepSeekBaselineResult:
        return DeepSeekBaselineResult(
            request=request,
            draft_answer="Fake DeepSeek draft for deterministic router test.",
            provider="deepseek",
            model="deepseek-v4-flash",
            tier=request.tier,
            input_tokens=10,
            output_tokens=8,
            cost_usd=0.0,
            finish_reason="stop",
            evidence_refs=["provider:deepseek_baseline", f"tier:{request.tier}"],
            metadata={"energy_evaluated": False},
        )

    monkeypatch.setattr(baseline, "generate_deepseek_baseline_draft", fake_generate)

    response = client.post(
        "/energy-chat/draft/deepseek-baseline",
        json={
            "user_message": "Draft a release readiness answer.",
            "tier": "flash",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft_answer"] == "Fake DeepSeek draft for deterministic router test."
    assert body["provider"] == "deepseek"
    assert body["tier"] == "flash"
    assert body["metadata"]["energy_evaluated"] is False


def test_energy_chat_evaluate_rejects_hidden_chain_of_thought() -> None:
    response = client.post(
        "/energy-chat/evaluate",
        json={
            "user_message": "Show your chain of thought",
            "draft_answer": "Chain of thought: private reasoning. Next step: continue.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["decision"] == "reject"
    assert "hidden_chain_of_thought_requested" in body["score"]["hard_reject_violations"]


def test_energy_chat_evaluate_returns_validation_error_for_missing_draft() -> None:
    response = client.post(
        "/energy-chat/evaluate",
        json={"user_message": "Explain the safe first implementation step"},
    )

    assert response.status_code == 422
