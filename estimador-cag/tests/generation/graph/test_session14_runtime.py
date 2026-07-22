from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

import app.generation.graph.session14_runtime as runtime_module
from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.observability import NoopGraphTracer
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
    open_session14_graph_estimation_service,
)
from app.routers.graph_estimations import router
from app.services.graph_estimation import GraphEstimationService

ESTIMATION_ID = UUID("f5317c82-05ad-4df5-bf43-f9b286f70e82")
TRANSCRIPT = (
    "The client needs JWT authentication and auditable "
    "logging for sensitive operations."
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
                        "budget_id": f"BUD-{index}",
                        "reference_component_id": f"AUTH-{index}",
                        "source_document_id": f"DOC-{index}",
                        "source_chunk_id": f"CH-{index}",
                        "recorded_hours": hours,
                        "distance": 0.1,
                        "score": 0.9,
                        "retrieval_method": "hybrid",
                    }
                    for index, hours in enumerate(
                        (32.0, 40.0, 48.0),
                        start=1,
                    )
                ]
            }
        ),
        search_k=5,
    )


def _service() -> GraphEstimationService:
    graph = build_session14_estimation_graph(
        _dependencies(),
        human_review_gate=runtime_module._session14_human_review_gate,
        checkpointer=InMemorySaver(),
    )
    return GraphEstimationService(
        graph=graph,
        graph_version=SESSION14_GRAPH_VERSION,
        graph_name=SESSION14_GRAPH_NAME,
        state_factory=new_session14_estimation_graph_state,
    )


@pytest.mark.asyncio
async def test_session14_runtime_wires_graph_service_and_checkpointer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkpointer = object()
    dependencies = object()
    graph = object()
    tracer = NoopGraphTracer()
    events: list[object] = []

    @asynccontextmanager
    async def fake_open_checkpointer(
        database_url: str | None = None,
    ):
        events.append(("checkpointer_enter", database_url))
        try:
            yield checkpointer
        finally:
            events.append(("checkpointer_exit", database_url))

    def fake_build_dependencies():
        events.append("dependencies")
        return dependencies

    def fake_build_graph(
        received_dependencies: object,
        *,
        human_review_gate: object,
        checkpointer: object,
        confidence_threshold: float,
    ):
        events.append(
            (
                "graph",
                received_dependencies,
                human_review_gate,
                checkpointer,
                confidence_threshold,
            )
        )
        return graph

    monkeypatch.setattr(
        runtime_module,
        "open_postgres_checkpointer",
        fake_open_checkpointer,
    )
    monkeypatch.setattr(
        runtime_module,
        "build_graph_node_dependencies",
        fake_build_dependencies,
    )
    monkeypatch.setattr(
        runtime_module,
        "build_session14_estimation_graph",
        fake_build_graph,
    )

    async with open_session14_graph_estimation_service(
        "postgresql://test",
        tracer=tracer,
    ) as service:
        assert service.graph is graph
        assert service.tracer is tracer
        assert service.graph_version == SESSION14_GRAPH_VERSION
        assert service.graph_name == SESSION14_GRAPH_NAME
        assert (
            service.state_factory
            is new_session14_estimation_graph_state
        )
        assert events == [
            ("checkpointer_enter", "postgresql://test"),
            "dependencies",
            (
                "graph",
                dependencies,
                runtime_module._session14_human_review_gate,
                checkpointer,
                runtime_module.settings.session14_confidence_threshold,
            ),
        ]

    assert events[-1] == (
        "checkpointer_exit",
        "postgresql://test",
    )


def test_existing_graph_endpoint_runs_session14_and_exposes_routes() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.graph_estimation_service = _service()
    client = TestClient(app)

    first = client.post(
        "/api/v1/estimate/graph",
        json={
            "transcript": TRANSCRIPT,
            "estimation_id": str(ESTIMATION_ID),
        },
    )
    second = client.post(
        "/api/v1/estimate/graph",
        json={
            "transcript": TRANSCRIPT,
            "estimation_id": str(ESTIMATION_ID),
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()

    payload = first.json()
    assert payload["graph_version"] == SESSION14_GRAPH_VERSION
    assert payload["status"] == "validated"
    assert payload["estimate"]["total_hours"] == 40.0
    assert [
        event["reason_code"] for event in payload["route_events"]
    ] == [
        "missing_requirements",
        "missing_budget_evidence",
        "missing_estimate",
        "missing_validation",
        "work_complete",
    ]
    assert [
        contribution["agent_id"]
        for contribution in payload["agent_contributions"]
    ] == [
        "requirements_extractor",
        "budget_searcher",
        "estimate_generator",
        "coherence_validator",
    ]
    assert "transcript" not in payload
