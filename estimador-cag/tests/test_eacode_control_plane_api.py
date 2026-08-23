"""HTTP contract tests for the EACODE control plane."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_eacode_status_reports_claim_boundary() -> None:
    response = client.get("/eacode/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["sdd_layer"] is True
    assert payload["critic_boss_layer"] is True
    assert payload["provider_selection"] == "planned_only"
    assert payload["live_process_execution_enabled"] is False
    assert payload["final_authority"] == "deterministic_boss"


def test_eacode_capabilities_use_verified_sources() -> None:
    response = client.get("/eacode/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] > 0
    models = {model["model_id"]: model for model in payload["models"]}
    assert models["deepseek-v4-pro"]["source_version"] == "2026-07-22"
    assert models["k3"]["surface"] == "kimi_code"
    assert models["k3"]["entitlement_state"] == "membership_required"


def test_eacode_select_separates_requested_planned_and_served() -> None:
    response = client.post(
        "/eacode/select",
        json={
            "provider": "kimi",
            "profile": "max",
            "context_profile": "max",
            "max_cost_usd": 1,
            "entitled_surfaces": ["kimi_code"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["requested"]["provider"] == "kimi"
    assert payload["planned"]["model_id"] == "k3"
    assert payload["served"] is None
    assert "not proof" in payload["claim_boundary"]


def test_eacode_unentitled_kimi_code_route_fails_closed() -> None:
    response = client.post(
        "/eacode/select",
        json={
            "provider": "kimi",
            "profile": "max",
            "context_profile": "max",
            "max_cost_usd": 1,
        },
    )
    assert response.status_code == 422
    assert "Entitlement required" in response.json()["detail"]


def test_eacode_premium_route_fails_closed_without_reason() -> None:
    response = client.post(
        "/eacode/select",
        json={
            "provider": "openai",
            "profile": "max",
            "context_profile": "max",
            "max_cost_usd": 5,
        },
    )
    assert response.status_code == 422


def test_eacode_selector_ui_is_same_origin_and_mount_safe() -> None:
    response = client.get("/eacode/ui")
    assert response.status_code == 200
    assert "EACODE" in response.text
    assert "fetch('./select'" in response.text
    assert "fetch('./gateway/proposals'" in response.text
    assert "fetch(`./demo/${state.proposalId}/authorize`" in response.text
    assert "fetch(`/eacode/" not in response.text
    assert "fetch('/eacode/" not in response.text
    assert "Planning only. This section does not call a provider." in response.text
    assert "Kimi Code membership confirmed" in response.text
    assert "Coding tools propose; EACODE governs." in response.text
