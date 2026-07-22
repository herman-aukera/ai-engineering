"""Real PostgreSQL pause-close-reopen-resume proof for Session 14."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

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
from app.generation.graph.runtime import open_postgres_checkpointer
from app.generation.graph.session14_build import (
    SESSION14_GRAPH_NAME,
    build_session14_estimation_graph,
)
from app.generation.graph.session14_runtime import (
    SESSION14_GRAPH_VERSION,
)
from app.schemas.session14_human_review import (
    Session14HumanReviewDecision,
)
from app.services.graph_estimation import GraphEstimationService

RUN_POSTGRES_INTEGRATION = (
    os.getenv("RUN_SESSION14_POSTGRES_INTEGRATION") == "1"
)
DATABASE_URL = os.getenv("SESSION14_POSTGRES_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not RUN_POSTGRES_INTEGRATION,
    reason=(
        "Set RUN_SESSION14_POSTGRES_INTEGRATION=1 for the real "
        "Session 14 pause/resume proof."
    ),
)

if RUN_POSTGRES_INTEGRATION and not DATABASE_URL:
    raise RuntimeError("SESSION14_POSTGRES_DATABASE_URL is required")


@pytest.fixture
def event_loop_policy():
    """Psycopg async requires SelectorEventLoop on Windows."""

    if os.name == "nt":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.get_event_loop_policy()


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
                        "retrieval_method": "postgres_restart_fake",
                    }
                ]
            }
        ),
        search_k=5,
    )


def _service(
    checkpointer: object,
    dependencies: GraphNodeDependencies,
) -> GraphEstimationService:
    graph = build_session14_estimation_graph(
        dependencies,
        human_review_gate=build_session14_human_review_gate(),
        checkpointer=checkpointer,
    )
    return GraphEstimationService(
        graph=graph,
        graph_version=SESSION14_GRAPH_VERSION,
        graph_name=SESSION14_GRAPH_NAME,
        state_factory=new_session14_estimation_graph_state,
    )


@pytest.mark.asyncio
async def test_pause_survives_reopen_and_resume_keeps_same_thread() -> None:
    estimation_id = uuid4()
    transcript = (
        "Build secure authentication with a persistent, auditable "
        "human review decision."
    )
    dependencies = _dependencies()

    async with open_postgres_checkpointer(DATABASE_URL) as saver:
        paused = await _service(saver, dependencies).estimate(
            transcript=transcript,
            estimation_id=estimation_id,
        )
        assert paused.execution_status == "awaiting_human_review"
        assert paused.state["human_review_revision"] == 1
        assert paused.interrupts[0]["value"]["reason_codes"] == [
            "low_confidence"
        ]

    async with open_postgres_checkpointer(DATABASE_URL) as saver:
        resumed = await _service(saver, dependencies).resume_human_review(
            estimation_id=estimation_id,
            decision=Session14HumanReviewDecision(
                action="approve",
                expected_revision=1,
                actor="postgres-restart-smoke",
                idempotency_key="postgres-review-001",
            ),
        )
        assert resumed.execution_status == "completed"
        assert resumed.thread_id == paused.thread_id
        assert resumed.state["human_review_status"] == "approved"

    async with open_postgres_checkpointer(DATABASE_URL) as saver:
        reopened = await _service(saver, dependencies).estimate(
            transcript=transcript,
            estimation_id=estimation_id,
        )

    assert reopened.state == resumed.state
    assert reopened.thread_id == paused.thread_id
    assert reopened.state["status"] == "validated"
    assert [
        event["event_type"]
        for event in reopened.state["trace_events"][-2:]
    ] == [
        "session14_human_review_paused",
        "session14_human_review_approve",
    ]

    artifact_path = os.getenv("SESSION14_POSTGRES_EVIDENCE_PATH")
    if artifact_path:
        path = Path(artifact_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": "session14.postgres_hitl.v1",
                    "connection_cycles": 3,
                    "estimation_id": str(estimation_id),
                    "thread_id": reopened.thread_id,
                    "pause_restored": True,
                    "same_thread_resume": True,
                    "trace_continuity": True,
                    "terminal_status": reopened.state["status"],
                    "human_review_status": reopened.state[
                        "human_review_status"
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
