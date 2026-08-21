from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient


def _configure_keyless_test_runtime(monkeypatch, production_module) -> None:
    @asynccontextmanager
    async def deterministic_runtime():
        yield object()

    monkeypatch.setattr(
        production_module,
        "open_unified_graph_estimation_service",
        deterministic_runtime,
    )
    monkeypatch.setattr(production_module, "flush_logfire_graph_traces", lambda: True)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "session15-smoke-provider")
    monkeypatch.setenv("KIMI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("GIT_SHA", "session15-smoke")
    monkeypatch.setenv("ESTIMATOR_ALLOW_IN_MEMORY_OWNERSHIP", "true")
    monkeypatch.setenv(
        "ESTIMATOR_SESSION_SIGNING_KEY",
        "estimator-smoke-signing-key-32-bytes-minimum",
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_production_http_shell_starts_without_model_calls(monkeypatch) -> None:
    import app.estimator.production_app as production_module

    _configure_keyless_test_runtime(monkeypatch, production_module)

    with TestClient(production_module.create_production_app()) as client:
        startup = client.get("/startup")
        health = client.get("/health")
        ready = client.get("/ready")
        version = client.get("/version")

    assert startup.status_code == 200
    assert startup.json() == {"status": "started", "started": True}
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "estimator"}
    assert ready.status_code == 200
    assert ready.json()["ready"] is True
    assert ready.json()["unified_runtime"] is True
    assert ready.json()["configured_providers"] == ["deepseek"]
    assert ready.json()["authority_store_available"] is True
    assert version.status_code == 200
    assert version.json()["git_sha"] == "session15-smoke"
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert health.headers["referrer-policy"] == "no-referrer"


def test_readiness_fails_closed_when_authority_store_is_unavailable(monkeypatch) -> None:
    import app.estimator.production_app as production_module

    _configure_keyless_test_runtime(monkeypatch, production_module)
    monkeypatch.setattr(
        production_module.InMemoryEstimationOwnershipStore,
        "ping",
        lambda self: False,
        raising=False,
    )

    with TestClient(production_module.create_production_app()) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert ready.status_code == 503
    assert ready.json()["ready"] is False
    assert ready.json()["authority_store_available"] is False


def test_public_production_api_is_canonical_v1_only() -> None:
    from app.estimator.production_app import create_production_app

    paths = set(create_production_app().openapi().get("paths", {}))

    assert paths
    assert all(path.startswith("/api/v1/estimate/graph/unified") for path in paths)
