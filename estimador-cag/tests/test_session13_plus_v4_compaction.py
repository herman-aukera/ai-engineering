"""Tests for Session 13 Plus S4: context-compaction runtime."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# 1. CompactionMetadata schema
# ---------------------------------------------------------------------------

def test_compaction_metadata_is_frozen_and_checkpoint_safe() -> None:
    """CompactionMetadata must round-trip through model_dump(mode='json')."""
    from app.schemas.v4_compaction import CompactionMetadata

    meta = CompactionMetadata(
        original_token_estimate=5_000,
        compacted_token_estimate=1_200,
        compaction_level="minimal",
        compaction_version="session13-v4-compaction-1.0.0",
    )
    payload = meta.model_dump(mode="json")
    assert payload["original_token_estimate"] == 5_000
    assert payload["compacted_token_estimate"] == 1_200
    assert payload["compaction_level"] == "minimal"


def test_compaction_metadata_rejects_invalid_level() -> None:
    """compaction_level must be minimal, medium, or max."""
    from app.schemas.v4_compaction import CompactionMetadata

    with pytest.raises(ValidationError):
        CompactionMetadata(
            original_token_estimate=100,
            compacted_token_estimate=50,
            compaction_level="aggressive",
            compaction_version="test",
        )


# ---------------------------------------------------------------------------
# 2. Minimal compaction — preserves canonical required fields
# ---------------------------------------------------------------------------

def test_minimal_compaction_preserves_identity_and_authority() -> None:
    """Minimal compaction must retain estimation_id, graph_version, status, review_required."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    result = compact_context(state, level="minimal")

    assert result["estimation_id"] == "11111111-1111-4111-8111-111111111111"
    assert result["graph_version"] == "session13.plus.v1"
    assert result["status"] == "validated"
    assert result["review_required"] is False


def test_minimal_compaction_preserves_boss_and_critic_summary() -> None:
    """Minimal compaction keeps boss_decision.action and critic_report.verdict."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    result = compact_context(state, level="minimal")

    assert result["boss_decision"]["action"] == "accept"
    assert result["critic_report"]["verdict"] == "accept"


def test_minimal_compaction_preserves_estimate_totals_only() -> None:
    """Minimal compaction keeps estimate totals but drops component details."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    result = compact_context(state, level="minimal")

    assert result["estimate"]["total_hours"] == 40.0
    # Component-level detail must be dropped.
    assert "component_estimates" not in result
    assert "components" not in result


def test_minimal_compaction_preserves_classifier_results() -> None:
    """Minimal compaction keeps classifier level and arbitration resolution."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    result = compact_context(state, level="minimal")

    assert result["semantic_assessment"]["level"] == "C1"
    assert result["arbitrated_assessment"]["arbitrated_level"] is not None
    assert result["v3_route_plan"]["plan_id"] is not None


def test_minimal_compaction_trims_large_text_fields() -> None:
    """Minimal compaction trims transcript/reformulated_request to first 500 chars."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    # Add a long transcript.
    state["transcript"] = "A" * 2_000
    state["reformulated_request"] = "B" * 2_000

    result = compact_context(state, level="minimal")

    assert len(result["transcript"]) <= 500
    assert len(result["reformulated_request"]) <= 500


def test_minimal_compaction_limits_trace_events() -> None:
    """Minimal compaction keeps only the last 3 trace events."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    state["trace_events"] = [
        {"event_type": f"event_{i}", "node": "test", "summary": str(i),
         "evidence_refs": [], "state_delta_keys": []}
        for i in range(10)
    ]
    result = compact_context(state, level="minimal")

    assert len(result["trace_events"]) <= 3
    # The last events must be preserved.
    assert result["trace_events"][-1]["event_type"] == "event_9"


def test_minimal_compaction_adds_compaction_metadata() -> None:
    """Every compaction result must carry its own metadata record."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    result = compact_context(state, level="minimal")

    assert "compaction_metadata" in result
    meta = result["compaction_metadata"]
    assert meta["compaction_level"] == "minimal"
    assert meta["original_token_estimate"] > 0
    assert meta["compacted_token_estimate"] > 0
    assert meta["compacted_token_estimate"] <= meta["original_token_estimate"]


# ---------------------------------------------------------------------------
# 3. Medium compaction — balanced default
# ---------------------------------------------------------------------------

def test_medium_compaction_preserves_structured_data() -> None:
    """Medium compaction keeps component_estimates and components."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    result = compact_context(state, level="medium")

    assert "component_estimates" in result
    assert "components" in result
    assert "budget_matches" in result


def test_medium_compaction_limits_trace_events() -> None:
    """Medium compaction keeps last 10 trace events."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    state["trace_events"] = [
        {"event_type": f"event_{i}", "node": "test", "summary": str(i),
         "evidence_refs": [], "state_delta_keys": []}
        for i in range(20)
    ]
    result = compact_context(state, level="medium")

    assert len(result["trace_events"]) <= 10


# ---------------------------------------------------------------------------
# 4. Max compaction — preserve the most detail
# ---------------------------------------------------------------------------

def test_max_compaction_preserves_everything() -> None:
    """Max compaction must preserve all present keys plus metadata."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    result = compact_context(state, level="max")

    # All original keys must still be present (plus compaction_metadata).
    for key in state:
        assert key in result
    assert "compaction_metadata" in result


# ---------------------------------------------------------------------------
# 5. Idempotency and safety
# ---------------------------------------------------------------------------

def test_compaction_is_idempotent() -> None:
    """Compacting an already-compacted state must not change it further."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    first = compact_context(state, level="minimal")
    second = compact_context(first, level="minimal")

    assert first == second


def test_compaction_drops_errors_in_minimal_mode() -> None:
    """Minimal compaction drops detailed errors list."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    state["errors"] = [
        {"code": "err_1", "message": "x" * 100, "node": "test", "severity": "warning"},
        {"code": "err_2", "message": "y" * 100, "node": "test", "severity": "error"},
    ]
    result = compact_context(state, level="minimal")

    assert "errors" not in result


def test_compaction_never_creates_keys() -> None:
    """Compaction must never fabricate keys that were absent from the input."""
    from app.services.v4_compaction import compact_context

    state = {
        "estimation_id": "test-1",
        "graph_version": "v1",
        "transcript": "Hello.",
    }
    result = compact_context(state, level="max")

    # Only the keys we put in plus compaction_metadata must be present.
    allowed = {"estimation_id", "graph_version", "transcript", "compaction_metadata"}
    assert set(result.keys()) == allowed


# ---------------------------------------------------------------------------
# 6. R5 — source fingerprint and freshness
# ---------------------------------------------------------------------------

def test_compaction_metadata_includes_source_fingerprint() -> None:
    """Every compaction must record a source_fingerprint of the original state."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    result = compact_context(state, level="minimal")

    meta = result["compaction_metadata"]
    assert "source_fingerprint" in meta
    fingerprint = meta["source_fingerprint"]
    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 64  # SHA-256 hex


def test_compaction_fingerprint_is_deterministic() -> None:
    """Same state produces the same fingerprint."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    a = compact_context(state, level="medium")
    b = compact_context(dict(state), level="medium")

    assert a["compaction_metadata"]["source_fingerprint"] == b["compaction_metadata"]["source_fingerprint"]


def test_stale_compaction_is_detected() -> None:
    """A compacted state that no longer matches source must be detected as stale."""
    from app.services.v4_compaction import compact_context, is_compaction_stale

    original = _full_state()
    compacted = compact_context(original, level="minimal")

    # Not stale — fingerprint matches.
    assert is_compaction_stale(original, compacted) is False

    # Modify the original — now stale.
    original["estimate"]["total_hours"] = 999.0
    assert is_compaction_stale(original, compacted) is True


def test_forced_recompaction_allows_re_compacting() -> None:
    """force=True must allow re-compacting an already-compacted state."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    first = compact_context(state, level="minimal")
    # Without force, this is idempotent (returns same).
    second_no_force = compact_context(first, level="minimal")
    assert first == second_no_force

    # With force, it must re-compact and produce a fresh metadata record.
    second_forced = compact_context(first, level="minimal", force=True)
    assert second_forced["compaction_metadata"] != first["compaction_metadata"]


def test_compaction_preserves_hard_constraints_when_present() -> None:
    """If hard_constraints is in state, minimal compaction must preserve it."""
    from app.services.v4_compaction import compact_context

    state = _full_state()
    state["hard_constraints"] = ["C5 lock", "no model-authored arithmetic"]
    result = compact_context(state, level="minimal")

    assert "hard_constraints" in result
    assert result["hard_constraints"] == state["hard_constraints"]


def test_compaction_does_not_alias_input() -> None:
    """Modifying the compacted result must not affect the original state."""
    from copy import deepcopy

    from app.services.v4_compaction import compact_context

    original = _full_state()
    original_copy = deepcopy(original)
    result = compact_context(original, level="max")

    # Modify the result — must not affect original.
    result["transcript"] = "MODIFIED"
    assert original["transcript"] == original_copy["transcript"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _full_state() -> dict[str, object]:
    """Return a realistic reviewed-graph state dict for compaction tests."""
    return {
        "transcript": "Build a secure FastAPI onboarding platform with PostgreSQL.",
        "reformulated_request": "Project type: web\nRequest: Build onboarding.",
        "estimation_id": "11111111-1111-4111-8111-111111111111",
        "graph_version": "session13.plus.v1",
        "status": "validated",
        "review_required": False,
        "requirements": [
            {"requirement_id": "req-1", "text": "Authenticate users with JWT."},
            {"requirement_id": "req-2", "text": "Persist accounts in PostgreSQL."},
        ],
        "components": [
            {
                "component_id": "cmp-auth",
                "name": "Authentication",
                "category": "backend",
                "requirement_ids": ["req-1", "req-2"],
            }
        ],
        "budget_matches": [
            {
                "component_id": "cmp-auth",
                "budget_id": "BUD-101",
                "reference_component_id": "REF-1",
                "source_document_id": "DOC-10",
                "source_chunk_id": "CH-101",
                "recorded_hours": 40.0,
                "distance": 0.08,
                "score": 0.92,
                "retrieval_method": "hybrid",
            }
        ],
        "component_estimates": [
            {
                "component_id": "cmp-auth",
                "name": "Authentication",
                "hours": 40.0,
                "grounding_status": "grounded",
                "reference_budget_ids": ["BUD-101"],
                "reference_component_ids": ["REF-1"],
                "source_hours": [40.0],
                "source_range_low": 40.0,
                "source_range_high": 40.0,
                "dispersion": 0.0,
                "confidence": 0.75,
                "derivation_method": "median_recorded_hours",
                "review_reasons": [],
            }
        ],
        "estimate": {
            "components": [],
            "subtotal_hours": 40.0,
            "contingency_hours": 0.0,
            "total_hours": 40.0,
            "total_cost_eur": 4000.0,
            "currency": "EUR",
        },
        "errors": [],
        "trace_events": [
            {
                "event_type": "semantic_classification_completed",
                "node": "semantic_classify",
                "summary": "Classified.",
                "evidence_refs": [],
                "state_delta_keys": [],
            }
        ],
        "critic_report": {
            "verdict": "accept",
            "issues": [],
            "confidence_in_review": 1.0,
            "summary": "No issues.",
        },
        "boss_decision": {
            "action": "accept",
            "reason": "Clean.",
            "issue_codes": [],
        },
        "semantic_assessment": {
            "level": "C1",
            "confidence": 0.8,
            "signals": {"domain_category": "web", "primary_modality": "text",
                         "transcript_quality": "well_structured"},
            "rationale": "Simple web app.",
            "classifier_version": "session13-v3-semantic-fake-1.0.0",
        },
        "v3_complexity": {
            "level": "C1",
            "score": 5,
            "confidence": 0.95,
            "dimensions": {},
            "classifier_version": "deterministic-1.0.0",
        },
        "arbitrated_assessment": {
            "arbitrated_level": "C1",
            "resolution": "consensus",
            "resolution_reason": "Both agree.",
            "human_review_required": False,
            "deterministic_assessment_ref": "det-1",
            "semantic_assessment_ref": "sem-1",
        },
        "v3_route_plan": {
            "plan_id": "route-plan:abc123",
            "policy_version": "v1",
            "calibration_dataset_version": "v1",
            "profile": "balanced",
            "routes_by_stage": {},
        },
        "execution_budgets": {
            "retry_count": 0, "retry_limit": 2,
        },
    }
