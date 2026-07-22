from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_fastapi_root_redirects_to_v2_product_by_default(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "true")
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/energy-chat/v2/demo"


def test_fastapi_root_preserves_legacy_rollback(monkeypatch) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "false")
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/energy-chat/demo"


def test_energy_chat_demo_route_serves_browser_ui() -> None:
    response = client.get("/energy-chat/demo")

    assert response.status_code == 200
    assert "Energy Aware Chat MVP Demo" in response.text
    assert "Visible execution audit" in response.text


def test_energy_chat_evaluate_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/evaluate" in schema["paths"]


def test_energy_chat_repair_once_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/evaluate/repair-once" in schema["paths"]


def test_energy_chat_rag_and_chat_routes_are_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/rag/search" in schema["paths"]
    assert "/energy-chat/chat" in schema["paths"]
    assert "/energy-chat/chat/live" in schema["paths"]


def test_energy_chat_deepseek_baseline_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/draft/deepseek-baseline" in schema["paths"]


def test_energy_chat_deepseek_benchmark_route_is_registered() -> None:
    schema = client.get("/openapi.json").json()

    assert "/energy-chat/benchmark/deepseek-energy-aware" in schema["paths"]


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
