from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient


def test_production_http_shell_starts_without_model_calls(monkeypatch) -> None:
    import app.main as main_module

    @asynccontextmanager
    async def deterministic_runtime():
        yield object()

    monkeypatch.setattr(main_module, "open_graph_estimation_service", deterministic_runtime)
    monkeypatch.setattr(
        main_module,
        "open_reviewed_graph_estimation_service",
        deterministic_runtime,
    )
    monkeypatch.setattr(
        main_module,
        "open_unified_graph_estimation_service",
        deterministic_runtime,
    )
    monkeypatch.setattr(main_module, "flush_logfire_graph_traces", lambda: True)
    monkeypatch.setenv("GIT_SHA", "session15-smoke")

    with TestClient(main_module.app) as client:
        startup = client.get("/startup")
        health = client.get("/health")
        version = client.get("/version")

    assert startup.status_code == 200
    assert startup.json() == {"status": "started", "started": True}
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert version.status_code == 200
    assert version.json()["git_sha"] == "session15-smoke"
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert health.headers["referrer-policy"] == "no-referrer"


def test_public_api_major_version_is_v1() -> None:
    import app.main as main_module

    paths = set(main_module.app.openapi().get("paths", {}))
    versioned = sorted(path for path in paths if path.startswith("/api/"))

    assert versioned
    assert all(path.startswith("/api/v1/") for path in versioned)
