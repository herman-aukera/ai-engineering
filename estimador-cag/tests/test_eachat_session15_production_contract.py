from fastapi.testclient import TestClient

from app.energy_chat.production_app import create_production_app

_SIGNING_KEY = "eachat-contract-signing-key-32-bytes-minimum"


def test_eachat_production_probes_are_local_and_llm_free(monkeypatch) -> None:
    monkeypatch.setenv("LANGGRAPH_STRICT_MSGPACK", "true")
    monkeypatch.setenv("EACHAT_ALLOW_IN_MEMORY", "true")
    monkeypatch.setenv("EACHAT_SESSION_SIGNING_KEY", _SIGNING_KEY)
    monkeypatch.delenv("EACHAT_POSTGRES_URL", raising=False)
    monkeypatch.delenv("EACHAT_MEMORY_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_API_KEY", raising=False)

    with TestClient(create_production_app()) as client:
        startup = client.get("/startup")
        assert startup.status_code == 200
        assert startup.json() == {"status": "started", "started": True}

        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.json()["service"] == "eachat"

        ready = client.get("/ready")
        assert ready.status_code == 200
        assert ready.json()["ready"] is True
        assert ready.json()["restart_persistent"] is False
        assert ready.json()["conversation_restart_persistent"] is False
        assert ready.json()["ownership_restart_persistent"] is False
        assert ready.json()["identity_required"] is True
        assert ready.json()["strict_msgpack"] is True
        assert ready.json()["byok_enabled"] is False


def test_eachat_version_exposes_safe_release_identity(monkeypatch) -> None:
    monkeypatch.setenv("LANGGRAPH_STRICT_MSGPACK", "true")
    monkeypatch.setenv("EACHAT_ALLOW_IN_MEMORY", "true")
    monkeypatch.setenv("EACHAT_SESSION_SIGNING_KEY", _SIGNING_KEY)
    monkeypatch.setenv("GIT_SHA", "abc123")
    monkeypatch.delenv("EACHAT_POSTGRES_URL", raising=False)

    with TestClient(create_production_app()) as client:
        payload = client.get("/version").json()

    assert payload == {"service": "eachat", "version": "0.4.0", "git_sha": "abc123"}
