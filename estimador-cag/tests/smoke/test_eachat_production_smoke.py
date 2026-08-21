from __future__ import annotations

from fastapi.testclient import TestClient

from app.energy_chat.production_app import create_production_app


def test_eachat_keyless_production_shell_smoke(monkeypatch) -> None:
    monkeypatch.setenv("LANGGRAPH_STRICT_MSGPACK", "true")
    monkeypatch.setenv("EACHAT_ALLOW_IN_MEMORY", "true")
    monkeypatch.setenv("GIT_SHA", "eachat-smoke")
    monkeypatch.delenv("EACHAT_POSTGRES_URL", raising=False)
    monkeypatch.delenv("EACHAT_MEMORY_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_API_KEY", raising=False)

    with TestClient(create_production_app()) as client:
        startup = client.get("/startup")
        health = client.get("/health")
        ready = client.get("/ready")
        version = client.get("/version")
        demo = client.get("/energy-chat/v2/demo")

    assert startup.json() == {"status": "started", "started": True}
    assert health.status_code == 200
    assert health.json()["service"] == "eachat"
    assert ready.status_code == 200
    assert ready.json()["ready"] is True
    assert ready.json()["restart_persistent"] is False
    assert version.json()["git_sha"] == "eachat-smoke"
    assert demo.status_code == 200
    assert demo.headers["cache-control"] == "no-store"
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"


def test_eachat_canonical_versioned_surface_is_v2() -> None:
    paths = {getattr(route, "path", "") for route in create_production_app().routes}
    canonical = sorted(path for path in paths if path.startswith("/energy-chat/v"))

    assert canonical
    assert all(path.startswith("/energy-chat/v2/") for path in canonical)
