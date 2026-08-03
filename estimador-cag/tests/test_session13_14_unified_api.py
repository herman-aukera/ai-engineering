from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.generation.graph.unified_state import (
    new_unified_estimation_graph_state,
)
from app.routers.unified_graph_estimations import router
from app.services.graph_estimation import GraphEstimationRun

ESTIMATION_ID = UUID("63555908-01bf-4ced-af80-16c2a6c8b23d")
TRANSCRIPT = "Build an auditable reporting API with human approval."


def _run() -> GraphEstimationRun:
    state = new_unified_estimation_graph_state(
        transcript=TRANSCRIPT,
        estimation_id=str(ESTIMATION_ID),
    )
    component = {
        "component_id": "CMP-001",
        "name": "Reporting API",
        "hours": 40.0,
        "grounding_status": "grounded",
        "reference_budget_ids": ["BUD-001"],
        "reference_component_ids": ["REF-001"],
        "source_hours": [40.0],
        "source_range_low": 40.0,
        "source_range_high": 40.0,
        "dispersion": 0.0,
        "confidence": 0.9,
        "derivation_method": "median_recorded_hours",
        "review_reasons": [],
    }
    state.update(
        requirements=[{"requirement_id": "REQ-001", "text": "Reporting API."}],
        components=[
            {
                "component_id": "CMP-001",
                "name": "Reporting API",
                "category": "backend",
                "requirement_ids": ["REQ-001"],
            }
        ],
        component_estimates=[component],
        estimate={
            "components": [component],
            "subtotal_hours": 40.0,
            "contingency_hours": 0.0,
            "total_hours": 40.0,
            "total_cost_eur": None,
            "currency": "EUR",
        },
        status="validated",
        review_required=False,
        human_review_status="approved",
        human_review_revision=2,
        unified_phase="finalized",
    )
    return GraphEstimationRun(
        estimation_id=str(ESTIMATION_ID),
        thread_id=f"estimate:{ESTIMATION_ID}",
        state=state,
    )


class FakeUnifiedService:
    def __init__(self) -> None:
        self.estimate_calls: list[dict[str, object]] = []
        self.resume_calls: list[dict[str, object]] = []

    async def estimate(self, *, transcript: str, estimation_id=None):
        self.estimate_calls.append(
            {"transcript": transcript, "estimation_id": estimation_id}
        )
        return deepcopy(_run())

    async def resume_human_review(self, *, estimation_id, decision):
        self.resume_calls.append(
            {
                "estimation_id": estimation_id,
                "action": decision.action,
                "expected_revision": decision.expected_revision,
                "idempotency_key": decision.idempotency_key,
            }
        )
        return deepcopy(_run())


def _app(service: object | None = None, *, error: str | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.unified_graph_estimation_service = service
    app.state.unified_graph_runtime_error = error
    return app


def test_unified_create_endpoint_is_additive_and_structured() -> None:
    service = FakeUnifiedService()
    response = TestClient(_app(service)).post(
        "/api/v1/estimate/graph/unified",
        json={
            "transcript": TRANSCRIPT,
            "estimation_id": str(ESTIMATION_ID),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["graph_version"] == "session13_14_plus.unified.v1"
    assert payload["status"] == "validated"
    assert payload["thread_id"] == f"estimate:{ESTIMATION_ID}"
    assert "transcript" not in payload
    assert service.estimate_calls == [
        {"transcript": TRANSCRIPT, "estimation_id": ESTIMATION_ID}
    ]


def test_unified_resume_delegates_same_thread_decision_contract() -> None:
    service = FakeUnifiedService()
    response = TestClient(_app(service)).post(
        f"/api/v1/estimate/graph/unified/{ESTIMATION_ID}/resume",
        json={
            "action": "approve",
            "expected_revision": 1,
            "actor": "api-reviewer",
            "idempotency_key": "unified-approval-001",
        },
    )

    assert response.status_code == 200
    assert service.resume_calls == [
        {
            "estimation_id": ESTIMATION_ID,
            "action": "approve",
            "expected_revision": 1,
            "idempotency_key": "unified-approval-001",
        }
    ]


def test_unified_endpoint_fails_closed_without_runtime() -> None:
    response = TestClient(_app()).post(
        "/api/v1/estimate/graph/unified",
        json={"transcript": TRANSCRIPT},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Unified estimation graph service is not available."
    }


def test_unified_readiness_is_sanitized_and_preserves_rollbacks() -> None:
    response = TestClient(_app(error="RuntimeError")).get(
        "/api/v1/estimate/graph/unified/readiness"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert payload["runtime_error"] == "RuntimeError"
    assert payload["rollback_paths"] == [
        "/api/v1/estimate/graph",
        "/api/v1/estimate/graph/reviewed/start",
    ]


def test_main_registers_unified_and_legacy_paths() -> None:
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/api/v1/estimate/graph/unified" in paths
    assert "/api/v1/estimate/graph" in paths
    assert "/api/v1/estimate/graph/reviewed/start" in paths
