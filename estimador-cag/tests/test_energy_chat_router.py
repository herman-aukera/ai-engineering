from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_energy_chat_evaluate_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/evaluate" in schema["paths"]


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
