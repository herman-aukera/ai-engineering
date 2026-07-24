"""Capture one hosted Session 14 ORBITA pause/reopen/resume trace."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import logfire
from fastapi import FastAPI
from opentelemetry import trace

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.nodes.session14_human_review import (
    build_session14_human_review_gate,
)
from app.generation.graph.observability import (
    SESSION14_ROOT_SPAN_NAME,
    GraphTracer,
    flush_logfire_graph_traces,
    get_logfire_graph_tracer,
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
from app.generation.graph.session14_runtime import SESSION14_GRAPH_VERSION
from app.routers.graph_estimations import router
from app.services.graph_estimation import GraphEstimationService

TEACHER_FIXTURE = (
    Path(__file__).parents[1]
    / "exercises"
    / "session-14"
    / "sample_transcript_edge_case.txt"
)
DEFAULT_ARTIFACT = (
    Path(__file__).parents[1]
    / "artifacts"
    / "session14"
    / "hosted_pause_resume_evidence.json"
)
FIXTURE_GIT_BLOB = "53b0a4625464fb5f4759972fa30a356972260986"


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _dependencies() -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor(
            [
                {
                    "requirement_id": "REQ-001",
                    "text": "Provide an auditable ORBITA estimation.",
                }
            ]
        ),
        component_classifier=FakeComponentClassifier(
            [
                {
                    "component_id": "CMP-001",
                    "name": "ORBITA integration",
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
                        "budget_id": "BUD-ORBITA-001",
                        "reference_component_id": "REF-001",
                        "source_document_id": "DOC-001",
                        "source_chunk_id": "CH-001",
                        "recorded_hours": 40.0,
                        "distance": 0.1,
                        "score": 0.9,
                        "retrieval_method": "session14_hosted_evidence",
                    }
                ]
            }
        ),
        search_k=5,
    )


def _service(checkpointer: object, tracer: GraphTracer) -> GraphEstimationService:
    graph = build_session14_estimation_graph(
        _dependencies(),
        human_review_gate=build_session14_human_review_gate(),
        checkpointer=checkpointer,
        tracer=tracer,
    )
    return GraphEstimationService(
        graph=graph,
        tracer=tracer,
        root_span_name=SESSION14_ROOT_SPAN_NAME,
        graph_version=SESSION14_GRAPH_VERSION,
        graph_name=SESSION14_GRAPH_NAME,
        state_factory=new_session14_estimation_graph_state,
    )


def _app(service: GraphEstimationService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.graph_estimation_service = service
    return app


async def _post(
    app: FastAPI,
    path: str,
    payload: Mapping[str, object],
) -> dict[str, Any]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://session14-evidence",
        timeout=30.0,
    ) as client:
        response = await client.post(path, json=dict(payload))
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, dict):
        raise RuntimeError("Session 14 API response must be a mapping")
    return value


def _rows_from_query_payload(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return [dict(row) for row in payload if isinstance(row, Mapping)]
    if not isinstance(payload, Mapping):
        return []

    rows = payload.get("rows")
    columns = payload.get("columns")
    if isinstance(rows, list) and isinstance(columns, list):
        names = [
            str(column.get("name")) if isinstance(column, Mapping) else str(column)
            for column in columns
        ]
        normalized: list[dict[str, object]] = []
        for row in rows:
            if isinstance(row, Mapping):
                normalized.append(dict(row))
            elif isinstance(row, list) and len(row) == len(names):
                normalized.append(dict(zip(names, row, strict=True)))
        return normalized

    for key in ("data", "result"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            return [dict(row) for row in candidate if isinstance(row, Mapping)]
    return []


async def _query_hosted_trace(
    *,
    api_key: str,
    trace_id: str,
) -> list[dict[str, object]]:
    base_url = os.getenv(
        "LOGFIRE_QUERY_BASE_URL",
        "https://logfire-eu.pydantic.dev",
    ).rstrip("/")
    sql = f"""
        SELECT
            trace_id,
            span_id,
            parent_span_id,
            span_name,
            attributes->>'execution_mode' AS execution_mode,
            attributes->>'execution_status' AS execution_status,
            attributes->>'human_review_status' AS human_review_status,
            attributes->>'node_name' AS node_name
        FROM records
        WHERE trace_id = '{trace_id}'
        ORDER BY start_timestamp ASC
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    params = {
        "sql": sql,
        "row_oriented": "true",
        "limit": "500",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(10):
            response = await client.get(
                f"{base_url}/v1/query",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            rows = _rows_from_query_payload(response.json())
            if rows:
                return rows
            await asyncio.sleep(min(2 + attempt, 8))
    raise RuntimeError("Hosted trace was not queryable after telemetry flush")


async def capture() -> dict[str, object]:
    token = _required_environment("LOGFIRE_TOKEN")
    database_url = _required_environment("SESSION14_POSTGRES_DATABASE_URL")
    transcript = TEACHER_FIXTURE.read_text(encoding="utf-8")
    if 'Proyecto "ORBITA"' not in transcript:
        raise RuntimeError("Teacher ORBITA fixture was not loaded")

    estimation_id = uuid4()
    evidence_run_id = str(uuid4())
    thread_id = f"estimate:{estimation_id}"
    tracer = get_logfire_graph_tracer()
    source_sha = os.getenv("GITHUB_SHA", "local")

    with logfire.span(
        "session14.evidence.journey",
        evidence_run_id=evidence_run_id,
        estimation_id=str(estimation_id),
        thread_id=thread_id,
        source_sha=source_sha,
        fixture_name=TEACHER_FIXTURE.name,
        fixture_git_blob=FIXTURE_GIT_BLOB,
    ) as journey_span:
        span_context = trace.get_current_span().get_span_context()
        if not span_context.is_valid:
            raise RuntimeError("Logfire did not create a valid evidence span")
        trace_id = f"{span_context.trace_id:032x}"
        span_id = f"{span_context.span_id:016x}"

        async with open_postgres_checkpointer(database_url) as saver:
            paused = await _post(
                _app(_service(saver, tracer)),
                "/api/v1/estimate/graph",
                {
                    "transcript": transcript,
                    "estimation_id": str(estimation_id),
                },
            )

        if paused.get("status") != "awaiting_human_review":
            raise RuntimeError("ORBITA execution did not pause for human review")
        if paused.get("thread_id") != thread_id or paused.get("revision") != 1:
            raise RuntimeError("Paused checkpoint identity or revision is invalid")

        async with open_postgres_checkpointer(database_url) as saver:
            resumed = await _post(
                _app(_service(saver, tracer)),
                f"/api/v1/estimate/graph/{estimation_id}/resume",
                {
                    "action": "approve",
                    "expected_revision": 1,
                    "actor": "github-actions-session14-evidence",
                    "idempotency_key": f"session14-evidence-{evidence_run_id}",
                },
            )

        if resumed.get("status") != "validated":
            raise RuntimeError("Resumed ORBITA execution did not validate")
        if resumed.get("thread_id") != thread_id or resumed.get("revision") != 2:
            raise RuntimeError("Resumed execution did not preserve thread identity")
        if resumed.get("human_review_status") != "approved":
            raise RuntimeError("Human approval was not folded into graph state")

        async with open_postgres_checkpointer(database_url) as saver:
            reopened = await _post(
                _app(_service(saver, tracer)),
                "/api/v1/estimate/graph",
                {
                    "transcript": transcript,
                    "estimation_id": str(estimation_id),
                },
            )

        if reopened != resumed:
            raise RuntimeError("Terminal checkpoint changed after third lifecycle")

        journey_span.set_attribute("pause_status", "awaiting_human_review")
        journey_span.set_attribute("resume_status", "validated")
        journey_span.set_attribute("reopen_status", "validated")
        journey_span.set_attribute("human_review_action", "approve")
        journey_span.set_attribute("checkpoint_lifecycles", 3)
        journey_span.set_attribute("evidence_status", "complete")

    if not flush_logfire_graph_traces(timeout_millis=15_000):
        raise RuntimeError("Logfire force_flush did not complete")

    hosted_rows = await _query_hosted_trace(api_key=token, trace_id=trace_id)
    span_names = [str(row.get("span_name", "")) for row in hosted_rows]
    execution_statuses = {
        str(row.get("execution_status"))
        for row in hosted_rows
        if row.get("execution_status") is not None
    }
    if "session14.evidence.journey" not in span_names:
        raise RuntimeError("Hosted evidence root span is missing")
    if SESSION14_ROOT_SPAN_NAME not in span_names:
        raise RuntimeError("Hosted Session 14 graph spans are missing")
    if not {"awaiting_human_review", "completed"}.issubset(execution_statuses):
        raise RuntimeError("Hosted trace does not contain pause and resume statuses")

    artifact = {
        "schema_version": "session14.hosted_pause_resume.v1",
        "source_sha": source_sha,
        "fixture_name": TEACHER_FIXTURE.name,
        "fixture_git_blob": FIXTURE_GIT_BLOB,
        "evidence_run_id": evidence_run_id,
        "estimation_id": str(estimation_id),
        "thread_id": thread_id,
        "trace_id": trace_id,
        "root_span_id": span_id,
        "hosted_span_count": len(hosted_rows),
        "pause_status": paused["status"],
        "resume_status": resumed["status"],
        "human_review_status": resumed["human_review_status"],
        "revision_before": paused["revision"],
        "revision_after": resumed["revision"],
        "checkpoint_lifecycles": 3,
        "same_thread_resume": True,
        "terminal_reread_equal": True,
        "public_trace_url": None,
        "public_trace_status": "create_in_logfire_ui_from_trace_id",
    }
    artifact_path = Path(
        os.getenv("SESSION14_HOSTED_EVIDENCE_PATH", str(DEFAULT_ARTIFACT))
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return artifact


def main() -> None:
    artifact = asyncio.run(capture())
    print(json.dumps(artifact, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
