"""Deterministic Session 14 Plus provider validation and context compaction."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from app.schemas.session14_plus_policy import (
    CompactedSession14Context,
    ContextCompactionEvent,
    ContextDetail,
    ModelCapabilityRecord,
    ModelCapabilityRegistry,
    Session14ContextSource,
)
from app.schemas.v3_routing import ModelRoutingPlan

_SENSITIVE_KEY_PARTS = (
    "api_key",
    "authorization",
    "dsn",
    "hidden_reasoning",
    "password",
    "prompt",
    "raw_provider_output",
    "secret",
    "token",
    "transcript",
)
_SECRET_VALUE_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|pylf_[A-Za-z0-9_-]{20,}|BEGIN (?:RSA|OPENSSH|PRIVATE) KEY)"
)
_LIST_LIMITS: dict[ContextDetail, dict[str, int | None]] = {
    "minimal": {
        "accepted_decisions": 8,
        "rejected_alternatives": 4,
        "evidence_refs": 12,
        "unresolved_questions": 6,
        "recent_events": 4,
    },
    "medium": {
        "accepted_decisions": 24,
        "rejected_alternatives": 12,
        "evidence_refs": 40,
        "unresolved_questions": 16,
        "recent_events": 16,
    },
    "max": {
        "accepted_decisions": None,
        "rejected_alternatives": None,
        "evidence_refs": None,
        "unresolved_questions": None,
        "recent_events": None,
    },
}


def build_capability_registry(
    records: Sequence[ModelCapabilityRecord],
    *,
    registry_version: str,
    generated_at: datetime | None = None,
) -> ModelCapabilityRegistry:
    """Build a strict registry without promoting documented models to executable."""

    return ModelCapabilityRegistry(
        registry_version=registry_version,
        generated_at=generated_at or datetime.now(UTC),
        records=list(records),
    )


def resolve_capability(
    registry: ModelCapabilityRegistry,
    *,
    provider: str,
    model: str,
) -> ModelCapabilityRecord:
    """Resolve exactly one provider/model record or fail closed."""

    matches = [
        record
        for record in registry.records
        if record.provider == provider and record.provider_model_id == model
    ]
    if not matches:
        raise ValueError(f"unregistered model route: {provider}/{model}")
    return matches[0]


def validate_routing_plan_capabilities(
    plan: ModelRoutingPlan,
    registry: ModelCapabilityRegistry,
) -> dict[str, str]:
    """Authorize every primary route against the injected capability registry."""

    authorized: dict[str, str] = {}
    for stage, route in plan.routes_by_stage.items():
        record = resolve_capability(
            registry,
            provider=route.provider,
            model=route.model,
        )
        if not record.enabled:
            raise ValueError(
                f"model route is not enabled: {route.provider}/{route.model}"
            )
        if route.max_output_tokens > record.max_output_tokens:
            raise ValueError(
                f"route output exceeds capability: {route.provider}/{route.model}"
            )
        if route.mode == "thinking" and route.effort not in record.reasoning_efforts:
            raise ValueError(
                f"unsupported reasoning effort: {route.provider}/{route.model}/{route.effort}"
            )
        if route.tool_call_limit > 0 and not record.supports_tools:
            raise ValueError(
                f"route requires unsupported tools: {route.provider}/{route.model}"
            )
        authorized[stage] = record.record_id
    return authorized


def compact_session14_context(
    source: Session14ContextSource,
    *,
    detail: ContextDetail = "medium",
    created_at: datetime | None = None,
) -> CompactedSession14Context:
    """Create a sanitized, stable context projection at a safe boundary."""

    source_payload = source.model_dump(mode="json")
    _assert_sanitized(source_payload)

    trimmed: dict[str, list[str]] = {}
    dropped: dict[str, int] = {}
    for field_name in (
        "accepted_decisions",
        "rejected_alternatives",
        "evidence_refs",
        "unresolved_questions",
        "recent_events",
    ):
        values = _stable_unique(getattr(source, field_name))
        limit = _LIST_LIMITS[detail][field_name]
        retained = values if limit is None else values[:limit]
        trimmed[field_name] = retained
        dropped[field_name] = len(values) - len(retained)

    canonical = {
        "source_revision": source.source_revision,
        "detail": detail,
        "identity": dict(sorted(source.identity.items())),
        "objective": source.objective.strip(),
        "working_mode": source.working_mode.strip(),
        "hard_constraints": _stable_unique(source.hard_constraints),
        "accepted_decisions": trimmed["accepted_decisions"],
        "rejected_alternatives": trimmed["rejected_alternatives"],
        "evidence_refs": trimmed["evidence_refs"],
        "current_state": dict(sorted(source.current_state.items())),
        "unresolved_questions": trimmed["unresolved_questions"],
        "execution_budgets": dict(sorted(source.execution_budgets.items())),
        "provider_route": dict(sorted(source.provider_route.items())),
        "repository_state": dict(sorted(source.repository_state.items())),
        "validation_state": dict(sorted(source.validation_state.items())),
        "checkpoint_state": dict(sorted(source.checkpoint_state.items())),
        "next_action": source.next_action.strip(),
        "rollback_boundary": source.rollback_boundary.strip(),
        "claim_boundary": source.claim_boundary.strip(),
        "recent_events": trimmed["recent_events"],
        "dropped_item_counts": dropped,
    }
    fingerprint = hashlib.sha256(_canonical_json(canonical).encode()).hexdigest()
    return CompactedSession14Context(
        context_id=f"context:{fingerprint[:24]}",
        fingerprint=fingerprint,
        created_at=created_at or datetime.now(UTC),
        **canonical,
    )


def build_context_compaction_event(
    context: CompactedSession14Context,
    *,
    event_id: str,
) -> ContextCompactionEvent:
    """Build a sanitized audit event without duplicating compacted content."""

    retained_sections = [
        key
        for key, value in context.model_dump(mode="json").items()
        if key
        not in {
            "context_id",
            "created_at",
            "detail",
            "dropped_item_counts",
            "fingerprint",
            "source_revision",
        }
        and value not in ({}, [], "", None)
    ]
    return ContextCompactionEvent(
        event_id=event_id,
        source_revision=context.source_revision,
        detail=context.detail,
        context_id=context.context_id,
        fingerprint=context.fingerprint,
        retained_sections=sorted(retained_sections),
        dropped_item_counts=dict(context.dropped_item_counts),
    )


def merge_context_compaction_events(
    current: Sequence[ContextCompactionEvent],
    incoming: Sequence[ContextCompactionEvent],
) -> list[ContextCompactionEvent]:
    """Deduplicate identical replay and reject conflicting event identifiers."""

    by_id: dict[str, ContextCompactionEvent] = {}
    for event in [*current, *incoming]:
        event_id = event.event_id.strip()
        if not event_id:
            raise ValueError("event_id must not be blank")
        existing = by_id.get(event_id)
        if existing is not None and existing != event:
            raise ValueError(f"conflicting compaction event_id: {event_id}")
        by_id[event_id] = event
    return sorted(
        by_id.values(),
        key=lambda event: (event.source_revision, event.event_id),
    )


def ensure_context_fresh(
    context: CompactedSession14Context,
    *,
    current_source_revision: int,
) -> None:
    """Reject stale derived context before provider switching or resume."""

    if context.source_revision != current_source_revision:
        raise ValueError(
            "compacted context is stale for the current source revision"
        )


def _stable_unique(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = raw_value.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _assert_sanitized(value: object, *, path: str = "context") -> None:
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key).lower()
            if any(part in key for part in _SENSITIVE_KEY_PARTS):
                raise ValueError(f"sensitive context field is forbidden: {path}.{raw_key}")
            _assert_sanitized(item, path=f"{path}.{raw_key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_sanitized(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str) and _SECRET_VALUE_PATTERN.search(value):
        raise ValueError(f"secret-like context value is forbidden: {path}")


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
