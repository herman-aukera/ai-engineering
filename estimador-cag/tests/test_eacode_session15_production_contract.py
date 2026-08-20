from fastapi.testclient import TestClient

from app.eacode.production_app import create_production_app
from app.main import app as coursework_app


def test_eacode_production_app_is_versioned_and_provider_keyless(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_API_KEY", raising=False)

    with TestClient(create_production_app()) as client:
        assert client.get("/startup").json() == {"status": "started", "started": True}
        assert client.get("/health").json() == {"status": "ok", "service": "eacode"}
        assert client.get("/ready").json() == {
            "status": "ready",
            "ready": True,
            "control_plane": "deterministic",
        }
        status = client.get("/api/v1/eacode/status")
        assert status.status_code == 200
        assert status.json()["control_plane"] == "deterministic"
        assert status.json()["served_provider_evidence"] == "requires_opt_in_live_call"
        assert client.get("/eacode/status").status_code == 404


def test_legacy_coursework_app_keeps_eacode_compatibility_route() -> None:
    paths = {getattr(route, "path", "") for route in coursework_app.routes}
    assert "/eacode/status" in paths


def test_eacode_selector_ui_uses_prefix_relative_api_call() -> None:
    with TestClient(create_production_app()) as client:
        response = client.get("/api/v1/eacode/ui")

    assert response.status_code == 200
    assert "fetch('./select'" in response.text
    assert "fetch('/eacode/select'" not in response.text
