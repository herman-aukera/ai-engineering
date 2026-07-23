from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routers import sessions as sessions_router
from app.services.graph_estimation import GraphEstimationRun
from app.services.sessions import global_session_store

VALID_TRANSCRIPT = (
    "Project Atlas needs a FastAPI and PostgreSQL onboarding service with "
    "authentication, reporting, and email notifications."
)


def setup_function() -> None:
    global_session_store.reset()


def _graph_run() -> GraphEstimationRun:
    return GraphEstimationRun(
        estimation_id="12345678-1234-5678-1234-567812345678",
        thread_id="estimate:12345678-1234-5678-1234-567812345678",
        state={
            "graph_version": "session13.v1",
            "status": "validated",
            "review_required": False,
            "requirements": [],
            "components": [],
            "budget_matches": [],
            "component_estimates": [],
            "estimate": {
                "components": [],
                "subtotal_hours": 0.0,
                "contingency_hours": 0.0,
                "total_hours": 0.0,
                "total_cost_eur": 0.0,
                "currency": "EUR",
            },
            "errors": [],
            "trace_events": [],
            "provider_metadata": {},
            "execution_metadata": {"graph_version": "session13.v1"},
        },
    )


class RecordingGraphService:
    def __init__(self) -> None:
        self.transcripts: list[str] = []

    async def estimate(self, *, transcript: str, estimation_id=None) -> GraphEstimationRun:
        self.transcripts.append(transcript)
        return _graph_run()


class FailingGraphService:
    async def estimate(self, *, transcript: str, estimation_id=None) -> GraphEstimationRun:
        raise ValueError("graph exploded")


def _create_session(client: TestClient) -> str:
    response = client.post("/sessions")
    assert response.status_code == 200
    return response.json()["session_id"]


def test_graph_backend_routes_only_session_product_path(monkeypatch) -> None:
    graph_service = RecordingGraphService()
    legacy_calls = 0

    def unexpected_legacy_call(request, **kwargs):
        nonlocal legacy_calls
        legacy_calls += 1
        raise AssertionError("legacy estimator must not run in graph mode")

    monkeypatch.setattr(settings, "estimation_backend", "graph")
    monkeypatch.setattr(settings, "stress_fake_provider", False)
    monkeypatch.setattr(app.state, "graph_estimation_service", graph_service, raising=False)
    monkeypatch.setattr(sessions_router, "estimate_product", unexpected_legacy_call)

    client = TestClient(app)
    session_id = _create_session(client)
    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": VALID_TRANSCRIPT, "prompt_version": "v2"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert legacy_calls == 0
    assert graph_service.transcripts == [VALID_TRANSCRIPT]
    assert payload["estimation_backend"] == "graph"
    assert payload["result"] is None
    assert payload["compatibility"]["parity"] == "partial"
    assert payload["graph_estimation"]["thread_id"].startswith("estimate:")
    assert payload["session_id"] == session_id
    assert payload["history_turns"] == 1


def test_graph_backend_unavailable_returns_503_without_legacy_fallback(monkeypatch) -> None:
    legacy_calls = 0

    def unexpected_legacy_call(request, **kwargs):
        nonlocal legacy_calls
        legacy_calls += 1
        return {"text": "unexpected"}

    monkeypatch.setattr(settings, "estimation_backend", "graph")
    monkeypatch.setattr(settings, "stress_fake_provider", False)
    monkeypatch.setattr(app.state, "graph_estimation_service", None, raising=False)
    monkeypatch.setattr(sessions_router, "estimate_product", unexpected_legacy_call)

    client = TestClient(app)
    session_id = _create_session(client)
    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": VALID_TRANSCRIPT},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Estimation graph service is not available."
    assert legacy_calls == 0
    diagnostics = client.get(f"/sessions/{session_id}").json()
    assert diagnostics["total_turn_count"] == 0


def test_graph_backend_failure_returns_502(monkeypatch) -> None:
    monkeypatch.setattr(settings, "estimation_backend", "graph")
    monkeypatch.setattr(settings, "stress_fake_provider", False)
    monkeypatch.setattr(
        app.state,
        "graph_estimation_service",
        FailingGraphService(),
        raising=False,
    )

    client = TestClient(app)
    session_id = _create_session(client)
    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": VALID_TRANSCRIPT},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Graph estimation execution failed."


def test_configuration_only_rollback_keeps_legacy_path_available(monkeypatch) -> None:
    calls = 0

    def legacy_estimator(request, **kwargs):
        nonlocal calls
        calls += 1
        return {
            "prompt_version": kwargs["prompt_version"],
            "text": "legacy estimate",
            "requested_tier": kwargs.get("tier") or "flash",
            "served_tier": kwargs.get("tier") or "flash",
            "fallback_used": False,
        }

    monkeypatch.setattr(settings, "estimation_backend", "legacy")
    monkeypatch.setattr(settings, "stress_fake_provider", False)
    monkeypatch.setattr(app.state, "graph_estimation_service", None, raising=False)
    monkeypatch.setattr(sessions_router, "estimate_product", legacy_estimator)

    client = TestClient(app)
    session_id = _create_session(client)
    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": VALID_TRANSCRIPT},
    )

    assert response.status_code == 200
    assert calls == 1
    assert response.json()["estimation_backend"] == "legacy"
    assert response.json()["text"] == "legacy estimate"


def test_stress_fake_override_precedes_configured_graph_backend(monkeypatch) -> None:
    monkeypatch.setattr(settings, "estimation_backend", "graph")
    monkeypatch.setattr(settings, "stress_fake_provider", True)
    monkeypatch.setattr(app.state, "graph_estimation_service", None, raising=False)

    client = TestClient(app)
    session_id = _create_session(client)
    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": VALID_TRANSCRIPT},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["estimation_backend"] == "stress_fake"
    assert payload["provider"] == "deterministic-local"
