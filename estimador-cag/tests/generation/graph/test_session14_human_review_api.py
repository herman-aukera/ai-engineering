from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.nodes.session14_human_review import (
    build_session14_human_review_gate,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.review_state import (
    new_session14_estimation_graph_state,
)
from app.generation.graph.session14_build import (
    SESSION14_GRAPH_NAME,
    build_session14_estimation_graph,
)
from app.generation.graph.session14_runtime import (
    SESSION14_GRAPH_VERSION,
)
from app.routers.graph_estimations import router
from app.services.graph_estimation import GraphEstimationService

ESTIMATION_ID = UUID("f5317c82-05ad-4df5-bf43-f9b286f70e82")
TRANSCRIPT = (
    "Build JWT authentication with auditable access control "
    "and a reviewer-visible estimation decision."
)


def _dependencies() -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor(
            [
                {
                    "requirement_id": "REQ-001",
                    "text": "Users authenticate with JWT.",
                }
            ]
        ),
        component_classifier=FakeComponentClassifier(
            [
                {
                    "component_id": "CMP-001",
                    "name": "JWT authentication",
                    "category": "backend",
                    "requirement_ids": ["REQ-001"],
                }
            ]
        ),
        budget_searcher=FakeBudgetSearcher(
            {
                "CMP-001": [
                    {
                        "component_id": "CMP-001",
                        "budget_id": "BUD-1",
                        "reference_component_id": "AUTH-1",
                        "source_document_id": "DOC-1",
                        "source_chunk_id": "CH-1",
                        "recorded_hours": 40.0,
                        "distance": 0.1,
                        "score": 0.9,
                        "retrieval_method": "hybrid",
                    }
                ]
            }
        ),
        search_k=5,
    )


def _client() -> TestClient:
    graph = build_session14_estimation_graph(
        _dependencies(),
        human_review_gate=build_session14_human_review_gate(),
        checkpointer=InMemorySaver(),
    )
    service = GraphEstimationService(
        graph=graph,
        graph_version=SESSION14_GRAPH_VERSION,
        graph_name=SESSION14_GRAPH_NAME,
        state_factory=new_session14_estimation_graph_state,
    )
    app = FastAPI()
    app.include_router(router)
    app.state.graph_estimation_service = service
    return TestClient(app)


def _start(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/estimate/graph",
        json={
            "transcript": TRANSCRIPT,
            "estimation_id": str(ESTIMATION_ID),
        },
    )
    assert response.status_code == 200
    return response.json()


def _resume(
    client: TestClient,
    payload: dict[str, object],
):
    return client.post(
        f"/api/v1/estimate/graph/{ESTIMATION_ID}/resume",
        json=payload,
    )


def test_low_confidence_pauses_and_approve_resumes_same_thread() -> None:
    client = _client()
    paused = _start(client)
    paused_replay = _start(client)

    assert paused["status"] == "awaiting_human_review"
    assert paused["review_required"] is True
    assert paused["revision"] == 1
    assert paused["human_review_status"] == "awaiting_human_review"
    assert paused["human_review_reason_codes"] == ["low_confidence"]
    assert paused["thread_id"] == f"estimate:{ESTIMATION_ID}"
    assert paused_replay == paused
    assert paused["human_review"]["value"]["allowed_actions"] == [
        "approve",
        "adjust",
        "reject",
    ]
    assert "transcript" not in str(paused["human_review"])

    decision = {
        "action": "approve",
        "expected_revision": 1,
        "actor": "reviewer@example.com",
        "idempotency_key": "approve-review-001",
    }
    first = _resume(client, decision)
    duplicate = _resume(client, decision)

    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert duplicate.json() == first.json()
    completed = first.json()
    assert completed["status"] == "validated"
    assert completed["thread_id"] == paused["thread_id"]
    assert completed["revision"] == 2
    assert completed["human_review_status"] == "approved"
    assert completed["human_review"] is None
    assert [
        event["event_type"] for event in completed["trace_events"][-2:]
    ] == [
        "session14_human_review_paused",
        "session14_human_review_approve",
    ]


def test_adjust_recalculates_and_conflicting_replay_returns_409() -> None:
    client = _client()
    paused = _start(client)
    decision = {
        "action": "adjust",
        "expected_revision": paused["revision"],
        "actor": "lead@example.com",
        "reason": "Use the signed discovery baseline.",
        "idempotency_key": "adjust-review-001",
        "adjustments": [
            {
                "component_id": "CMP-001",
                "hours": 52.0,
                "evidence_refs": ["HUMAN-NOTE-7"],
            }
        ],
    }

    completed = _resume(client, decision)
    assert completed.status_code == 200
    payload = completed.json()
    assert payload["status"] == "validated"
    assert payload["human_review_status"] == "adjusted"
    assert payload["estimate"]["total_hours"] == 52.0
    assert (
        payload["component_estimates"][0]["derivation_method"]
        == "human_adjustment"
    )

    conflicting = {**decision, "actor": "other@example.com"}
    response = _resume(client, conflicting)
    assert response.status_code == 409
    assert "idempotency key" in response.json()["detail"]


def test_reject_finishes_without_authorizing_the_estimate() -> None:
    client = _client()
    paused = _start(client)
    response = _resume(
        client,
        {
            "action": "reject",
            "expected_revision": paused["revision"],
            "actor": "reviewer@example.com",
            "reason": "The evidence is insufficient.",
            "idempotency_key": "reject-review-001",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_review"
    assert payload["review_required"] is True
    assert payload["human_review_status"] == "rejected"
    assert payload["thread_id"] == paused["thread_id"]


def test_stale_revision_is_rejected_without_resuming() -> None:
    client = _client()
    _start(client)
    response = _resume(
        client,
        {
            "action": "approve",
            "expected_revision": 2,
            "actor": "reviewer@example.com",
            "idempotency_key": "stale-review-001",
        },
    )

    assert response.status_code == 409
    assert "does not match" in response.json()["detail"]
