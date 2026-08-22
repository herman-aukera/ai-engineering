"""Deterministic acceptance tests for context compaction."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from energy_core.context_compaction import (
    ArtifactRef,
    CompactionRecord,
    DecisionRef,
    EventRange,
    EvidenceRef,
)
from energy_core.context_compaction_guard import (
    CompactionAcceptanceContext,
    require_accepted_compaction,
    validate_compaction_record,
)

SOURCE_HASH = "a" * 64
ARTIFACT_HASH = "b" * 64


def _original(**updates: object) -> CompactionRecord:
    payload: dict[str, object] = {
        "summary_id": "source-record",
        "source_event_range": EventRange(start=0, end=4),
        "source_hashes": (SOURCE_HASH,),
        "compaction_profile": "medium",
        "objective": "Preserve governed execution state.",
        "hard_constraints": ("no self approval",),
        "accepted_decisions": (
            DecisionRef(decision_id="decision-1", disposition="accept"),
        ),
        "evidence_refs": (
            EvidenceRef(evidence_id="evidence-1", status="pass"),
        ),
        "rehydration_refs": (
            ArtifactRef(
                artifact_id="artifact-1",
                artifact_type="event-log",
                hash_sha256=ARTIFACT_HASH,
            ),
        ),
        "created_at": datetime.now(UTC),
        "creator_model_or_rule": "raw-event-projector",
        "repository_snapshot_ref": "snapshot-1",
        "policy_version": "policy-1",
        "schema_version": "schema-1",
    }
    payload.update(updates)
    return CompactionRecord.model_validate(payload)


def _compacted(**updates: object) -> CompactionRecord:
    payload = _original().model_dump(mode="python")
    payload.update(
        {
            "summary_id": "compacted-record",
            "creator_model_or_rule": "deterministic-compaction-engine",
        }
    )
    payload.update(updates)
    return CompactionRecord.model_validate(payload)


def _context(**updates: object) -> CompactionAcceptanceContext:
    payload: dict[str, object] = {
        "repository_snapshot_ref": "snapshot-1",
        "policy_version": "policy-1",
        "schema_version": "schema-1",
        "expected_source_hashes": (SOURCE_HASH,),
        "max_age_days": 90,
        "max_summary_depth": 2,
    }
    payload.update(updates)
    return CompactionAcceptanceContext.model_validate(payload)


def test_valid_compaction_is_accepted_and_marked_audited() -> None:
    compacted = _compacted()
    decision = validate_compaction_record(compacted, [_original()], _context())

    assert decision.accepted is True
    assert decision.loss_audit_status == "passed"
    accepted = require_accepted_compaction(compacted, [_original()], _context())
    assert accepted.loss_audit_status == "passed"


def test_repository_policy_schema_and_source_mismatches_fail_closed() -> None:
    decision = validate_compaction_record(
        _compacted(
            repository_snapshot_ref="wrong",
            policy_version="wrong",
            schema_version="wrong",
            source_hashes=("c" * 64,),
        ),
        [_original()],
        _context(),
    )

    assert decision.accepted is False
    assert set(decision.reasons) >= {
        "repository_snapshot_mismatch",
        "policy_version_mismatch",
        "schema_version_mismatch",
        "source_hash_mismatch",
    }


def test_stale_summary_secrets_and_hidden_reasoning_are_rejected() -> None:
    decision = validate_compaction_record(
        _compacted(
            created_at=datetime.now(UTC) - timedelta(days=365),
            objective=(
                "private scratchpad chain of thought "
                "sk-abcdefghijklmnopqrstuvwxyz123456"  # test-secret-fixture
            ),
        ),
        [_original()],
        _context(),
    )

    assert decision.accepted is False
    assert "summary_stale" in decision.reasons
    assert "secret_detected" in decision.reasons
    assert "hidden_reasoning_detected" in decision.reasons


def test_loss_audit_failure_blocks_use_and_triggers_rehydration() -> None:
    rehydrated: list[str] = []
    compacted = _compacted(hard_constraints=())

    decision = validate_compaction_record(
        compacted,
        [_original()],
        _context(),
        rehydrate=rehydrated.append,
    )

    assert decision.accepted is False
    assert decision.loss_audit_status == "failed"
    assert decision.rehydration_required is True
    assert rehydrated == ["artifact-1"]
    with pytest.raises(PermissionError, match="loss_audit_failed"):
        require_accepted_compaction(compacted, [_original()], _context())


def test_unresolved_contradictions_and_failing_gates_block_use() -> None:
    decision = validate_compaction_record(
        _compacted(
            contradictions=("branch state differs",),
            failing_gates=("pytest",),
        ),
        [_original()],
        _context(),
    )

    assert decision.accepted is False
    assert "unresolved_contradictions" in decision.reasons
    assert "failing_gates_present" in decision.reasons


def test_summary_of_summary_decay_requires_rehydration() -> None:
    source_summary = _original(
        creator_model_or_rule="deterministic-compaction-engine",
        current_state={"_compaction_depth": 2},
    )
    decision = validate_compaction_record(
        _compacted(),
        [source_summary],
        _context(max_summary_depth=2),
    )

    assert decision.accepted is False
    assert "summary_of_summary_decay" in decision.reasons
