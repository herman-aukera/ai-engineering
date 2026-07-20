"""Context compaction contracts for EACODE.

Preserves immutable raw events while producing versioned hierarchical summaries,
bounded working windows, and on-demand evidence rehydration. Never replaces raw
source-of-truth with a summary. Never persists hidden chain of thought or secrets.

Spec 0010 runtime — additive module. No live provider calls. Deterministic fixtures.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from energy_core.models import EnergyModel

CompactionProfile = Literal["minimal", "medium", "max"]
LossAuditStatus = Literal["passed", "failed", "not_run"]


class EventRange(EnergyModel):
    """Closed range of source event indices."""

    start: int = Field(ge=0)
    end: int = Field(ge=0)


class ArtifactRef(EnergyModel):
    """Reference to a rehydratable source artifact."""

    artifact_id: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1)
    hash_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    location: str = ""


class DecisionRef(EnergyModel):
    """Reference to an accepted or superseded decision."""

    decision_id: str = Field(min_length=1)
    disposition: str = ""  # accept, repair, reject, escalate
    summary: str = ""


class EvidenceRef(EnergyModel):
    """Reference to an evidence record."""

    evidence_id: str = Field(min_length=1)
    evidence_type: str = ""
    status: str = ""  # pass, fail, missing, conflict


class CompactionRecord(EnergyModel):
    """Versioned hierarchical summary produced by one compaction pass.

    Records what was compacted, what was preserved, and whether a loss
    audit was run after compaction.
    """

    summary_id: str = Field(min_length=1)
    source_event_range: EventRange
    source_hashes: tuple[str, ...] = Field(default_factory=tuple)
    compaction_profile: CompactionProfile = "medium"
    objective: str = ""
    hard_constraints: tuple[str, ...] = Field(default_factory=tuple)
    accepted_decisions: tuple[DecisionRef, ...] = Field(default_factory=tuple)
    superseded_decisions: tuple[DecisionRef, ...] = Field(default_factory=tuple)
    current_state: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    open_questions: tuple[str, ...] = Field(default_factory=tuple)
    risks: tuple[str, ...] = Field(default_factory=tuple)
    next_actions: tuple[str, ...] = Field(default_factory=tuple)
    rehydration_refs: tuple[ArtifactRef, ...] = Field(default_factory=tuple)
    tokens_before: int = Field(default=0, ge=0)
    tokens_after: int = Field(default=0, ge=0)
    loss_audit_status: LossAuditStatus = "not_run"
    created_at: datetime = Field(default_factory=lambda: datetime(2026, 7, 20))
    creator_model_or_rule: str = ""
    # R7 additions per Spec 0010 Slice D
    repository_snapshot_ref: str = ""
    policy_version: str = ""
    schema_version: str = ""
    failing_gates: tuple[str, ...] = Field(default_factory=tuple)
    contradictions: tuple[str, ...] = Field(default_factory=tuple)

    def is_stale(self, *, max_age_days: int = 90) -> bool:
        """Return True if this record is older than max_age_days."""
        from datetime import UTC, datetime as dt
        now = dt.now(UTC)
        age = now - self.created_at.replace(tzinfo=None).replace(tzinfo=UTC) if self.created_at.tzinfo is None else now - self.created_at
        return age.days > max_age_days


class CompactionConfig(EnergyModel):
    """Configuration for compaction triggers and thresholds."""

    profile: CompactionProfile = "medium"
    trigger_threshold_pct: int = Field(default=70, ge=1, le=99)
    release_threshold_pct: int = Field(default=45, ge=1, le=99)
    max_recent_window_tokens: int = Field(default=8_000, ge=512)
    retention_min_summaries: int = Field(default=3, ge=1)

    def should_compact(self, current_tokens: int, provider_budget: int) -> bool:
        """Return True if current usage exceeds the trigger threshold."""
        if provider_budget <= 0:
            return False
        return (current_tokens / provider_budget) * 100 >= self.trigger_threshold_pct

    def compaction_sufficient(self, after_tokens: int, provider_budget: int) -> bool:
        """Return True if after-compaction usage is below the release threshold."""
        if provider_budget <= 0:
            return True
        return (after_tokens / provider_budget) * 100 <= self.release_threshold_pct


# ------------------------------------------------------------------
# Profile-preserved fields per compaction level
# ------------------------------------------------------------------

_MINIMAL_KEEP = frozenset({
    "objective",
    "hard_constraints",
    "current_state",
    "open_questions",
    "next_actions",
})

_MEDIUM_KEEP = _MINIMAL_KEEP | frozenset({
    "accepted_decisions",
    "superseded_decisions",
    "evidence_refs",
    "risks",
    "rehydration_refs",
})

_MAX_KEEP = _MEDIUM_KEEP | frozenset({
    "source_hashes",
    "creator_model_or_rule",
})


# ------------------------------------------------------------------
# Compaction engine
# ------------------------------------------------------------------


class CompactionEngine:
    """Deterministic compaction engine with profile-based preservation.

    Does not call any model. Applies rule-based compaction to a set of
    records, preserving fields required by the active profile.
    """

    def __init__(self, config: CompactionConfig | None = None) -> None:
        self.config = config or CompactionConfig()

    def compact(
        self,
        records: list[CompactionRecord],
        *,
        source_start: int,
        source_end: int,
        current_tokens: int,
        provider_budget: int,
    ) -> CompactionRecord | None:
        """Produce a summary from a range of records.

        Returns None if compaction is not needed (below trigger threshold).
        """
        if not self.config.should_compact(current_tokens, provider_budget):
            return None

        profile = self.config.profile
        keep_fields = _fields_for_profile(profile)

        # Merge decisions from all records in range
        accepted: list[DecisionRef] = []
        superseded: list[DecisionRef] = []
        evidence: list[EvidenceRef] = []
        questions: list[str] = []
        risks: list[str] = []
        actions: list[str] = []
        constraints: list[str] = []
        rehydration: list[ArtifactRef] = []
        source_hashes: list[str] = []
        state: dict[str, Any] = {}

        for rec in records:
            if rec.compaction_profile == "minimal":
                # Minimal records keep only critical state
                pass
            accepted.extend(rec.accepted_decisions)
            superseded.extend(rec.superseded_decisions)
            evidence.extend(rec.evidence_refs)
            questions.extend(rec.open_questions)
            risks.extend(rec.risks)
            actions.extend(rec.next_actions)
            constraints.extend(rec.hard_constraints)
            rehydration.extend(rec.rehydration_refs)
            source_hashes.extend(rec.source_hashes)

        # Deduplicate while preserving order
        accepted_deduped = _dedup_by_id(accepted)
        evidence_deduped = _dedup_by_id(evidence)
        rehydration_deduped = _dedup_by_id(rehydration)

        # Take the last record's state as current
        if records:
            state = dict(records[-1].current_state)

        # Compute summary hash
        summary_payload = {
            "source_start": source_start,
            "source_end": source_end,
            "profile": profile,
            "hard_constraints": sorted(set(constraints)),
            "decisions": [d.decision_id for d in accepted_deduped],
            "evidence": [e.evidence_id for e in evidence_deduped],
        }
        summary_hash = _sha256_json(summary_payload)

        # Contradiction detection: flag conflicting state across records
        contradictions: list[str] = []
        state_keys = set()
        for rec in records:
            for k in rec.current_state:
                if k in state_keys:
                    # Check if values differ
                    for other in records:
                        if other is not rec and k in other.current_state:
                            if rec.current_state[k] != other.current_state[k]:
                                contradictions.append(
                                    f"Conflicting state key '{k}': "
                                    f"'{rec.current_state[k]}' vs '{other.current_state[k]}'"
                                )
                                break
                state_keys.add(k)
        contradictions = list(dict.fromkeys(contradictions))  # deduplicate preserve order

        # Build the compacted record
        compacted = CompactionRecord(
            summary_id=f"compaction-{summary_hash[:16]}",
            source_event_range=EventRange(start=source_start, end=source_end),
            source_hashes=tuple(source_hashes),
            compaction_profile=profile,
            objective=records[-1].objective if records else "",
            hard_constraints=tuple(sorted(set(constraints))) if "hard_constraints" in keep_fields else (),
            accepted_decisions=tuple(accepted_deduped) if "accepted_decisions" in keep_fields else (),
            superseded_decisions=tuple(_dedup_by_id(superseded)) if "superseded_decisions" in keep_fields else (),
            current_state=state if "current_state" in keep_fields else {},
            evidence_refs=tuple(evidence_deduped) if "evidence_refs" in keep_fields else (),
            open_questions=tuple(sorted(set(questions))) if "open_questions" in keep_fields else (),
            risks=tuple(sorted(set(risks))) if "risks" in keep_fields else (),
            next_actions=tuple(actions[-5:]) if "next_actions" in keep_fields else (),
            rehydration_refs=tuple(rehydration_deduped) if "rehydration_refs" in keep_fields else (),
            tokens_before=current_tokens,
            tokens_after=_estimate_tokens_after(profile, current_tokens),
            loss_audit_status="not_run",
            creator_model_or_rule="deterministic-compaction-engine",
            contradictions=tuple(contradictions),
        )

        return compacted


# ------------------------------------------------------------------
# Loss audit
# ------------------------------------------------------------------


class LossAuditor:
    """Deterministic loss auditor that verifies critical fields survived compaction.

    A failed audit invalidates the summary and requires rehydration or a safer profile.
    """

    def audit(
        self,
        compacted: CompactionRecord,
        original_records: list[CompactionRecord],
    ) -> LossAuditStatus:
        """Run a loss audit against the source records.

        Checks that hard constraints, decision IDs, evidence IDs, and
        rehydration references are preserved.
        """
        profile = compacted.compaction_profile

        # Collect expected fields from source records
        source_decisions: set[str] = set()
        source_evidence: set[str] = set()
        source_constraints: set[str] = set()
        source_rehydration: set[str] = set()
        source_questions: set[str] = set()

        for rec in original_records:
            for d in rec.accepted_decisions:
                source_decisions.add(d.decision_id)
            for d in rec.superseded_decisions:
                source_decisions.add(d.decision_id)
            for e in rec.evidence_refs:
                source_evidence.add(e.evidence_id)
            source_constraints.update(rec.hard_constraints)
            for r in rec.rehydration_refs:
                source_rehydration.add(r.artifact_id)

        # Check preserved fields
        compacted_decisions = {d.decision_id for d in compacted.accepted_decisions}
        compacted_decisions |= {d.decision_id for d in compacted.superseded_decisions}
        compacted_evidence = {e.evidence_id for e in compacted.evidence_refs}
        compacted_constraints = set(compacted.hard_constraints)
        compacted_rehydration = {r.artifact_id for r in compacted.rehydration_refs}

        # Hard constraints must always survive
        if "hard_constraints" in _fields_for_profile(profile):
            if not source_constraints.issubset(compacted_constraints):
                return "failed"

        # Decision and evidence refs must survive in medium+
        if profile in ("medium", "max"):
            if source_decisions and not source_decisions.issubset(compacted_decisions):
                return "failed"
            if source_evidence and not source_evidence.issubset(compacted_evidence):
                return "failed"

        # Rehydration refs must survive in medium+
        if profile in ("medium", "max"):
            if source_rehydration and not source_rehydration.issubset(compacted_rehydration):
                return "failed"

        return "passed"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _fields_for_profile(profile: CompactionProfile) -> frozenset[str]:
    if profile == "minimal":
        return _MINIMAL_KEEP
    elif profile == "max":
        return _MAX_KEEP
    return _MEDIUM_KEEP


def _dedup_by_id(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for item in items:
        item_id = getattr(item, "decision_id", None) or getattr(item, "evidence_id", None) or getattr(item, "artifact_id", None) or str(item)
        if item_id not in seen:
            seen.add(item_id)
            result.append(item)
    return result


def _sha256_json(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _estimate_tokens_after(profile: CompactionProfile, tokens_before: int) -> int:
    """Rough token estimate after compaction by profile."""
    ratios = {"minimal": 0.15, "medium": 0.35, "max": 0.60}
    return max(1, int(tokens_before * ratios.get(profile, 0.35)))
