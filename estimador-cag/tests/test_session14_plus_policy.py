from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.session14_plus_policy import (
    ContextCompactionEvent,
    ModelCapabilityRecord,
    Session14ContextSource,
)
from app.schemas.v3_routing import ComplexitySignals
from app.services.session14_plus_policy import (
    build_capability_registry,
    build_context_compaction_event,
    compact_session14_context,
    ensure_context_fresh,
    merge_context_compaction_events,
    validate_routing_plan_capabilities,
)
from app.services.v3_complexity_router import (
    assess_complexity,
    build_model_routing_plan,
)


def _capability(
    *,
    provider: str,
    model: str,
    efforts: list[str],
    supports_tools: bool = True,
    enabled: bool = True,
) -> ModelCapabilityRecord:
    return ModelCapabilityRecord(
        record_id=f"cap:{provider}:{model}",
        provider=provider,
        provider_model_id=model,
        display_name=model,
        capability_tier="test",
        context_window_tokens=1_000_000,
        max_output_tokens=20_000,
        modalities=["text"],
        supports_tools=supports_tools,
        supports_structured_output=True,
        reasoning_efforts=efforts,
        speed_class="deterministic" if provider == "python" else "balanced",
        cost_metadata_version="test-v1",
        lifecycle="contract_verified",
        verified_at=datetime(2026, 7, 1, tzinfo=UTC),
        calibration_status="baseline",
        enabled=enabled,
    )


def _source(**overrides: object) -> Session14ContextSource:
    payload: dict[str, object] = {
        "source_revision": 3,
        "identity": {
            "estimation_id": "EST-14-PLUS",
            "thread_id": "estimate:EST-14-PLUS",
        },
        "objective": "Produce an auditable estimate.",
        "working_mode": "LIDR coursework + Session 14 Plus",
        "hard_constraints": [
            "Python owns arithmetic.",
            "Human review cannot be bypassed.",
        ],
        "accepted_decisions": [f"decision-{index}" for index in range(20)],
        "rejected_alternatives": [f"rejected-{index}" for index in range(8)],
        "evidence_refs": [f"chunk:{index}" for index in range(20)],
        "current_state": {"status": "needs_review", "confidence": 0.61},
        "unresolved_questions": [f"question-{index}" for index in range(10)],
        "execution_budgets": {"routing_steps": 5, "max_routing_steps": 12},
        "provider_route": {"provider": "deepseek", "model": "deepseek-v4-flash"},
        "repository_state": {
            "branch": "gg-session-14/plus",
            "sha": "286ed83f",
        },
        "validation_state": {"ci": "green", "tests": "908 passed"},
        "checkpoint_state": {"revision": 3, "status": "paused"},
        "next_action": "Resume after an authorized decision.",
        "rollback_boundary": "session-14/pre-work",
        "claim_boundary": "No live-provider superiority claim.",
        "recent_events": [f"event-{index}" for index in range(12)],
    }
    payload.update(overrides)
    return Session14ContextSource(**payload)


def test_capability_registry_authorizes_every_primary_route() -> None:
    plan = build_model_routing_plan(
        assess_complexity(ComplexitySignals(requirement_count=3))
    )
    registry = build_capability_registry(
        [
            _capability(
                provider="deepseek",
                model="deepseek-v4-flash",
                efforts=["none", "high"],
            ),
            _capability(
                provider="python",
                model="deterministic-recovery",
                efforts=["none"],
                supports_tools=False,
            ),
        ],
        registry_version="test-registry-v1",
    )

    authorized = validate_routing_plan_capabilities(plan, registry)

    assert set(authorized) == {
        "complexity",
        "structure",
        "recovery",
        "reliability",
        "proposal",
    }
    assert authorized["recovery"] == "cap:python:deterministic-recovery"


def test_capability_registry_rejects_documented_but_disabled_route() -> None:
    plan = build_model_routing_plan(
        assess_complexity(ComplexitySignals(requirement_count=3))
    )
    registry = build_capability_registry(
        [
            _capability(
                provider="deepseek",
                model="deepseek-v4-flash",
                efforts=["none", "high"],
                enabled=False,
            ),
            _capability(
                provider="python",
                model="deterministic-recovery",
                efforts=["none"],
                supports_tools=False,
            ),
        ],
        registry_version="test-registry-v1",
    )

    with pytest.raises(ValueError, match="not enabled"):
        validate_routing_plan_capabilities(plan, registry)


def test_enabled_capability_requires_verified_lifecycle() -> None:
    with pytest.raises(
        ValidationError,
        match="must be contract verified or benchmark calibrated",
    ):
        ModelCapabilityRecord(
            record_id="cap:deepseek:unverified",
            provider="deepseek",
            provider_model_id="unverified",
            display_name="Unverified",
            capability_tier="test",
            context_window_tokens=10_000,
            max_output_tokens=1_000,
            modalities=["text"],
            reasoning_efforts=["none"],
            speed_class="fast",
            cost_metadata_version="test-v1",
            lifecycle="documented",
            enabled=True,
        )


def test_minimal_compaction_preserves_authority_and_has_stable_identity() -> None:
    first = compact_session14_context(
        _source(),
        detail="minimal",
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    second = compact_session14_context(
        _source(),
        detail="minimal",
        created_at=datetime(2026, 7, 2, tzinfo=UTC),
    )

    assert first.context_id == second.context_id
    assert first.fingerprint == second.fingerprint
    assert first.hard_constraints == [
        "Python owns arithmetic.",
        "Human review cannot be bypassed.",
    ]
    assert len(first.accepted_decisions) == 8
    assert len(first.evidence_refs) == 12
    assert first.dropped_item_counts["recent_events"] == 8
    assert first.repository_state["branch"] == "gg-session-14/plus"
    assert first.checkpoint_state["revision"] == 3


def test_compaction_rejects_sensitive_source_fields() -> None:
    source = _source(current_state={"raw_prompt": "do not persist this"})

    with pytest.raises(ValueError, match="sensitive context field"):
        compact_session14_context(source)


def test_compaction_event_replay_is_idempotent_and_conflicts_fail_closed() -> None:
    context = compact_session14_context(_source())
    event = build_context_compaction_event(
        context,
        event_id="EST-14-PLUS:context:3",
    )

    assert merge_context_compaction_events([event], [event]) == [event]

    conflicting = ContextCompactionEvent(
        **{
            **event.model_dump(),
            "fingerprint": "f" * 64,
        }
    )
    with pytest.raises(ValueError, match="conflicting compaction event_id"):
        merge_context_compaction_events([event], [conflicting])


def test_stale_compacted_context_is_rejected_before_resume() -> None:
    context = compact_session14_context(_source(source_revision=3))

    with pytest.raises(ValueError, match="stale"):
        ensure_context_fresh(context, current_source_revision=4)

    ensure_context_fresh(context, current_source_revision=3)
