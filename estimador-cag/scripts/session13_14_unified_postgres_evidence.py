"""Capture durable Session 13 + 14 Plus unified lifecycle evidence."""

from __future__ import annotations

import asyncio
import json
import os
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
from app.generation.graph.observability import (
    NOOP_GRAPH_TRACER,
    UNIFIED_ROOT_SPAN_NAME,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.runtime import open_postgres_checkpointer
from app.generation.graph.unified_build import (
    UNIFIED_GRAPH_NAME,
    build_unified_estimation_graph,
)
from app.generation.graph.unified_state import (
    new_unified_estimation_graph_state,
)
from app.schemas.session14_human_review import Session14HumanReviewDecision
from app.services.graph_estimation import GraphEstimationService
from app.services.unified_capability_registry import (
    build_unified_capability_registry,
    load_benchmark_snapshot,
)

UNIFIED_GRAPH_VERSION = "session13_14_plus.unified.v1"
TEACHER_FIXTURE = (
    Path(__file__).parents[1]
    / "exercises"
    / "session-14"
    / "sample_transcript_edge_case.txt"
)
DEFAULT_ARTIFACT = (
    Path(__file__).parents[1]
    / "artifacts"
    / "session13_14_unified"
    / "postgres_pause_resume.json"
)
_BOSS_ACTIONS = {
    "accept",
    "retry_selected",
    "fallback_provider",
    "human_review",
    "reject",
}


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
                        "distance": 0.08,
                        "score": 0.92,
                        "retrieval_method": "unified-postgres-evidence",
                    },
                    {
                        "component_id": "CMP-ORBITA-001",
                        "budget_id": "BUD-ORBITA-002",
                        "reference_component_id": "REF-ORBITA-002",
                        "source_document_id": "DOC-ORBITA-002",
                        "source_chunk_id": "CH-ORBITA-002",
                        "recorded_hours": 42.0,
                        "distance": 0.07,
                        "score": 0.93,
                        "retrieval_method": "unified-postgres-evidence",
                    },
                    {
                        "component_id": "CMP-ORBITA-001",
                        "budget_id": "BUD-ORBITA-003",
                        "reference_component_id": "REF-ORBITA-003",
                        "source_document_id": "DOC-ORBITA-003",
                        "source_chunk_id": "CH-ORBITA-003",
                        "recorded_hours": 44.0,
                        "distance": 0.09,
                        "score": 0.91,
                        "retrieval_method": "unified-postgres-evidence",
                    },
                ]
            }
        ),
        search_k=5,
    )


def _service(checkpointer: object, *, source_sha: str) -> GraphEstimationService:
    graph = build_unified_estimation_graph(
        _dependencies(),
        capability_registry=build_unified_capability_registry(
            load_benchmark_snapshot()
        ),
        human_review_gate=build_session14_human_review_gate(
            confidence_threshold=1.0
        ),
        repository_state={
            "branch": "gg-session-14/plus-consolidated",
            "sha": source_sha,
            "base_branch": "gg-session-14/plus",
            "session13_plus_source": (
                "f87605cb8a8ee5ff2606c51e5490b6beb2ca7f7a"
            ),
            "session14_plus_source": (
                "34011bcd9442130e09ab776d9072c0d53a2d93c2"
            ),
        },
        checkpointer=checkpointer,
        tracer=NOOP_GRAPH_TRACER,
        structure_review_mode="disabled",
        retrieval_mode="sequential",
    )
    return GraphEstimationService(
        graph=graph,
        tracer=NOOP_GRAPH_TRACER,
        root_span_name=UNIFIED_ROOT_SPAN_NAME,
        graph_version=UNIFIED_GRAPH_VERSION,
        graph_name=UNIFIED_GRAPH_NAME,
        state_factory=new_unified_estimation_graph_state,
    )


def _require_mapping(state: dict[str, object], key: str) -> dict[str, object]:
    value = state.get(key)
    if not isinstance(value, dict) or not value:
        raise RuntimeError(f"{key} is missing from unified state")
    return value


def _critic_evidence(
    critic_report: dict[str, object],
) -> tuple[str, list[object]]:
    verdict = critic_report.get("verdict")
    issues = critic_report.get("issues")
    if not isinstance(verdict, str) or not verdict:
        raise RuntimeError("Critic verdict is missing from unified state")
    if not isinstance(issues, list):
        raise RuntimeError("Critic issues are missing from unified state")
    return verdict, issues


def _boss_evidence(
    boss_decision: dict[str, object],
) -> tuple[str, list[object]]:
    action = boss_decision.get("action")
    issue_codes = boss_decision.get("issue_codes")
    if action not in _BOSS_ACTIONS:
        raise RuntimeError("Boss action is invalid or missing")
    if not isinstance(issue_codes, list):
        raise RuntimeError("Boss issue codes are missing from unified state")
    return str(action), issue_codes


async def capture() -> dict[str, object]:
    database_url = _required_environment(
        "SESSION13_14_UNIFIED_POSTGRES_DATABASE_URL"
    )
    transcript = TEACHER_FIXTURE.read_text(encoding="utf-8")
    if 'Proyecto "ORBITA"' not in transcript:
        raise RuntimeError("teacher ORBITA fixture was not loaded")

    estimation_id = uuid4()
    source_sha = os.getenv("GITHUB_SHA", "local")

    async with open_postgres_checkpointer(database_url) as saver:
        paused = await _service(saver, source_sha=source_sha).estimate(
            transcript=transcript,
            estimation_id=estimation_id,
        )

    if paused.execution_status != "awaiting_human_review":
        raise RuntimeError("unified graph did not pause for human review")
    if not paused.interrupts:
        raise RuntimeError("unified graph paused without an interrupt payload")
    paused_state = paused.state
    if paused_state.get("unified_structure_completed") is not True:
        raise RuntimeError("unified structure phase did not complete")
    if paused_state.get("unified_estimation_completed") is not True:
        raise RuntimeError("unified estimation phase did not complete")
    if paused_state.get("plus_competition_completed") is not True:
        raise RuntimeError("candidate competition did not complete")
    if len(paused_state.get("plus_competition_candidates", [])) != 4:
        raise RuntimeError("four candidates were not persisted")
    if paused_state.get("unified_reliability_completed") is not True:
        raise RuntimeError("reliability phase did not complete")
    if paused_state.get("unified_review_policy_completed") is not True:
        raise RuntimeError("Critic/Boss policy did not complete")
    if paused_state.get("unified_coherence_completed") is not True:
        raise RuntimeError("coherence validation did not complete")

    paused_context = _require_mapping(
        paused_state,
        "plus_compacted_context",
    )
    pause_fingerprint = paused_context.get("fingerprint")
    pause_context_revision = paused_state.get("plus_context_source_revision")
    critic_report = _require_mapping(paused_state, "critic_report")
    boss_decision = _require_mapping(paused_state, "boss_decision")
    critic_verdict, critic_issues = _critic_evidence(critic_report)
    boss_action, boss_issue_codes = _boss_evidence(boss_decision)
    competition = _require_mapping(
        paused_state,
        "plus_competition_assessment",
    )
    energy = competition.get("energy_snapshot")
    if not isinstance(energy, dict) or not energy.get("snapshot_id"):
        raise RuntimeError("competition Energy snapshot was not persisted")

    async with open_postgres_checkpointer(database_url) as saver:
        resumed = await _service(saver, source_sha=source_sha).resume_human_review(
            estimation_id=estimation_id,
            decision=Session14HumanReviewDecision(
                action="approve",
                expected_revision=1,
                actor="github-actions-unified-evidence",
                idempotency_key=f"unified-{estimation_id}-approve",
            ),
        )

    if resumed.execution_status != "completed":
        raise RuntimeError("unified resume did not complete")
    if resumed.thread_id != paused.thread_id:
        raise RuntimeError("resume changed thread identity")
    resumed_state = resumed.state
    if resumed_state.get("human_review_status") != "approved":
        raise RuntimeError("human approval was not persisted")
    if resumed_state.get("human_review_revision") != 2:
        raise RuntimeError("human review revision did not advance")
    if resumed_state.get("unified_proposal_completed") is not True:
        raise RuntimeError("proposal did not complete after approval")
    if resumed_state.get("unified_phase") != "finalized":
        raise RuntimeError("unified graph did not reach finalized phase")

    resumed_context = _require_mapping(
        resumed_state,
        "plus_compacted_context",
    )
    if resumed_context.get("fingerprint") == pause_fingerprint:
        raise RuntimeError("context fingerprint did not refresh after approval")
    if resumed_state.get("plus_context_source_revision") == pause_context_revision:
        raise RuntimeError("context revision did not advance after approval")
    validation_state = resumed_context.get("validation_state")
    if not isinstance(validation_state, dict):
        raise RuntimeError("resumed validation context is missing")
    if validation_state.get("human_review_status") != "approved":
        raise RuntimeError("resumed context did not retain human approval")

    async with open_postgres_checkpointer(database_url) as saver:
        reread = await _service(saver, source_sha=source_sha).estimate(
            transcript=transcript,
            estimation_id=estimation_id,
        )

    if reread.execution_status != "completed":
        raise RuntimeError("terminal checkpoint was not reread as completed")
    if reread.thread_id != resumed.thread_id:
        raise RuntimeError("terminal reread changed thread identity")
    if reread.state != resumed.state:
        raise RuntimeError("terminal state changed after third lifecycle")

    route_events = resumed_state.get("unified_route_events", [])
    if not isinstance(route_events, list) or not route_events:
        raise RuntimeError("unified route ledger is missing")
    destinations = [
        event.get("destination")
        for event in route_events
        if isinstance(event, dict)
    ]
    authorized = resumed_state.get("plus_authorized_capabilities", {})
    if not isinstance(authorized, dict) or len(authorized) < 5:
        raise RuntimeError("capability authorization evidence is incomplete")

    artifact = {
        "schema_version": "session13_14.unified.postgres-evidence.v2",
        "source_sha": source_sha,
        "fixture_name": TEACHER_FIXTURE.name,
        "estimation_id": str(estimation_id),
        "thread_id": resumed.thread_id,
        "graph_name": UNIFIED_GRAPH_NAME,
        "graph_version": UNIFIED_GRAPH_VERSION,
        "pause_execution_status": paused.execution_status,
        "pause_interrupt_count": len(paused.interrupts),
        "pause_checkpoint_human_review_status": paused_state.get(
            "human_review_status"
        ),
        "resume_execution_status": resumed.execution_status,
        "resume_human_review_status": resumed_state.get(
            "human_review_status"
        ),
        "revision_before": paused_state.get("human_review_revision"),
        "revision_after": resumed_state.get("human_review_revision"),
        "same_thread_resume": True,
        "terminal_reread_equal": True,
        "checkpoint_lifecycles": 3,
        "unified_phase_after": resumed_state.get("unified_phase"),
        "unified_route_destinations": destinations,
        "routing_steps": resumed_state.get("routing_steps"),
        "critic_verdict": critic_verdict,
        "critic_issue_count": len(critic_issues),
        "boss_action": boss_action,
        "boss_issue_code_count": len(boss_issue_codes),
        "boss_route": paused_state.get("boss_route"),
        "competition_candidate_count": len(
            resumed_state.get("plus_competition_candidates", [])
        ),
        "competition_disposition": competition.get("disposition"),
        "competition_energy_snapshot_id": energy.get("snapshot_id"),
        "context_revision_before": pause_context_revision,
        "context_revision_after": resumed_state.get(
            "plus_context_source_revision"
        ),
        "context_fingerprint_before": pause_fingerprint,
        "context_fingerprint_after": resumed_context.get("fingerprint"),
        "authorized_capabilities": authorized,
        "route_plan_id": _require_mapping(
            resumed_state,
            "plus_routing_plan",
        ).get("plan_id"),
        "proposal_completed": resumed_state.get("unified_proposal_completed"),
    }
    artifact_path = Path(
        os.getenv(
            "SESSION13_14_UNIFIED_POSTGRES_EVIDENCE_PATH",
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
