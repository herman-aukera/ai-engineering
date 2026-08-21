from __future__ import annotations

from fastapi.testclient import TestClient

from app.eacode.production_app import create_production_app


def test_eacode_keyless_v1_control_plane_smoke(monkeypatch) -> None:
    monkeypatch.setenv("GIT_SHA", "eacode-smoke")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_API_KEY", raising=False)

    with TestClient(create_production_app()) as client:
        startup = client.get("/startup")
        health = client.get("/health")
        ready = client.get("/ready")
        version = client.get("/version")
        status = client.get("/api/v1/eacode/status")
        capabilities = client.get("/api/v1/eacode/capabilities")
        selection = client.post("/api/v1/eacode/select", json={})

    assert startup.json() == {"status": "started", "started": True}
    assert health.json() == {"status": "ok", "service": "eacode"}
    assert ready.json() == {
        "status": "ready",
        "ready": True,
        "control_plane": "deterministic",
    }
    assert version.json()["git_sha"] == "eacode-smoke"
    assert status.status_code == 200
    assert status.json()["provider_selection"] == "planned_only"
    assert capabilities.status_code == 200
    assert capabilities.json()["count"] > 0
    assert selection.status_code == 200
    assert selection.json()["status"] == "ok"
    assert selection.json()["served"] is None
    assert "not proof" in selection.json()["claim_boundary"]
    assert status.headers["cache-control"] == "no-store"
    assert health.headers["x-content-type-options"] == "nosniff"


def test_eacode_production_app_does_not_mount_legacy_unversioned_surface() -> None:
    paths = {getattr(route, "path", "") for route in create_production_app().routes}

    assert "/api/v1/eacode/status" in paths
    assert "/eacode/status" not in paths
    assert all(
        not path.startswith("/api/") or path.startswith("/api/v1/")
        for path in paths
    )
