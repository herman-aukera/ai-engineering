"""Fail-closed acceptance guard for EACODE context compaction."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from pydantic import Field

from energy_core.context_compaction import (
    CompactionRecord,
    LossAuditor,
)
from energy_core.models import EnergyModel

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE),
    re.compile(r"BEGIN (?:RSA|OPENSSH|PRIVATE) KEY"),
)
_HIDDEN_REASONING_MARKERS = (
    "chain of thought",
    "hidden reasoning",
    "private scratchpad",
    "internal monologue",
)


class CompactionAcceptanceContext(EnergyModel):
    """Current authority and freshness facts for one compaction decision."""

    repository_snapshot_ref: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    expected_source_hashes: tuple[str, ...] = Field(default_factory=tuple)
    max_age_days: int = Field(default=90, ge=0)
    max_summary_depth: int = Field(default=2, ge=0)


class CompactionAcceptanceDecision(EnergyModel):
    """Deterministic acceptance result; summaries never self-authorize."""

    accepted: bool = False
    reasons: tuple[str, ...] = Field(default_factory=tuple)
    loss_audit_status: str = "not_run"
    rehydration_required: bool = False
    rehydrated_artifact_ids: tuple[str, ...] = Field(default_factory=tuple)


Rehydrate = Callable[[str], Any]


def validate_compaction_record(
    compacted: CompactionRecord,
    original_records: list[CompactionRecord],
    context: CompactionAcceptanceContext,
    *,
    rehydrate: Rehydrate | None = None,
) -> CompactionAcceptanceDecision:
    """Validate a compacted record against current authority and raw sources."""

    reasons: list[str] = []

    if compacted.repository_snapshot_ref != context.repository_snapshot_ref:
        reasons.append("repository_snapshot_mismatch")
    if compacted.policy_version != context.policy_version:
        reasons.append("policy_version_mismatch")
    if compacted.schema_version != context.schema_version:
        reasons.append("schema_version_mismatch")
    if compacted.is_stale(max_age_days=context.max_age_days):
        reasons.append("summary_stale")

    expected_hashes = set(context.expected_source_hashes)
    actual_hashes = set(compacted.source_hashes)
    if expected_hashes and expected_hashes != actual_hashes:
        reasons.append("source_hash_mismatch")

    if compacted.failing_gates:
        reasons.append("failing_gates_present")
    if compacted.contradictions:
        reasons.append("unresolved_contradictions")

    serialized = json.dumps(compacted.model_dump(mode="json"), sort_keys=True)
    if any(pattern.search(serialized) for pattern in _SECRET_PATTERNS):
        reasons.append("secret_detected")
    lowered = serialized.lower()
    if any(marker in lowered for marker in _HIDDEN_REASONING_MARKERS):
        reasons.append("hidden_reasoning_detected")

    summary_depth = _summary_depth(original_records)
    if summary_depth > context.max_summary_depth:
        reasons.append("summary_of_summary_decay")

    loss_status = LossAuditor().audit(compacted, original_records)
    if loss_status != "passed":
        reasons.append("loss_audit_failed")

    rehydration_required = bool(reasons)
    rehydrated: list[str] = []
    if rehydration_required and rehydrate is not None:
        for reference in compacted.rehydration_refs:
            rehydrate(reference.artifact_id)
            rehydrated.append(reference.artifact_id)

    return CompactionAcceptanceDecision(
        accepted=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
        loss_audit_status=loss_status,
        rehydration_required=rehydration_required,
        rehydrated_artifact_ids=tuple(rehydrated),
    )


def require_accepted_compaction(
    compacted: CompactionRecord,
    original_records: list[CompactionRecord],
    context: CompactionAcceptanceContext,
    *,
    rehydrate: Rehydrate | None = None,
) -> CompactionRecord:
    """Return the summary only when every deterministic acceptance gate passes."""

    decision = validate_compaction_record(
        compacted,
        original_records,
        context,
        rehydrate=rehydrate,
    )
    if not decision.accepted:
        joined = ",".join(decision.reasons)
        raise PermissionError(f"Compaction rejected: {joined}")
    return compacted.model_copy(update={"loss_audit_status": "passed"})


def _summary_depth(records: list[CompactionRecord]) -> int:
    depth = 0
    for record in records:
        value = record.current_state.get("_compaction_depth", 0)
        if isinstance(value, int):
            depth = max(depth, value)
        if record.creator_model_or_rule == "deterministic-compaction-engine":
            depth = max(depth, 1)
    return depth + 1 if records else 0
