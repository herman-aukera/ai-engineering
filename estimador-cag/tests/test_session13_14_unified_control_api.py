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

ESTIMATION_ID = UUID("46cc93ea-f9c7-48cf-aefb-332076633d33")


def _control_run() -> GraphEstimationRun:
    state = new_unified_estimation_graph_state(
        transcript="SOURCE BODY MUST NOT RETURN",
        estimation_id=str(ESTIMATION_ID),
    )
    state.update(
        status="needs_review",
        review_required=True,
        unified_phase="human_review",
        human_review_status="awaiting_human_review",
        human_review_revision=1,
        human_review_reason_codes=["confidence_below_threshold"],
        unified_route_events=[
            {
                "event_id": "route-1",
                "sequence": 1,
                "destination": "human_review_gate",
                "reason_code": "human_authority_required",
                "summary": "Human authority is required.",
            }
        ],
        critic_report={"verdict": "human_required", "issues": []},
        boss_decision={"action": "human_review"},
        reliability_report={"overall_score": 0.5},
        plus_competition_candidates=[],
        plus_competition_assessment={},
        plus_authorized_capabilities={"proposal": "cap:test"},
        plus_context_detail="medium",
        plus_context_source_revision=4,
        plus_compacted_context={
            "context_id": "context:test",
            "fingerprint": "a" * 64,
            "evidence_refs": [],
        },
        proposal={},
    )
    return GraphEstimationRun(
        estimation_id=str(ESTIMATION_ID),
        thread_id=f"estimate:{ESTIMATION_ID}",
        state=state,
        execution_status="awaiting_human_review",
    )


class FakeControlService:
    def __init__(self) -> None:
        self.resume_action: str | None = None

    async def estimate(self, *, transcript: str, estimation_id=None):
        return deepcopy(_control_run())

    async def resume_human_review(self, *, estimation_id, decision):
        self.resume_action = decision.action
        paused = deepcopy(_control_run())
        resumed_state = deepcopy(paused.state)
        resumed_state.update(
            human_review_status="approved",
            human_review_revision=2,
            unified_phase="finalized",
            status="validated",
            review_required=False,
        )
        return GraphEstimationRun(
            estimation_id=paused.estimation_id,
            thread_id=paused.thread_id,
            state=resumed_state,
            execution_status="completed",
        )


def _client(service: FakeControlService) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.unified_graph_estimation_service = service
    app.state.unified_graph_runtime_error = None
    return TestClient(app)


def test_control_start_returns_allowlisted_projection() -> None:
    response = _client(FakeControlService()).post(
        "/api/v1/estimate/graph/unified/control",
        json={"transcript": "SOURCE BODY MUST NOT RETURN"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_status"] == "awaiting_human_review"
    assert payload["route_events"][0]["destination"] == "human_review_gate"
    assert payload["authorized_capabilities"] == {"proposal": "cap:test"}
    assert "SOURCE BODY MUST NOT RETURN" not in response.text
    assert "transcript" not in response.text.lower()


def test_control_resume_returns_refreshed_projection() -> None:
    service = FakeControlService()
    response = _client(service).post(
        f"/api/v1/estimate/graph/unified/control/{ESTIMATION_ID}/resume",
        json={
            "action": "approve",
            "expected_revision": 1,
            "actor": "control-reviewer",
            "reason": None,
            "adjustments": None,
            "idempotency_key": "control-approval-001",
        },
    )

    assert response.status_code == 200
    assert service.resume_action == "approve"
    payload = response.json()
    assert payload["execution_status"] == "completed"
    assert payload["human_review_status"] == "approved"
    assert payload["human_review_revision"] == 2
