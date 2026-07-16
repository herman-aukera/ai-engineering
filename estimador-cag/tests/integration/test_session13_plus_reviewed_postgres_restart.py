"""Real PostgreSQL restart/resume proof for both durable human gates."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from langgraph.types import Command

from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.reviewed_build import build_reviewed_estimation_graph
from app.generation.graph.runtime import open_postgres_checkpointer
from app.generation.graph.state import new_estimation_graph_state
from app.services.graph_estimation import thread_id_from_estimation_id

RUN_POSTGRES_INTEGRATION = os.getenv("RUN_POSTGRES_INTEGRATION") == "1"
DATABASE_URL = os.getenv("SESSION13_POSTGRES_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not RUN_POSTGRES_INTEGRATION,
    reason="Set RUN_POSTGRES_INTEGRATION=1 for the real reviewed restart proof.",
)

if RUN_POSTGRES_INTEGRATION and not DATABASE_URL:
    raise RuntimeError("SESSION13_POSTGRES_DATABASE_URL is required")


@pytest.fixture
def event_loop_policy():
    """Psycopg async requires SelectorEventLoop on Windows."""

    if os.name == "nt":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.get_event_loop_policy()


class Extractor:
    async def extract_requirements(self, *, transcript: str):
        assert transcript
        return [{"requirement_id": "req-1", "text": "Authenticate users."}]


class Classifier:
    async def classify_components(self, *, requirements):
        assert requirements
        return [
            {
                "component_id": "cmp-auth",
                "name": "Authentication",
                "category": "backend",
                "requirement_ids": ["req-1"],
            }
        ]


class Searcher:
    async def search_budgets(self, *, component, k: int):
        assert component["component_id"] == "cmp-auth"
        assert k == 5
        return [
            {
                "component_id": "cmp-auth",
                "budget_id": f"BUD-{index}",
                "reference_component_id": f"REF-{index}",
                "source_document_id": f"DOC-{index}",
                "source_chunk_id": f"CH-{index}",
                "recorded_hours": hours,
                "distance": 0.1,
                "score": 0.9,
                "retrieval_method": "restart_fake",
            }
            for index, hours in enumerate((32.0, 40.0, 48.0), start=1)
        ]


def _dependencies() -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=Extractor(),
        component_classifier=Classifier(),
        budget_searcher=Searcher(),
    )


def _initial_state(estimation_id: str):
    state = new_estimation_graph_state(
        transcript="Build secure authentication with an auditable review trail.",
        estimation_id=estimation_id,
        graph_version="session13.plus.v1",
    )
    state.update(
        {
            "human_review_mode": "required",
            "structure_review_revision": 0,
            "final_review_revision": 0,
        }
    )
    return state


@pytest.mark.asyncio
async def test_reviewed_interrupts_survive_two_process_style_reopens() -> None:
    estimation_id = str(uuid4())
    thread_id = thread_id_from_estimation_id(estimation_id)
    config = {"configurable": {"thread_id": thread_id}}

    async with open_postgres_checkpointer(DATABASE_URL) as saver:
        graph = build_reviewed_estimation_graph(_dependencies(), checkpointer=saver)
        structure_pause = await graph.ainvoke(_initial_state(estimation_id), config=config)
        assert structure_pause["__interrupt__"][0].value["gate"] == "structure_review"

    async with open_postgres_checkpointer(DATABASE_URL) as saver:
        graph = build_reviewed_estimation_graph(_dependencies(), checkpointer=saver)
        persisted = await graph.aget_state(config)
        assert persisted.values["estimation_id"] == estimation_id
        assert persisted.interrupts[0].value["gate"] == "structure_review"
        final_pause = await graph.ainvoke(
            Command(resume={"action": "approve", "expected_revision": 0}),
            config=config,
        )
        assert final_pause["__interrupt__"][0].value["gate"] == "final_estimate_review"
        trace_before_final_restart = list(final_pause["trace_events"])

    async with open_postgres_checkpointer(DATABASE_URL) as saver:
        graph = build_reviewed_estimation_graph(_dependencies(), checkpointer=saver)
        persisted = await graph.aget_state(config)
        assert persisted.interrupts[0].value["gate"] == "final_estimate_review"
        completed = await graph.ainvoke(
            Command(
                resume={
                    "action": "approve",
                    "expected_revision": 0,
                    "actor": "restart-smoke",
                }
            ),
            config=config,
        )

    assert completed.get("__interrupt__", ()) == ()
    assert completed["status"] == "validated"
    assert completed["estimate"]["total_hours"] == 40.0
    assert completed["trace_events"][: len(trace_before_final_restart)] == trace_before_final_restart
    assert completed["final_review_status"] == "approved"

    artifact_path = os.getenv("SESSION13_PLUS_POSTGRES_EVIDENCE_PATH")
    if artifact_path:
        path = Path(artifact_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": "session13.plus.postgres_restart.v1",
                    "connection_cycles": 3,
                    "estimation_id": estimation_id,
                    "thread_id": thread_id,
                    "structure_gate_restored": True,
                    "final_gate_restored": True,
                    "trace_continuity": True,
                    "terminal_status": completed["status"],
                    "total_hours": completed["estimate"]["total_hours"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
