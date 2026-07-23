from __future__ import annotations

import json

from app.services.audit_export import build_estimation_audit_packet


def test_audit_packet_contains_decisions_provenance_lineage_and_limit() -> None:
    packet = build_estimation_audit_packet(
        {
            "estimation_id": "E-1",
            "graph_version": "plus",
            "scenario_id": "enterprise",
            "parent_estimation_id": "E-0",
            "parent_checkpoint_id": "CP-0",
            "status": "validated",
            "estimate": {"total_hours": 52.0},
            "budget_matches": [{"budget_id": "BUD-1"}],
            "critic_report": {"verdict": "accept"},
            "boss_decision": {"action": "accept"},
            "structure_review_record": {"action": "approve"},
            "final_review_record": {"action": "override", "actor": "lead"},
        },
        thread_id="estimate:E-1",
        checkpoint_id="CP-9",
        limitations=["Live proof pending."],
    )
    assert packet["identity"]["checkpoint_id"] == "CP-9"
    assert packet["identity"]["parent_checkpoint_id"] == "CP-0"
    assert packet["provenance"] == [{"budget_id": "BUD-1"}]
    assert packet["human_decisions"]["final"]["actor"] == "lead"
    assert packet["limitations"] == ["Live proof pending."]


def test_audit_packet_excludes_transcript_prompts_and_secrets() -> None:
    packet = build_estimation_audit_packet(
        {
            "estimation_id": "E-1",
            "transcript": "private transcript",
            "prompt": "hidden prompt",
            "api_key": "secret-key",
            "provider_metadata": {"provider": "deepseek", "model": "test"},
        },
        thread_id="estimate:E-1",
        checkpoint_id="CP-1",
    )
    serialized = json.dumps(packet)
    assert "private transcript" not in serialized
    assert "hidden prompt" not in serialized
    assert "secret-key" not in serialized
    assert packet["execution"]["provider"] == {
        "provider": "deepseek",
        "model": "test",
    }
