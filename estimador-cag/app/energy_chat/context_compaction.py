"""Versioned context compaction and bounded orchestration contracts for EACHAT."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

ContextProfile = Literal["minimal", "balanced", "max"]
OrchestrationMode = Literal["single", "critic", "committee", "adaptive"]
RuntimeMaturity = Literal["contract_only", "implemented"]


class ContextCompactionPolicy(BaseModel):
    """Explicit deterministic retention rules for conversation context."""

    profile: ContextProfile
    target_input_tokens: int = Field(ge=1)
    recent_raw_turns: int = Field(ge=0)
    preserve_pinned_facts: bool = True
    preserve_evidence_refs: bool = True
    preserve_ledger_refs: bool = True
    preserve_open_questions: bool = True
    preserve_failures: bool = True
    preserve_exact_identifiers: bool = True
    summarizer_profile: str = "balanced"
    max_summary_depth: int = Field(default=1, ge=1)
    drift_check_enabled: bool = True


class ContextSnapshot(BaseModel):
    """Versioned context projection linked to its exact source revision range."""

    snapshot_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    revision: int = Field(ge=0)
    profile: ContextProfile
    source_start_revision: int = Field(ge=0)
    source_end_revision: int = Field(ge=0)
    summary_text: str = ""
    pinned_facts: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    accepted_decisions: list[str] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    ledger_entry_ids: list[str] = Field(default_factory=list)
    token_count_before: int = Field(default=0, ge=0)
    token_count_after: int = Field(default=0, ge=0)
    source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    summary_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    limitations: list[str] = Field(default_factory=list)


POLICY_MINIMAL = ContextCompactionPolicy(
    profile="minimal",
    target_input_tokens=4_000,
    recent_raw_turns=2,
    summarizer_profile="deterministic",
    max_summary_depth=1,
)

POLICY_BALANCED = ContextCompactionPolicy(
    profile="balanced",
    target_input_tokens=16_000,
    recent_raw_turns=8,
    summarizer_profile="deterministic",
    max_summary_depth=1,
)

POLICY_MAX = ContextCompactionPolicy(
    profile="max",
    target_input_tokens=64_000,
    recent_raw_turns=24,
    summarizer_profile="deterministic",
    max_summary_depth=1,
)


def resolve_compaction_policy(profile: ContextProfile) -> ContextCompactionPolicy:
    """Return the active deterministic policy for a public context profile."""

    return {
        "minimal": POLICY_MINIMAL,
        "balanced": POLICY_BALANCED,
        "max": POLICY_MAX,
    }[profile]


def build_context_snapshot(
    *,
    conversation_id: str,
    revision: int,
    turns: list[Any],
    profile: ContextProfile,
) -> ContextSnapshot:
    """Build a bounded, hash-linked projection without model-generated summaries."""

    policy = resolve_compaction_policy(profile)
    source_payload = [
        {
            "turn_id": turn.turn_id,
            "turn_index": turn.turn_index,
            "graph_thread_id": turn.graph_thread_id,
            "request_fingerprint": turn.request_fingerprint,
            "user_message": turn.user_message,
            "assistant_message": turn.assistant_message,
            "required_constraints": list(getattr(turn, "required_constraints", [])),
            "required_sections": list(getattr(turn, "required_sections", [])),
            "disposition": turn.graph_response.final_disposition,
            "evidence_refs": turn.graph_response.evidence_refs,
            "ledger_entry_ids": turn.graph_response.ledger_entry_ids,
            "awaiting_evidence": turn.graph_response.awaiting_evidence,
            "human_action_pending": turn.graph_response.human_action_request is not None,
        }
        for turn in turns
    ]
    source_json = json.dumps(source_payload, sort_keys=True, separators=(",", ":"))
    source_hash = _sha256(source_json)
    retained = turns[-policy.recent_raw_turns :] if policy.recent_raw_turns else []
    raw_lines: list[str] = []
    for turn in retained:
        raw_lines.extend(
            (
                f"Turn {turn.turn_index} ID {turn.turn_id}",
                f"User: {turn.user_message.strip()}",
                f"Assistant: {turn.assistant_message.strip()}",
            )
        )
    hard_constraints = _unique(
        value
        for turn in turns
        for value in getattr(turn, "required_constraints", [])
    )
    accepted_decisions = _unique(
        f"turn:{turn.turn_index}:{turn.graph_response.final_disposition}"
        for turn in turns
        if turn.graph_response.final_disposition is not None
    )
    evidence_refs = _unique(
        value for turn in turns for value in turn.graph_response.evidence_refs
    )
    ledger_entry_ids = _unique(
        value for turn in turns for value in turn.graph_response.ledger_entry_ids
    )
    unresolved_items = _unique(
        item
        for turn in turns
        for item in (
            [f"turn:{turn.turn_index}:awaiting_evidence"]
            if turn.graph_response.awaiting_evidence
            else []
        )
        + (
            [f"turn:{turn.turn_index}:human_action_pending"]
            if turn.graph_response.human_action_request is not None
            else []
        )
    )
    structural_lines = [
        f"Conversation ID: {conversation_id}",
        f"Source revision: {revision}",
        f"Source hash: {source_hash}",
        f"Retained turn IDs: {', '.join(turn.turn_id for turn in retained) or 'none'}",
        f"Hard constraints: {'; '.join(hard_constraints) or 'none'}",
        f"Decision refs: {'; '.join(accepted_decisions) or 'none'}",
        f"Evidence refs: {', '.join(evidence_refs) or 'none'}",
        f"Ledger refs: {', '.join(ledger_entry_ids) or 'none'}",
        f"Unresolved refs: {', '.join(unresolved_items) or 'none'}",
    ]
    before_text = "\n".join(
        f"User: {turn.user_message}\nAssistant: {turn.assistant_message}" for turn in turns
    )
    summary = "\n".join([*structural_lines, "Recent visible turns:", *raw_lines])
    character_ceiling = policy.target_input_tokens * 4
    if len(summary) > character_ceiling:
        summary = summary[:character_ceiling]
        limitations = ["Context projection reached the deterministic character ceiling."]
    else:
        limitations = []
    summary_hash = _sha256(summary)
    snapshot_id = f"{conversation_id}:context:{revision}:{profile}:{summary_hash[-16:]}"
    return ContextSnapshot(
        snapshot_id=snapshot_id,
        thread_id=conversation_id,
        revision=revision,
        profile=profile,
        source_start_revision=turns[0].turn_index if turns else 0,
        source_end_revision=turns[-1].turn_index if turns else 0,
        summary_text=summary,
        pinned_facts=[f"conversation_id:{conversation_id}", f"revision:{revision}"],
        hard_constraints=hard_constraints,
        accepted_decisions=accepted_decisions,
        unresolved_items=unresolved_items,
        evidence_refs=evidence_refs,
        ledger_entry_ids=ledger_entry_ids,
        token_count_before=_approx_tokens(before_text),
        token_count_after=_approx_tokens(summary),
        source_hash=source_hash,
        summary_hash=summary_hash,
        limitations=limitations,
    )


class MultiAgentBudget(BaseModel):
    """Resource ceilings for bounded orchestration modes."""

    mode: OrchestrationMode
    max_agent_count: int = Field(ge=1, le=16)
    max_parallel_branches: int = Field(ge=1, le=8)
    max_turns_per_branch: int = Field(ge=1, le=32)
    token_ceiling: int = Field(ge=1)
    cost_ceiling_usd: float = Field(ge=0.0)
    wall_clock_deadline_ms: int = Field(ge=1)
    retry_ceiling: int = Field(ge=0, le=8)
    provider_concurrency_ceiling: int = Field(ge=1, le=8)


BUDGET_SINGLE = MultiAgentBudget(
    mode="single",
    max_agent_count=1,
    max_parallel_branches=1,
    max_turns_per_branch=1,
    token_ceiling=16_000,
    cost_ceiling_usd=0.05,
    wall_clock_deadline_ms=30_000,
    retry_ceiling=1,
    provider_concurrency_ceiling=1,
)

BUDGET_CRITIC = MultiAgentBudget(
    mode="critic",
    max_agent_count=3,
    max_parallel_branches=2,
    max_turns_per_branch=4,
    token_ceiling=48_000,
    cost_ceiling_usd=0.15,
    wall_clock_deadline_ms=60_000,
    retry_ceiling=2,
    provider_concurrency_ceiling=2,
)

BUDGET_COMMITTEE = MultiAgentBudget(
    mode="committee",
    max_agent_count=8,
    max_parallel_branches=4,
    max_turns_per_branch=8,
    token_ceiling=200_000,
    cost_ceiling_usd=0.50,
    wall_clock_deadline_ms=120_000,
    retry_ceiling=3,
    provider_concurrency_ceiling=4,
)

BUDGET_ADAPTIVE = MultiAgentBudget(
    mode="adaptive",
    max_agent_count=6,
    max_parallel_branches=3,
    max_turns_per_branch=6,
    token_ceiling=100_000,
    cost_ceiling_usd=0.30,
    wall_clock_deadline_ms=90_000,
    retry_ceiling=2,
    provider_concurrency_ceiling=3,
)


def resolve_multi_agent_budget(mode: OrchestrationMode) -> MultiAgentBudget:
    """Return the enforced budget for an orchestration mode."""

    return {
        "single": BUDGET_SINGLE,
        "critic": BUDGET_CRITIC,
        "committee": BUDGET_COMMITTEE,
        "adaptive": BUDGET_ADAPTIVE,
    }[mode]


class M18RuntimeStatus(BaseModel):
    """Authoritative distinction between active and deferred runtime behavior."""

    context_compaction: RuntimeMaturity = "implemented"
    multi_agent_orchestration: RuntimeMaturity = "implemented"
    active_context_profiles: list[ContextProfile] = Field(
        default_factory=lambda: ["minimal", "balanced", "max"]
    )
    active_orchestration_modes: list[OrchestrationMode] = Field(
        default_factory=lambda: ["critic", "committee", "adaptive"]
    )
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Context snapshots are deterministic projections, not model-generated summaries.",
            "Committee and adaptive are deterministic-only; live multi-provider calibration remains deferred.",
        ]
    )


def get_m18_runtime_status() -> M18RuntimeStatus:
    """Return the exact M18 runtime claim boundary."""

    return M18RuntimeStatus()


def _sha256(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _approx_tokens(value: str) -> int:
    return (len(value) + 3) // 4


def _unique(values) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
