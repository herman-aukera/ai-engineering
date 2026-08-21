from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.estimator.identity import SignedSessionCodec

_SIGNING_KEY = "estimator-ownership-test-key-32-bytes-minimum"


class _CaptureService:
    def __init__(self) -> None:
        self.last_decision = None

    async def resume_human_review(self, *, estimation_id, decision):
        self.last_decision = decision
        raise RuntimeError("stop-after-authority-capture")


def _headers(subject: str, tenant: str) -> dict[str, str]:
    token = SignedSessionCodec(_SIGNING_KEY.encode()).issue(
        subject=subject,
        tenant_id=tenant,
        roles=("member",),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    return {"Authorization": f"Bearer {token}"}


def _service(monkeypatch):
    import app.estimator.production_app as production_module

    fake = _CaptureService()

    @asynccontextmanager
    async def fake_runtime():
        yield fake

    monkeypatch.setattr(
        production_module,
        "open_unified_graph_estimation_service",
        fake_runtime,
    )
    monkeypatch.setattr(production_module, "flush_logfire_graph_traces", lambda: True)
    monkeypatch.setenv("ESTIMATOR_ALLOW_IN_MEMORY_OWNERSHIP", "true")
    monkeypatch.setenv("ESTIMATOR_SESSION_SIGNING_KEY", _SIGNING_KEY)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "configured-test-provider")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    return production_module.create_production_app(), fake


def _resume_payload() -> dict[str, object]:
    return {
        "action": "approve",
        "expected_revision": 1,
        "actor": "client-controlled-actor",
        "idempotency_key": "review-test-001",
    }


def test_estimator_business_api_requires_signed_identity(monkeypatch) -> None:
    app, _ = _service(monkeypatch)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/estimate/graph/unified/readiness").status_code == 401
        assert client.get(
            "/api/v1/estimate/graph/unified/readiness",
            headers=_headers("alice", "tenant-a"),
        ).status_code == 200


def test_cross_tenant_estimation_resume_fails_before_graph_access(monkeypatch) -> None:
    app, fake = _service(monkeypatch)
    estimation_id = str(uuid4())
    with TestClient(app) as client:
        app.state.estimator_ownership_store.claim(estimation_id, "tenant-a:alice")
        denied = client.post(
            f"/api/v1/estimate/graph/unified/{estimation_id}/resume",
            headers=_headers("bob", "tenant-b"),
            json=_resume_payload(),
        )
    assert denied.status_code == 403
    assert denied.json()["detail"]["reason_code"] == "tenant_mismatch"
    assert fake.last_decision is None


def test_human_resume_actor_is_server_owned(monkeypatch) -> None:
    app, fake = _service(monkeypatch)
    estimation_id = str(uuid4())
    with TestClient(app) as client:
        app.state.estimator_ownership_store.claim(estimation_id, "tenant-a:alice")
        response = client.post(
            f"/api/v1/estimate/graph/unified/{estimation_id}/resume",
            headers=_headers("alice", "tenant-a"),
            json=_resume_payload(),
        )
    assert response.status_code == 502
    assert fake.last_decision is not None
    assert fake.last_decision.actor == "tenant-a:alice"
