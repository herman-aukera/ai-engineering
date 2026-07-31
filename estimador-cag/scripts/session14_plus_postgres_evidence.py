"""Capture PostgreSQL pause/reopen/resume evidence for Session 14 Plus."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.nodes.session14_human_review import (
    build_session14_human_review_gate,
)
from app.generation.graph.observability import NOOP_GRAPH_TRACER
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.runtime import open_postgres_checkpointer
from app.generation.graph.session14_plus_build import (
    SESSION14_PLUS_GRAPH_NAME,
    build_session14_plus_estimation_graph,
)
from app.generation.graph.session14_plus_state import (
    new_session14_plus_estimation_graph_state,
)
from app.schemas.session14_human_review import (
    Session14HumanReviewDecision,
)
from app.schemas.session14_plus_policy import ModelCapabilityRecord
from app.services.graph_estimation import GraphEstimationService
from app.services.session14_plus_policy import build_capability_registry

SESSION14_PLUS_GRAPH_VERSION = "session14.plus.v1"
TEACHER_FIXTURE = (
    Path(__file__).parents[1]
    / "exercises"
    / "session-14"
    / "sample_transcript_edge_case.txt"
)
DEFAULT_ARTIFACT = (
    Path(__file__).parents[1]
    / "artifacts"
    / "session14_plus"
    / "postgres_pause_resume.json"
)


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _capability_registry():
    verified_at = datetime(2026, 7, 31, tzinfo=UTC)

    def record(
        *,
        record_id: str,
        provider: str,
        model: str,
        efforts: list[str],
        speed_class: str = "balanced",
        supports_tools: bool = True,
        max_output_tokens: int = 20_000,
    ) -> ModelCapabilityRecord:
        return ModelCapabilityRecord(
            record_id=record_id,
            provider=provider,
            provider_model_id=model,
            display_name=model,
            capability_tier="ci-contract",
            context_window_tokens=1_000_000,
            max_output_tokens=max_output_tokens,
            modalities=["text"],
            supports_tools=supports_tools,
            supports_structured_output=True,
            reasoning_efforts=efforts,
            speed_class=speed_class,
            cost_metadata_version="ci-contract-v1",
            lifecycle="contract_verified",
            verified_at=verified_at,
            calibration_status="baseline",
            enabled=True,
        )

    return build_capability_registry(
        [
            record(
                record_id="cap:deepseek:flash",
                provider="deepseek",
                model="deepseek-v4-flash",
                efforts=["none", "high"],
                speed_class="fast",
            ),
            record(
                record_id="cap:deepseek:pro",
                provider="deepseek",
                model="deepseek-v4-pro",
                efforts=["none", "high", "max"],
            ),
            record(
                record_id="cap:moonshot:kimi-k2.6",
                provider="moonshot",
                model="kimi-k2.6",
                efforts=["none", "high"],
            ),
            record(
                record_id="cap:python:recovery",
                provider="python",
                model="deterministic-recovery",
                efforts=["none"],
                speed_class="deterministic",
                supports_tools=False,
                max_output_tokens=0,
            ),
        ],
        registry_version="session14-plus-ci-contract-v1",
        generated_at=verified_at,
    )


def _dependencies() -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor(
            [
                {
                    "requirement_id": "REQ-ORBITA-001",
                    "text": "Provide an auditable ORBITA integration estimate.",
                }
            ]
        ),
        component_classifier=FakeComponentClassifier(
            [
                {
                    "component_id": "CMP-ORBITA-001",
                    "name": "ORBITA integration",
                    "category": "backend",
                    "requirement_ids": ["REQ-ORBITA-001"],
                }
            ]
        ),
        budget_searcher=FakeBudgetSearcher(
            {
                "CMP-ORBITA-001": [
                    {
                        "component_id": "CMP-ORBITA-001",
                        "budget_id": "BUD-ORBITA-001",
                        "reference_component_id": "REF-ORBITA-001",
                        "source_document_id": "DOC-ORBITA-001",
                        "source_chunk_id": "CH-ORBITA-001",
                        "recorded_hours": 40.0,
                        "distance": 0.1,
                        "score": 0.9,
                        "retrieval_method": "session14_plus_postgres_evidence",
                    }
                ]
            }
        ),
        search_k=5,
    )


def _service(checkpointer: object, *, source_sha: str) -> GraphEstimationService:
    graph = build_session14_plus_estimation_graph(
        _dependencies(),
        capability_registry=_capability_registry(),
        human_review_gate=build_session14_human_review_gate(),
        repository_state={
            "branch": "gg-session-14/plus",
            "sha": source_sha,
            "base_branch": "session-14/pre-work",
        },
        checkpointer=checkpointer,
        tracer=NOOP_GRAPH_TRACER,
    )
    return GraphEstimationService(
        graph=graph,
        tracer=NOOP_GRAPH_TRACER,
        root_span_name="session14.plus.graph.run",
        graph_version=SESSION14_PLUS_GRAPH_VERSION,
        graph_name=SESSION14_PLUS_GRAPH_NAME,
        state_factory=new_session14_plus_estimation_graph_state,
    )


async def capture() -> dict[str, object]:
    database_url = _required_environment(
        "SESSION14_PLUS_POSTGRES_DATABASE_URL"
    )
    transcript = TEACHER_FIXTURE.read_text(encoding="utf-8")
    if 'Proyecto "ORBITA"' not in transcript:
        raise RuntimeError("teacher ORBITA fixture was not loaded")

    estimation_id = uuid4()
    source_sha = os.getenv("GITHUB_SHA", "local")

    async with open_postgres_checkpointer(database_url) as saver:
        paused = await _service(
            saver,
            source_sha=source_sha,
        ).estimate(
            transcript=transcript,
            estimation_id=estimation_id,
        )

    if paused.execution_status != "awaiting_human_review":
        raise RuntimeError("Session 14 Plus did not pause for human review")
    paused_state = paused.state
    if paused_state.get("plus_competition_completed") is not True:
        raise RuntimeError("candidate competition did not complete before pause")
    if len(paused_state.get("plus_competition_candidates", [])) != 4:
        raise RuntimeError("four competition candidates were not persisted")
    paused_context = paused_state.get("plus_compacted_context")
    if not isinstance(paused_context, dict):
        raise RuntimeError("paused compacted context is missing")
    pause_fingerprint = paused_context.get("fingerprint")

    async with open_postgres_checkpointer(database_url) as saver:
        resumed = await _service(
            saver,
            source_sha=source_sha,
        ).resume_human_review(
            estimation_id=estimation_id,
            decision=Session14HumanReviewDecision(
                action="approve",
                expected_revision=1,
                actor="github-actions-session14-plus",
                idempotency_key=(
                    f"session14-plus-{estimation_id}-approve"
                ),
            ),
        )

    if resumed.execution_status != "completed":
        raise RuntimeError("Session 14 Plus resume did not complete")
    if resumed.thread_id != paused.thread_id:
        raise RuntimeError("resume did not preserve thread identity")
    resumed_state = resumed.state
    if resumed_state.get("human_review_status") != "approved":
        raise RuntimeError("human approval was not persisted")
    if resumed_state.get("human_review_revision") != 2:
        raise RuntimeError("human review revision did not advance")
    resumed_context = resumed_state.get("plus_compacted_context")
    if not isinstance(resumed_context, dict):
        raise RuntimeError("resumed compacted context is missing")
    if resumed_context.get("fingerprint") == pause_fingerprint:
        raise RuntimeError("context fingerprint did not refresh after resume")
    validation_state = resumed_context.get("validation_state")
    if not isinstance(validation_state, dict):
        raise RuntimeError("resumed context validation state is missing")
    if validation_state.get("human_review_status") != "approved":
        raise RuntimeError("resumed context did not retain human approval")

    async with open_postgres_checkpointer(database_url) as saver:
        reread = await _service(
            saver,
            source_sha=source_sha,
        ).estimate(
            transcript=transcript,
            estimation_id=estimation_id,
        )

    if reread.execution_status != "completed":
        raise RuntimeError("terminal checkpoint was not reread as completed")
    if reread.thread_id != resumed.thread_id:
        raise RuntimeError("terminal reread changed thread identity")
    if reread.state != resumed.state:
        raise RuntimeError("terminal state changed after third lifecycle")

    assessment = resumed_state.get("plus_competition_assessment", {})
    artifact = {
        "schema_version": "session14.plus.postgres-evidence.v1",
        "source_sha": source_sha,
        "fixture_name": TEACHER_FIXTURE.name,
        "estimation_id": str(estimation_id),
        "thread_id": resumed.thread_id,
        "pause_execution_status": paused.execution_status,
        "resume_execution_status": resumed.execution_status,
        "pause_human_review_status": paused_state.get(
            "human_review_status"
        ),
        "resume_human_review_status": resumed_state.get(
            "human_review_status"
        ),
        "revision_before": paused_state.get("human_review_revision"),
        "revision_after": resumed_state.get("human_review_revision"),
        "same_thread_resume": True,
        "terminal_reread_equal": True,
        "checkpoint_lifecycles": 3,
        "competition_candidate_count": len(
            resumed_state.get("plus_competition_candidates", [])
        ),
        "competition_disposition": (
            assessment.get("disposition")
            if isinstance(assessment, dict)
            else None
        ),
        "competition_energy_snapshot_id": (
            assessment.get("energy_snapshot", {}).get("snapshot_id")
            if isinstance(assessment, dict)
            and isinstance(assessment.get("energy_snapshot"), dict)
            else None
        ),
        "context_revision_before": paused_state.get(
            "plus_context_source_revision"
        ),
        "context_revision_after": resumed_state.get(
            "plus_context_source_revision"
        ),
        "context_fingerprint_before": pause_fingerprint,
        "context_fingerprint_after": resumed_context.get("fingerprint"),
        "authorized_capabilities": resumed_state.get(
            "plus_authorized_capabilities",
            {},
        ),
    }
    artifact_path = Path(
        os.getenv(
            "SESSION14_PLUS_POSTGRES_EVIDENCE_PATH",
            str(DEFAULT_ARTIFACT),
        )
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return artifact


def main() -> None:
    print(json.dumps(asyncio.run(capture()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
