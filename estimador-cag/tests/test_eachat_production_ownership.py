from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.energy_chat.identity import SignedSessionCodec
from app.energy_chat.production_app import create_production_app

_SIGNING_KEY = "eachat-ownership-test-signing-key-32-bytes-minimum"


def _headers(subject: str, tenant: str) -> dict[str, str]:
    token = SignedSessionCodec(_SIGNING_KEY.encode()).issue(
        subject=subject,
        tenant_id=tenant,
        roles=("member",),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    return {"Authorization": f"Bearer {token}"}


def _configure(monkeypatch) -> None:
    monkeypatch.setenv("LANGGRAPH_STRICT_MSGPACK", "true")
    monkeypatch.setenv("EACHAT_ALLOW_IN_MEMORY", "true")
    monkeypatch.setenv("EACHAT_SESSION_SIGNING_KEY", _SIGNING_KEY)
    monkeypatch.delenv("EACHAT_POSTGRES_URL", raising=False)
    monkeypatch.delenv("EACHAT_MEMORY_ENCRYPTION_KEY", raising=False)


def test_cross_tenant_conversation_access_is_rejected(monkeypatch) -> None:
    _configure(monkeypatch)
    alice = _headers("alice", "tenant-a")
    bob = _headers("bob", "tenant-b")

    with TestClient(create_production_app()) as client:
        created = client.post("/energy-chat/v2/conversations", headers=alice)
        assert created.status_code == 201
        conversation_id = created.json()["conversation_id"]

        assert client.get(
            f"/energy-chat/v2/conversations/{conversation_id}", headers=alice
        ).status_code == 200
        denied = client.get(
            f"/energy-chat/v2/conversations/{conversation_id}", headers=bob
        )
        assert denied.status_code == 403
        assert denied.json()["detail"]["reason_code"] == "tenant_mismatch"


def test_cross_tenant_thread_replay_is_rejected(monkeypatch) -> None:
    _configure(monkeypatch)
    alice = _headers("alice", "tenant-a")
    bob = _headers("bob", "tenant-b")
    thread_id = "thread-owned-by-alice"

    with TestClient(create_production_app()) as client:
        response = client.post(
            "/energy-chat/v2/chat",
            headers=alice,
            json={
                "user_message": "Give one deterministic release safety check.",
                "thread_id": thread_id,
            },
        )
        assert response.status_code == 200

        assert client.post(
            f"/energy-chat/v2/threads/{thread_id}/replay", headers=alice
        ).status_code == 200
        denied = client.post(
            f"/energy-chat/v2/threads/{thread_id}/replay", headers=bob
        )
        assert denied.status_code == 403
        assert denied.json()["detail"]["reason_code"] == "tenant_mismatch"
