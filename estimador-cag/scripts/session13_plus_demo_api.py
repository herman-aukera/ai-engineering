"""Keyless demo composition for the Session 13 Plus control room.

Run only for local demonstration:

    uv run uvicorn scripts.session13_plus_demo_api:app --port 8001

It uses the production reviewed router/service/graph with deterministic adapters
and an in-memory saver. It is not persistence evidence and is never a production
fallback.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.memory import InMemorySaver

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.reviewed_build import build_reviewed_estimation_graph
from app.routers.reviewed_graph_estimations import router
from app.services.reviewed_graph_estimation import ReviewedGraphEstimationService

REQUIREMENTS = [
    {"requirement_id": "req-auth", "text": "Authenticate users securely."},
    {"requirement_id": "req-audit", "text": "Keep an auditable event trail."},
]
COMPONENTS = [
    {
        "component_id": "cmp-auth",
        "name": "Authentication and audit trail",
        "category": "backend",
        "requirement_ids": ["req-auth", "req-audit"],
    }
]
MATCHES = {
    "cmp-auth": [
        {
            "component_id": "cmp-auth",
            "budget_id": f"BUD-{index}",
            "reference_component_id": f"AUTH-{index}",
            "source_document_id": f"DOC-{index}",
            "source_chunk_id": f"CH-{index}",
            "recorded_hours": hours,
            "distance": 0.1,
            "score": 0.9,
            "retrieval_method": "demo_fake",
        }
        for index, hours in enumerate((32.0, 40.0, 48.0), start=1)
    ]
}


def build_demo_service() -> ReviewedGraphEstimationService:
    dependencies = GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor(REQUIREMENTS),
        component_classifier=FakeComponentClassifier(COMPONENTS),
        budget_searcher=FakeBudgetSearcher(MATCHES),
    )
    graph = build_reviewed_estimation_graph(
        dependencies,
        checkpointer=InMemorySaver(),
        retrieval_mode="parallel",
        retrieval_max_concurrency=2,
    )
    return ReviewedGraphEstimationService(graph=graph)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.reviewed_graph_estimation_service = build_demo_service()
    yield
    app.state.reviewed_graph_estimation_service = None


app = FastAPI(title="Session 13 Plus deterministic demo API", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "runtime": "deterministic_demo"}
