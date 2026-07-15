from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.generation.graph.build import build_estimation_graph
from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.runtime import open_postgres_checkpointer
from app.services.graph_estimation import GraphEstimationService

RUN_POSTGRES_INTEGRATION = (
    os.getenv("RUN_POSTGRES_INTEGRATION") == "1"
)

pytestmark = pytest.mark.skipif(
    not RUN_POSTGRES_INTEGRATION,
    reason=(
        "Set RUN_POSTGRES_INTEGRATION=1 to execute "
        "the real PostgreSQL persistence proof."
    ),
)

DATABASE_URL = os.getenv(
    "SESSION13_POSTGRES_DATABASE_URL",
    (
        "postgresql+asyncpg://estimator:estimator@"
        "localhost:5432/estimator"
    ),
)

TRANSCRIPT = (
    "The client requires JWT authentication and auditable "
    "logging for all sensitive administrative operations."
)

REQUIREMENTS = [
    {
        "requirement_id": "REQ-001",
        "text": "Users authenticate with JWT.",
    }
]

COMPONENTS = [
    {
        "component_id": "CMP-001",
        "name": "JWT authentication",
        "category": "backend",
        "requirement_ids": ["REQ-001"],
    }
]

MATCHES = [
    {
        "component_id": "CMP-001",
        "budget_id": "BUD-101",
        "reference_component_id": "AUTH-01",
        "source_document_id": "DOC-101",
        "source_chunk_id": "CH-101",
        "recorded_hours": 32.0,
        "distance": 0.1,
        "score": 0.9,
        "retrieval_method": "hybrid",
    },
    {
        "component_id": "CMP-001",
        "budget_id": "BUD-102",
        "reference_component_id": "AUTH-02",
        "source_document_id": "DOC-102",
        "source_chunk_id": "CH-102",
        "recorded_hours": 40.0,
        "distance": 0.1,
        "score": 0.9,
        "retrieval_method": "hybrid",
    },
    {
        "component_id": "CMP-001",
        "budget_id": "BUD-103",
        "reference_component_id": "AUTH-03",
        "source_document_id": "DOC-103",
        "source_chunk_id": "CH-103",
        "recorded_hours": 48.0,
        "distance": 0.1,
        "score": 0.9,
        "retrieval_method": "hybrid",
    },
]


def _dependencies() -> tuple[
    GraphNodeDependencies,
    FakeRequirementExtractor,
    FakeComponentClassifier,
    FakeBudgetSearcher,
]:
    extractor = FakeRequirementExtractor(REQUIREMENTS)
    classifier = FakeComponentClassifier(COMPONENTS)
    searcher = FakeBudgetSearcher(
        {"CMP-001": MATCHES}
    )

    dependencies = GraphNodeDependencies(
        requirement_extractor=extractor,
        component_classifier=classifier,
        budget_searcher=searcher,
        search_k=5,
    )

    return dependencies, extractor, classifier, searcher


def _write_evidence(
    *,
    estimation_id: str,
    thread_id: str,
    status: str,
    total_hours: float,
    extractor_calls: int,
    classifier_calls: int,
    searcher_calls: int,
) -> None:
    raw_path = os.getenv(
        "SESSION13_POSTGRES_EVIDENCE_PATH"
    )

    if not raw_path:
        return

    evidence_path = Path(raw_path)
    evidence_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    evidence = {
        "schema_version": (
            "session13.postgres_persistence.v1"
        ),
        "generated_at": datetime.now(UTC).isoformat(),
        "proof": "write-close-reopen-reread",
        "database_backend": "postgresql",
        "connection_cycles": 2,
        "estimation_id": estimation_id,
        "thread_id": thread_id,
        "terminal_status": status,
        "total_hours": total_hours,
        "state_equal_after_reopen": True,
        "reducer_counts": {
            "budget_matches": 3,
            "errors": 0,
            "trace_events": 5,
        },
        "node_call_counts": {
            "extract_requirements": extractor_calls,
            "classify_components": classifier_calls,
            "search_budgets": searcher_calls,
        },
        "nodes_reexecuted_after_reopen": False,
    }

    evidence_path.write_text(
        json.dumps(
            evidence,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_completed_graph_survives_saver_reopen() -> None:
    (
        dependencies,
        extractor,
        classifier,
        searcher,
    ) = _dependencies()

    estimation_id = uuid4()

    async with open_postgres_checkpointer(
        DATABASE_URL
    ) as first_checkpointer:
        first_graph = build_estimation_graph(
            dependencies,
            checkpointer=first_checkpointer,
        )
        first_service = GraphEstimationService(
            graph=first_graph
        )

        first = await first_service.estimate(
            transcript=TRANSCRIPT,
            estimation_id=estimation_id,
        )

        assert first.state["status"] == "validated"
        assert first.state["review_required"] is False
        assert first.state["errors"] == []
        assert first.state["estimate"]["total_hours"] == 40.0
        assert len(first.state["budget_matches"]) == 3
        assert len(first.state["trace_events"]) == 5

    calls_after_first_run = {
        "extractor": len(extractor.calls),
        "classifier": len(classifier.calls),
        "searcher": len(searcher.calls),
    }

    assert calls_after_first_run == {
        "extractor": 1,
        "classifier": 1,
        "searcher": 1,
    }

    async with open_postgres_checkpointer(
        DATABASE_URL
    ) as reopened_checkpointer:
        reopened_graph = build_estimation_graph(
            dependencies,
            checkpointer=reopened_checkpointer,
        )
        reopened_service = GraphEstimationService(
            graph=reopened_graph
        )

        reopened = await reopened_service.estimate(
            transcript=TRANSCRIPT,
            estimation_id=estimation_id,
        )

    assert reopened.estimation_id == first.estimation_id
    assert reopened.thread_id == first.thread_id
    assert reopened.state == first.state

    assert len(extractor.calls) == 1
    assert len(classifier.calls) == 1
    assert len(searcher.calls) == 1

    assert len(reopened.state["budget_matches"]) == 3
    assert len(reopened.state["errors"]) == 0
    assert len(reopened.state["trace_events"]) == 5

    _write_evidence(
        estimation_id=reopened.estimation_id,
        thread_id=reopened.thread_id,
        status=reopened.state["status"],
        total_hours=reopened.state["estimate"][
            "total_hours"
        ],
        extractor_calls=len(extractor.calls),
        classifier_calls=len(classifier.calls),
        searcher_calls=len(searcher.calls),
    )
