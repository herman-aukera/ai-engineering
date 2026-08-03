from __future__ import annotations

import pytest

from app.generation.graph.unified_state import (
    new_unified_estimation_graph_state,
)
from app.services.graph_estimation import GraphEstimationRun
from app.services.unified_control_projection import (
    unified_control_projection_from_run,
)
from app.ui.unified_control_room import (
    build_review_payload,
    candidate_rows,
    normalize_backend_url,
    route_rows,
    unified_control_url,
    unified_resume_url,
)


def _run() -> GraphEstimationRun:
    state = new_unified_estimation_graph_state(
        transcript="PRIVATE SOURCE REQUEST",
        estimation_id="EST-CONTROL-001",
    )
    state.update(
        status="needs_review",
        review_required=True,
        human_review_status="awaiting_human_review",
        human_review_revision=1,
        human_review_reason_codes=["confidence_below_threshold"],
        unified_phase="human_review",
        unified_route_events=[
            {
                "event_id": "route-1",
                "sequence": 1,
                "destination": "human_review_gate",
                "reason_code": "human_authority_required",
                "summary": "Final authority is human.",
            }
        ],
        critic_report={
            "verdict": "human_required",
            "issues": [
                {
                    "code": "unreliable_estimate",
                    "severity": "major",
                    "state_path": "component_estimates[0]",
                    "explanation": "Evidence confidence requires review.",
                    "evidence_refs": ["budget:BUD-1"],
                    "proposed_repair": "Request human approval.",
                    "repair_scope": "human",
                    "component_ids": ["CMP-1"],
                    "node": "critic",
                }
            ],
            "confidence_in_review": 0.9,
            "summary": "Human authority is required.",
        },
        boss_decision={"action": "human_review", "reason": "Major issue."},
        reliability_report={"overall_score": 0.58},
        plus_competition_candidates=[
            {
                "candidate_id": "candidate:baseline",
                "variant": "baseline",
                "total_hours": 40.0,
                "fingerprint": "a" * 64,
                "components": [],
                "policy_version": "test",
                "assumptions": [],
            }
        ],
        plus_competition_assessment={
            "disposition": "human_review",
            "energy_snapshot": {"snapshot_id": "energy:1"},
        },
        plus_authorized_capabilities={
            "proposal": "benchmark:test:deepseek:flash"
        },
        plus_context_detail="medium",
        plus_context_source_revision=7,
        plus_compacted_context={
            "context_id": "context:1",
            "fingerprint": "b" * 64,
            "evidence_refs": ["budget:BUD-1"],
        },
        proposal={"total_hours": 40.0, "boss_action": "human_review"},
    )
    return GraphEstimationRun(
        estimation_id="EST-CONTROL-001",
        thread_id="estimate:EST-CONTROL-001",
        state=state,
        execution_status="awaiting_human_review",
    )


def test_control_projection_is_allowlisted_and_excludes_source_request() -> None:
    projection = unified_control_projection_from_run(_run())
    serialized = projection.model_dump_json()

    assert projection.unified_phase == "human_review"
    assert projection.route_events[0]["destination"] == "human_review_gate"
    assert projection.context_evidence_refs == ["budget:BUD-1"]
    assert "PRIVATE SOURCE REQUEST" not in serialized
    assert "transcript" not in serialized.lower()
    assert "raw_provider_output" not in serialized.lower()


def test_control_projection_rejects_sensitive_nested_fields() -> None:
    run = _run()
    run.state["critic_report"] = {
        "verdict": "accept",
        "prompt": "must never leave state",
    }

    with pytest.raises(ValueError, match="sensitive field"):
        unified_control_projection_from_run(run)


def test_control_room_builds_exact_urls_and_decision_contract() -> None:
    assert normalize_backend_url("http://localhost:8000/") == (
        "http://localhost:8000"
    )
    assert unified_control_url("http://localhost:8000/").endswith(
        "/api/v1/estimate/graph/unified/control"
    )
    assert unified_resume_url(
        "http://localhost:8000",
        "EST-1",
    ).endswith("/api/v1/estimate/graph/unified/control/EST-1/resume")

    payload = build_review_payload(
        action="approve",
        expected_revision=1,
        actor="reviewer",
        reason=None,
        idempotency_key="decision-1",
    )
    assert payload == {
        "action": "approve",
        "expected_revision": 1,
        "actor": "reviewer",
        "reason": None,
        "adjustments": None,
        "idempotency_key": "decision-1",
    }


def test_control_room_fails_closed_on_incomplete_human_decisions() -> None:
    with pytest.raises(ValueError, match="reject requires"):
        build_review_payload(
            action="reject",
            expected_revision=1,
            actor="reviewer",
            reason="",
        )
    with pytest.raises(ValueError, match="adjust requires"):
        build_review_payload(
            action="adjust",
            expected_revision=1,
            actor="reviewer",
            reason="Fix estimate.",
            adjustments=[],
        )


def test_control_room_rows_are_sanitized_allowlists() -> None:
    projection = _run().state
    projection["competition_candidates"] = projection[
        "plus_competition_candidates"
    ]
    projection["route_events"] = projection["unified_route_events"]

    assert candidate_rows(projection) == [
        {
            "variant": "baseline",
            "candidate_id": "candidate:baseline",
            "total_hours": 40.0,
            "fingerprint": "a" * 64,
        }
    ]
    assert route_rows(projection)[0]["reason_code"] == (
        "human_authority_required"
    )
