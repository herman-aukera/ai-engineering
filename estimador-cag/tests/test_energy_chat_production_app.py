"""Production composition-root tests for the isolated EACHAT service."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.energy_chat.production_app import create_production_app


def test_production_service_fails_closed_without_strict_msgpack(monkeypatch) -> None:
    monkeypatch.delenv("LANGGRAPH_STRICT_MSGPACK", raising=False)
    monkeypatch.setenv("EACHAT_ALLOW_IN_MEMORY", "true")
    service = create_production_app()

    with pytest.raises(RuntimeError, match="LANGGRAPH_STRICT_MSGPACK=true is required"):
        with TestClient(service):
            pass


def test_production_service_fails_closed_without_durable_storage(monkeypatch) -> None:
    monkeypatch.setenv("LANGGRAPH_STRICT_MSGPACK", "true")
    monkeypatch.delenv("EACHAT_POSTGRES_URL", raising=False)
    monkeypatch.delenv("EACHAT_ALLOW_IN_MEMORY", raising=False)
    service = create_production_app()

    with pytest.raises(RuntimeError, match="EACHAT_POSTGRES_URL is required"):
        with TestClient(service):
            pass


def test_explicit_in_memory_override_serves_v2_product_and_graph(monkeypatch) -> None:
    monkeypatch.setenv("LANGGRAPH_STRICT_MSGPACK", "true")
    monkeypatch.delenv("EACHAT_POSTGRES_URL", raising=False)
    monkeypatch.setenv("EACHAT_ALLOW_IN_MEMORY", "true")
    service = create_production_app()

    with TestClient(service) as client:
        health = client.get("/health")
        root = client.get("/", follow_redirects=False)
        demo = client.get("/energy-chat/v2/demo")
        response = client.post(
            "/energy-chat/v2/chat",
            json={"user_message": "Explain the safest release-validation step."},
        )

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "service": "eachat",
        "restart_persistent": False,
        "strict_msgpack": True,
    }
    assert root.status_code == 307
    assert root.headers["location"] == "/energy-chat/v2/demo"
    assert demo.status_code == 200
    assert demo.headers["x-content-type-options"] == "nosniff"
    assert response.status_code == 200
    assert response.json()["final_answer"]
    assert response.json()["energy_card_v2"]


def test_production_openapi_contains_only_eachat_business_routes(monkeypatch) -> None:
    monkeypatch.setenv("LANGGRAPH_STRICT_MSGPACK", "true")
    monkeypatch.delenv("EACHAT_POSTGRES_URL", raising=False)
    monkeypatch.setenv("EACHAT_ALLOW_IN_MEMORY", "true")
    service = create_production_app()

    with TestClient(service) as client:
        schema = client.get("/openapi.json").json()

    paths = set(schema["paths"])
    assert "/energy-chat/v2/chat" in paths
    assert "/energy-chat/v2/chat/human" in paths
    assert "/energy-chat/v2/threads/{thread_id}/replay" in paths
    assert not any(path.startswith("/estimations") for path in paths)
    assert not any(path.startswith("/embeddings") for path in paths)
