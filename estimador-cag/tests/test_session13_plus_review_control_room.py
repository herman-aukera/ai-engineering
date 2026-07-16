from __future__ import annotations

import json

import pytest

from app.ui.review_control_room import (
    build_final_resume_payload,
    build_structure_resume_payload,
    pending_final_review,
    pending_structure_review,
    reviewed_response_to_graph_payload,
)


def _paused_response() -> dict:
    return {
        "execution_status": "paused",
        "estimation_id": "11111111-1111-4111-8111-111111111111",
        "thread_id": "estimate:11111111-1111-4111-8111-111111111111",
        "graph_version": "session13.plus.v1",
        "graph_status": "pending",
        "review_required": False,
        "human_review_mode": "required",
        "structure_review_revision": 0,
        "structure_review_status": None,
        "next_nodes": ["structure_review"],
        "interrupts": [
            {
                "id": "interrupt-1",
                "value": {
                    "gate": "structure_review",
                    "revision": 0,
                    "requirements": [
                        {"requirement_id": "req-1", "text": "Use JWT."}
                    ],
                    "components": [
                        {
                            "component_id": "cmp-auth",
                            "name": "Authentication",
                            "category": "backend",
                            "requirement_ids": ["req-1"],
                        }
                    ],
                },
            }
        ],
        "state": {
            "estimation_id": "11111111-1111-4111-8111-111111111111",
            "graph_version": "session13.plus.v1",
            "status": "pending",
            "requirements": [],
            "components": [],
            "budget_matches": [],
            "component_estimates": [],
            "errors": [],
            "trace_events": [],
            "provider_metadata": {},
            "execution_metadata": {},
        },
    }


def test_pending_structure_review_extracts_gate_payload() -> None:
    payload = pending_structure_review(_paused_response())

    assert payload is not None
    assert payload["gate"] == "structure_review"
    assert payload["revision"] == 0
    assert payload["components"][0]["component_id"] == "cmp-auth"


def test_pending_structure_review_ignores_unrelated_interrupts() -> None:
    response = _paused_response()
    response["interrupts"] = [{"id": "x", "value": {"gate": "estimate_review"}}]

    assert pending_structure_review(response) is None


def test_reviewed_response_flattens_state_for_graph_inspector() -> None:
    payload = reviewed_response_to_graph_payload(_paused_response())

    assert payload["estimation_id"] == "11111111-1111-4111-8111-111111111111"
    assert payload["thread_id"].startswith("estimate:")
    assert payload["graph_version"] == "session13.plus.v1"
    assert payload["status"] == "pending"
    assert payload["review_required"] is False


def test_approve_resume_payload_contains_only_strict_fields() -> None:
    payload = build_structure_resume_payload(
        action="approve",
        expected_revision=3,
    )

    assert payload == {
        "action": "approve",
        "expected_revision": 3,
    }


def test_edit_resume_payload_parses_human_changes() -> None:
    payload = build_structure_resume_payload(
        action="edit",
        expected_revision=1,
        reason="Split the identity scope.",
        requirements_json=json.dumps(
            [{"requirement_id": "req-1", "text": "Use OAuth2."}]
        ),
        components_json=json.dumps(
            [
                {
                    "component_id": "cmp-identity",
                    "name": "Identity",
                    "category": "backend",
                    "requirement_ids": ["req-1"],
                }
            ]
        ),
    )

    assert payload["action"] == "edit"
    assert payload["expected_revision"] == 1
    assert payload["reason"] == "Split the identity scope."
    assert payload["requirements"][0]["text"] == "Use OAuth2."
    assert payload["components"][0]["component_id"] == "cmp-identity"


def test_edit_resume_payload_rejects_non_list_json() -> None:
    with pytest.raises(ValueError, match="requirements must be a JSON array"):
        build_structure_resume_payload(
            action="edit",
            expected_revision=0,
            requirements_json='{"requirement_id": "req-1"}',
            components_json="[]",
        )


def test_pending_final_review_extracts_final_gate() -> None:
    response = _paused_response()
    response["interrupts"] = [
        {"id": "final-1", "value": {"gate": "final_estimate_review", "revision": 2}}
    ]
    assert pending_final_review(response) == {
        "gate": "final_estimate_review",
        "revision": 2,
    }


def test_final_override_payload_preserves_typed_human_evidence() -> None:
    payload = build_final_resume_payload(
        action="override",
        expected_revision=2,
        actor=" lead@example.com ",
        reason="Accepted discovery baseline.",
        overrides_json=json.dumps(
            [{"component_id": "CMP-1", "hours": 52, "evidence_refs": ["NOTE-7"]}]
        ),
    )
    assert payload == {
        "action": "override",
        "expected_revision": 2,
        "actor": "lead@example.com",
        "reason": "Accepted discovery baseline.",
        "overrides": [
            {"component_id": "CMP-1", "hours": 52, "evidence_refs": ["NOTE-7"]}
        ],
    }
