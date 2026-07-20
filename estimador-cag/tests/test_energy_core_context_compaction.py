"""Tests for context compaction contracts and engine.

Deterministic — no live API calls, no provider keys required.
"""

from __future__ import annotations

from energy_core.context_compaction import (
    ArtifactRef,
    CompactionConfig,
    CompactionEngine,
    CompactionProfile,
    CompactionRecord,
    DecisionRef,
    EventRange,
    EvidenceRef,
    LossAuditor,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _record(index: int, **overrides) -> CompactionRecord:
    payload = {
        "summary_id": f"summary-{index:03d}",
        "source_event_range": EventRange(start=index, end=index + 1),
        "compaction_profile": "medium",
        "objective": f"Test objective {index}",
        "hard_constraints": ("constraint-a", "constraint-b"),
        "accepted_decisions": (
            DecisionRef(decision_id=f"dec-{index}", disposition="accept", summary="ok"),
        ),
        "evidence_refs": (
            EvidenceRef(evidence_id=f"ev-{index}", evidence_type="test", status="pass"),
        ),
        "open_questions": (f"q-{index}",),
        "risks": (f"risk-{index}",),
        "next_actions": (f"action-{index}",),
        "rehydration_refs": (
            ArtifactRef(
                artifact_id=f"art-{index}",
                artifact_type="log",
                hash_sha256="0" * 64,
            ),
        ),
        "tokens_before": 1000,
        "tokens_after": 350,
    }
    payload.update(overrides)
    return CompactionRecord.model_validate(payload)


def _config(profile: CompactionProfile = "medium") -> CompactionConfig:
    return CompactionConfig(profile=profile)


# ------------------------------------------------------------------
# Contract serialization
# ------------------------------------------------------------------


def test_event_range_round_trips() -> None:
    er = EventRange(start=0, end=10)
    reloaded = EventRange.model_validate(er.model_dump(mode="json"))
    assert reloaded.start == 0
    assert reloaded.end == 10


def test_compaction_record_round_trips() -> None:
    rec = _record(1)
    reloaded = CompactionRecord.model_validate(rec.model_dump(mode="json"))
    assert reloaded.summary_id == "summary-001"
    assert reloaded.compaction_profile == "medium"


# ------------------------------------------------------------------
# CompactionConfig hysteresis
# ------------------------------------------------------------------


def test_should_compact_above_threshold() -> None:
    config = _config()
    assert config.should_compact(8000, 10000) is True  # 80% > 70%


def test_should_not_compact_below_threshold() -> None:
    config = _config()
    assert config.should_compact(5000, 10000) is False  # 50% < 70%


def test_compaction_sufficient_below_release() -> None:
    config = _config()
    assert config.compaction_sufficient(4000, 10000) is True  # 40% < 45%


def test_compaction_not_sufficient_above_release() -> None:
    config = _config()
    assert config.compaction_sufficient(5000, 10000) is False  # 50% > 45%


# ------------------------------------------------------------------
# CompactionEngine
# ------------------------------------------------------------------


def test_compact_below_threshold_returns_none() -> None:
    engine = CompactionEngine(_config())
    result = engine.compact(
        [_record(1)],
        source_start=0, source_end=2,
        current_tokens=5000, provider_budget=10000,
    )
    assert result is None  # Below 70% threshold


def test_compact_above_threshold_produces_summary() -> None:
    engine = CompactionEngine(_config())
    result = engine.compact(
        [_record(1), _record(2)],
        source_start=0, source_end=3,
        current_tokens=8000, provider_budget=10000,
    )
    assert result is not None
    assert result.compaction_profile == "medium"
    assert result.tokens_after < 8000


def test_compact_minimal_drops_evidence_and_decisions() -> None:
    engine = CompactionEngine(_config(profile="minimal"))
    result = engine.compact(
        [_record(1)],
        source_start=0, source_end=2,
        current_tokens=8000, provider_budget=10000,
    )
    assert result is not None
    assert result.accepted_decisions == ()
    assert result.evidence_refs == ()
    assert result.hard_constraints != ()  # Constraints survive minimal


def test_compact_medium_preserves_decisions_and_evidence() -> None:
    engine = CompactionEngine(_config(profile="medium"))
    result = engine.compact(
        [_record(1)],
        source_start=0, source_end=2,
        current_tokens=8000, provider_budget=10000,
    )
    assert result is not None
    assert len(result.accepted_decisions) > 0
    assert len(result.evidence_refs) > 0


def test_compact_preserves_last_record_state() -> None:
    engine = CompactionEngine(_config())
    records = [
        _record(1, current_state={"phase": "start"}),
        _record(2, current_state={"phase": "end"}),
    ]
    result = engine.compact(
        records, source_start=0, source_end=3,
        current_tokens=8000, provider_budget=10000,
    )
    assert result is not None
    assert result.current_state == {"phase": "end"}


# ------------------------------------------------------------------
# Deduplication
# ------------------------------------------------------------------


def test_compact_deduplicates_decisions() -> None:
    engine = CompactionEngine(_config())
    dec = DecisionRef(decision_id="dec-shared", disposition="accept", summary="ok")
    r1 = _record(1, accepted_decisions=(dec,))
    r2 = _record(2, accepted_decisions=(dec,))
    result = engine.compact(
        [r1, r2], source_start=0, source_end=3,
        current_tokens=8000, provider_budget=10000,
    )
    assert result is not None
    # Same decision should appear only once
    decision_ids = [d.decision_id for d in result.accepted_decisions]
    assert decision_ids.count("dec-shared") == 1


# ------------------------------------------------------------------
# Loss auditor
# ------------------------------------------------------------------


def test_audit_passes_when_all_preserved() -> None:
    auditor = LossAuditor()
    original = [_record(1)]
    engine = CompactionEngine(_config(profile="medium"))
    compacted = engine.compact(
        original, source_start=0, source_end=2,
        current_tokens=8000, provider_budget=10000,
    )
    assert compacted is not None
    status = auditor.audit(compacted, original)
    assert status == "passed"


def test_audit_fails_when_constraint_missing() -> None:
    auditor = LossAuditor()
    original = [_record(1)]
    compacted = _record(1, hard_constraints=())  # Dropped constraints
    status = auditor.audit(compacted, original)
    assert status == "failed"


def test_audit_fails_when_decision_missing() -> None:
    auditor = LossAuditor()
    original = [_record(1)]
    compacted = _record(1, accepted_decisions=())  # Dropped decisions
    status = auditor.audit(compacted, original)
    assert status == "failed"


def test_audit_passes_for_minimal_profile_skipping_decisions() -> None:
    """Minimal profile doesn't preserve decisions, so missing decisions is OK."""
    auditor = LossAuditor()
    original = [_record(1)]
    compacted = _record(1, compaction_profile="minimal", accepted_decisions=())
    status = auditor.audit(compacted, original)
    assert status == "passed"  # Minimal doesn't require decisions


# ------------------------------------------------------------------
# R7 — Missing features from Spec 0010 Slice D (EXPECTED FAILURES)
# ------------------------------------------------------------------


def test_compaction_record_has_repository_snapshot_ref() -> None:
    """CompactionRecord must carry repository_snapshot_ref for freshness."""
    rec = CompactionRecord(
        summary_id="test",
        source_event_range=EventRange(start=0, end=1),
        repository_snapshot_ref="abc123",
    )
    assert rec.repository_snapshot_ref == "abc123"


def test_compaction_record_has_policy_and_schema_versions() -> None:
    """CompactionRecord must carry policy_version and schema_version."""
    rec = CompactionRecord(
        summary_id="test",
        source_event_range=EventRange(start=0, end=1),
        policy_version="1.0.0",
        schema_version="1.0.0",
    )
    assert rec.policy_version == "1.0.0"
    assert rec.schema_version == "1.0.0"


def test_compaction_record_has_failing_gates() -> None:
    """CompactionRecord must preserve failing gates."""
    rec = CompactionRecord(
        summary_id="test",
        source_event_range=EventRange(start=0, end=1),
        failing_gates=("ruff", "test_symlink"),
    )
    assert "ruff" in rec.failing_gates


def test_contradiction_detection() -> None:
    """Engine must detect when summaries contradict each other."""
    engine = CompactionEngine(_config())
    # Two records with contradictory decisions
    r1 = _record(1, current_state={"status": "pass"})
    r2 = _record(2, current_state={"status": "fail"})
    result = engine.compact(
        [r1, r2], source_start=0, source_end=3,
        current_tokens=8000, provider_budget=10000,
    )
    assert result is not None
    assert len(result.contradictions) > 0, "Contradicting state must be flagged"


def test_staleness_detection() -> None:
    """CompactionRecord staleness must be detectable."""
    from datetime import UTC, datetime

    old = _record(1, created_at=datetime(2020, 1, 1, tzinfo=UTC))
    assert old.is_stale() is True, "Record from 2020 must be stale"


def test_deterministic_minimal_fixture() -> None:
    """Minimal compaction must produce deterministic output for same input."""
    engine = CompactionEngine(_config(profile="minimal"))
    recs = [_record(1)]
    r1 = engine.compact(recs, source_start=0, source_end=2, current_tokens=8000, provider_budget=10000)
    r2 = engine.compact(recs, source_start=0, source_end=2, current_tokens=8000, provider_budget=10000)
    assert r1.model_dump(mode="json") == r2.model_dump(mode="json")


def test_deterministic_max_fixture() -> None:
    """Max compaction must produce deterministic output for same input."""
    engine = CompactionEngine(_config(profile="max"))
    recs = [_record(1)]
    r1 = engine.compact(recs, source_start=0, source_end=2, current_tokens=8000, provider_budget=10000)
    r2 = engine.compact(recs, source_start=0, source_end=2, current_tokens=8000, provider_budget=10000)
    assert r1.model_dump(mode="json") == r2.model_dump(mode="json")
