from __future__ import annotations

from copy import deepcopy
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.generation.graph.state import new_estimation_graph_state
from app.routers.graph_estimations import router
from app.services.graph_estimation import GraphEstimationRun

ESTIMATION_ID = UUID(
    "f5317c82-05ad-4df5-bf43-f9b286f70e82"
)
TRANSCRIPT = (
    "The client needs JWT authentication and auditable "
    "logging for sensitive operations."
)


def _run() -> GraphEstimationRun:
    state = new_estimation_graph_state(
        transcript=TRANSCRIPT,
        estimation_id=str(ESTIMATION_ID),
    )
    state.update(
        {
            "requirements": [
                {
                    "requirement_id": "REQ-001",
                    "text": "Users authenticate with JWT.",
                }
            ],
            "components": [
                {
                    "component_id": "CMP-001",
                    "name": "JWT authentication",
                    "category": "backend",
                    "requirement_ids": ["REQ-001"],
                }
            ],
            "budget_matches": [
                {
                    "component_id": "CMP-001",
                    "budget_id": "BUD-101",
                    "reference_component_id": "AUTH-01",
                    "source_document_id": "DOC-10",
                    "source_chunk_id": "CH-101",
                    "recorded_hours": 40.0,
                    "distance": 0.1,
                    "score": 0.9,
                    "retrieval_method": "hybrid",
                }
            ],
            "component_estimates": [
                {
                    "component_id": "CMP-001",
                    "name": "JWT authentication",
                    "hours": 40.0,
                    "grounding_status": "grounded",
                    "reference_budget_ids": ["BUD-101"],
                    "reference_component_ids": ["AUTH-01"],
                    "source_hours": [40.0],
                    "source_range_low": 40.0,
                    "source_range_high": 40.0,
                    "dispersion": 0.0,
                    "confidence": 0.5,
                    "derivation_method": "median_recorded_hours",
                    "review_reasons": [],
                }
            ],
            "estimate": {
                "components": [
                    {
                        "component_id": "CMP-001",
                        "name": "JWT authentication",
                        "hours": 40.0,
                        "grounding_status": "grounded",
                        "reference_budget_ids": ["BUD-101"],
                        "reference_component_ids": ["AUTH-01"],
                        "source_hours": [40.0],
                        "source_range_low": 40.0,
                        "source_range_high": 40.0,
                        "dispersion": 0.0,
                        "confidence": 0.5,
                        "derivation_method": "median_recorded_hours",
                        "review_reasons": [],
                    }
                ],
                "subtotal_hours": 40.0,
                "contingency_hours": 0.0,
                "total_hours": 40.0,
                "total_cost_eur": None,
                "currency": "EUR",
            },
            "status": "validated",
            "review_required": False,
            "trace_events": [
                {
                    "event_type": "estimate_validated",
                    "node": "validate_and_consolidate",
                    "summary": "Validated one component estimate.",
                    "evidence_refs": ["CMP-001", "BUD-101"],
                    "state_delta_keys": [
                        "estimate",
                        "status",
                    ],
                }
            ],
            "execution_metadata": {
                "requirement_count": 1,
                "component_count": 1,
                "budget_match_count": 1,
                "component_estimate_count": 1,
            },
        }
    )

    return GraphEstimationRun(
        estimation_id=str(ESTIMATION_ID),
        thread_id=(
            "estimate:"
            "f5317c82-05ad-4df5-bf43-f9b286f70e82"
        ),
        state=state,
    )


class FakeService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def estimate(
        self,
        *,
        transcript: str,
        estimation_id: UUID | None = None,
    ) -> GraphEstimationRun:
        self.calls.append(
            {
                "transcript": transcript,
                "estimation_id": estimation_id,
            }
        )
        return deepcopy(_run())


class FailingService:
    async def estimate(
        self,
        *,
        transcript: str,
        estimation_id: UUID | None = None,
    ) -> GraphEstimationRun:
        del transcript, estimation_id
        raise RuntimeError("provider unavailable")


def _app(service: object | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    if service is not None:
        app.state.graph_estimation_service = service

    return app


def test_graph_endpoint_returns_structured_evidence_without_transcript() -> None:
    service = FakeService()
    client = TestClient(_app(service))

    response = client.post(
        "/api/v1/estimate/graph",
        json={
            "transcript": TRANSCRIPT,
            "estimation_id": str(ESTIMATION_ID),
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["estimation_id"] == str(ESTIMATION_ID)
    assert payload["thread_id"] == (
        "estimate:"
        "f5317c82-05ad-4df5-bf43-f9b286f70e82"
    )
    assert payload["graph_version"] == "session13.v1"
    assert payload["status"] == "validated"
    assert payload["review_required"] is False
    assert payload["estimate"]["total_hours"] == 40.0
    assert payload["errors"] == []
    assert "transcript" not in payload

    assert service.calls == [
        {
            "transcript": TRANSCRIPT,
            "estimation_id": ESTIMATION_ID,
        }
    ]


def test_graph_endpoint_returns_503_until_service_is_configured() -> None:
    client = TestClient(_app())

    response = client.post(
        "/api/v1/estimate/graph",
        json={"transcript": TRANSCRIPT},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Estimation graph service is not available."
    }


def test_graph_endpoint_maps_execution_failure_to_502() -> None:
    client = TestClient(_app(FailingService()))

    response = client.post(
        "/api/v1/estimate/graph",
        json={"transcript": TRANSCRIPT},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Failed to produce a graph estimate."
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"transcript": "short"},
        {
            "transcript": TRANSCRIPT,
            "unexpected": True,
        },
    ],
)
def test_graph_endpoint_rejects_invalid_requests(
    payload: dict[str, object],
) -> None:
    client = TestClient(_app(FakeService()))

    response = client.post(
        "/api/v1/estimate/graph",
        json=payload,
    )

    assert response.status_code == 422


def test_existing_estimation_routes_remain_registered() -> None:
    from app.main import app

    paths = {
        route.path
        for route in app.routes
    }

    assert "/api/v1/estimate" in paths
    assert "/api/v1/estimate/stream" in paths
    assert "/api/v1/estimate/graph" in paths
