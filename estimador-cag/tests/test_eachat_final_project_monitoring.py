from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.energy_chat.identity import SignedSessionCodec
from app.energy_chat.monitoring import EnergyChatMonitoringWindow
from app.energy_chat.production_app import create_production_app

_SIGNING_KEY = "eachat-monitoring-test-signing-key-32-bytes-minimum"


def test_monitoring_window_reports_latency_cost_error_and_disposition_aggregates() -> None:
    window = EnergyChatMonitoringWindow(max_samples=10)
    window.record_success(
        wall_latency_ms=100,
        provider_call_count=1,
        provider_cost_usd=0.01,
        disposition="accept",
    )
    window.record_success(
        wall_latency_ms=300,
        provider_call_count=2,
        provider_cost_usd=0.03,
        disposition="clarify",
    )
    window.record_error(wall_latency_ms=200)

    snapshot = window.snapshot()

    assert snapshot.request_count == 3
    assert snapshot.successful_request_count == 2
    assert snapshot.error_count == 1
    assert snapshot.error_rate == 1 / 3
    assert snapshot.mean_latency_ms == 200.0
    assert snapshot.p95_latency_ms == 300
    assert snapshot.mean_provider_cost_usd == (0.04 / 3)
    assert snapshot.provider_call_count == 3
    assert snapshot.disposition_counts == {"accept": 1, "clarify": 1}


def test_production_monitoring_is_authenticated_and_observes_chat(monkeypatch) -> None:
    monkeypatch.setenv("LANGGRAPH_STRICT_MSGPACK", "true")
    monkeypatch.setenv("EACHAT_ALLOW_IN_MEMORY", "true")
    monkeypatch.setenv("EACHAT_SESSION_SIGNING_KEY", _SIGNING_KEY)
    monkeypatch.delenv("EACHAT_POSTGRES_URL", raising=False)
    monkeypatch.delenv("EACHAT_MEMORY_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("EACHAT_SUPPORT_RAG_ENABLED", raising=False)

    token = SignedSessionCodec(_SIGNING_KEY.encode()).issue(
        subject="reviewer",
        tenant_id="final-project",
        roles=("member",),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(create_production_app()) as client:
        assert client.get("/energy-chat/v2/monitoring").status_code == 401
        response = client.post(
            "/energy-chat/v2/chat",
            headers=headers,
            json={"user_message": "Explain the safest release-validation step."},
        )
        metrics = client.get("/energy-chat/v2/monitoring", headers=headers)
        dashboard = client.get("/energy-chat/v2/monitoring/dashboard", headers=headers)

    assert response.status_code == 200
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["request_count"] >= 1
    assert payload["successful_request_count"] >= 1
    assert payload["mean_latency_ms"] >= 0
    assert payload["p95_latency_ms"] >= 0
    assert payload["mean_provider_cost_usd"] >= 0
    assert payload["provider_call_count"] >= 0
    assert payload["disposition_counts"]
    assert dashboard.status_code == 200
    assert "EACHAT Final Project Monitoring" in dashboard.text
    assert "Prompts, answers, credentials" in dashboard.text
