"""Context compaction and multi-agent profile contracts for Energy Aware Chat.

Milestone 18: typed compaction policies per context profile, multi-agent
budget models per orchestration mode. Profiles resolve to explicit retention
rules and budget limits. Runtime execution is deferred to provider-integrated
milestones; this module provides the validated contract layer.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── Context profiles ────────────────────────────────────────────────────

ContextProfile = Literal["minimal", "balanced", "max"]


class ContextCompactionPolicy(BaseModel):
    """What to retain when compacting conversation context.

    Each profile defines explicit retention rules. Hard constraints,
    pinned facts, evidence/ledger references, and unresolved items are
    always preserved regardless of profile.
    """

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
    """One versioned compaction of a conversation context.

    Links back to source range via revision numbers and content hashes
    so drift can be detected and the previous trusted snapshot restored.
    """

    snapshot_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
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
    source_hash: str = ""
    summary_hash: str = ""
    limitations: list[str] = Field(default_factory=list)


POLICY_MINIMAL = ContextCompactionPolicy(
    profile="minimal",
    target_input_tokens=4_000,
    recent_raw_turns=2,
    summarizer_profile="fast",
    max_summary_depth=1,
)

POLICY_BALANCED = ContextCompactionPolicy(
    profile="balanced",
    target_input_tokens=16_000,
    recent_raw_turns=8,
    summarizer_profile="balanced",
    max_summary_depth=2,
)

POLICY_MAX = ContextCompactionPolicy(
    profile="max",
    target_input_tokens=64_000,
    recent_raw_turns=24,
    summarizer_profile="max",
    max_summary_depth=3,
)


def resolve_compaction_policy(profile: ContextProfile) -> ContextCompactionPolicy:
    """Return the compaction policy for a given context profile."""
    return {
        "minimal": POLICY_MINIMAL,
        "balanced": POLICY_BALANCED,
        "max": POLICY_MAX,
    }[profile]


# ── Multi-agent profiles ────────────────────────────────────────────────

OrchestrationMode = Literal["single", "critic", "committee", "adaptive"]


class MultiAgentBudget(BaseModel):
    """Bounded resource limits for one orchestration mode.

    Every limit is explicit and enforced deterministically. The boss/
    adjudicator cannot override these ceilings.
    """

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
    """Return the budget limits for a given orchestration mode."""
    return {
        "single": BUDGET_SINGLE,
        "critic": BUDGET_CRITIC,
        "committee": BUDGET_COMMITTEE,
        "adaptive": BUDGET_ADAPTIVE,
    }[mode]
