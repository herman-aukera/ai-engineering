"""Milestone 18 contracts and explicit runtime-maturity boundaries."""

from app.energy_chat.context_compaction import (
    ContextSnapshot,
    get_m18_runtime_status,
    resolve_compaction_policy,
    resolve_multi_agent_budget,
)


# ── compaction policies ─────────────────────────────────────────────────


def test_minimal_policy_retains_core_constraints() -> None:
    policy = resolve_compaction_policy("minimal")
    assert policy.profile == "minimal"
    assert policy.target_input_tokens == 4_000
    assert policy.recent_raw_turns == 2
    assert policy.preserve_pinned_facts is True
    assert policy.preserve_evidence_refs is True
    assert policy.preserve_ledger_refs is True
    assert policy.drift_check_enabled is True


def test_balanced_policy_is_default() -> None:
    policy = resolve_compaction_policy("balanced")
    assert policy.target_input_tokens == 16_000
    assert policy.recent_raw_turns == 8
    assert policy.max_summary_depth == 2


def test_max_policy_retains_most_context() -> None:
    policy = resolve_compaction_policy("max")
    assert policy.target_input_tokens == 64_000
    assert policy.recent_raw_turns == 24
    assert policy.max_summary_depth == 3


def test_policies_scale_monotonically() -> None:
    minimal = resolve_compaction_policy("minimal")
    balanced = resolve_compaction_policy("balanced")
    max_p = resolve_compaction_policy("max")
    assert minimal.target_input_tokens < balanced.target_input_tokens < max_p.target_input_tokens
    assert minimal.recent_raw_turns < balanced.recent_raw_turns < max_p.recent_raw_turns


def test_context_snapshot_links_source_range() -> None:
    snap = ContextSnapshot(
        snapshot_id="snap-1",
        thread_id="thread-1",
        revision=1,
        profile="balanced",
        source_start_revision=0,
        source_end_revision=5,
    )
    assert snap.token_count_before == 0
    assert snap.token_count_after == 0
    assert snap.pinned_facts == []


# ── multi-agent budgets ─────────────────────────────────────────────────


def test_single_mode_is_cheapest() -> None:
    budget = resolve_multi_agent_budget("single")
    assert budget.max_agent_count == 1
    assert budget.max_parallel_branches == 1
    assert budget.cost_ceiling_usd == 0.05


def test_critic_mode_is_default_energy_aware() -> None:
    budget = resolve_multi_agent_budget("critic")
    assert budget.max_agent_count == 3
    assert budget.token_ceiling == 48_000
    assert budget.cost_ceiling_usd == 0.15


def test_committee_mode_is_most_expensive() -> None:
    budget = resolve_multi_agent_budget("committee")
    assert budget.max_agent_count == 8
    assert budget.cost_ceiling_usd == 0.50


def test_adaptive_mode_sits_between_critic_and_committee() -> None:
    critic = resolve_multi_agent_budget("critic")
    adaptive = resolve_multi_agent_budget("adaptive")
    committee = resolve_multi_agent_budget("committee")
    assert critic.max_agent_count < adaptive.max_agent_count < committee.max_agent_count
    assert critic.cost_ceiling_usd < adaptive.cost_ceiling_usd < committee.cost_ceiling_usd


def test_all_budgets_have_positive_limits() -> None:
    for mode in ("single", "critic", "committee", "adaptive"):
        budget = resolve_multi_agent_budget(mode)
        assert budget.max_agent_count >= 1
        assert budget.token_ceiling >= 1
        assert budget.wall_clock_deadline_ms >= 1


def test_m18_reports_contracts_without_claiming_runtime_execution() -> None:
    status = get_m18_runtime_status()

    assert status.context_compaction == "contract_only"
    assert status.multi_agent_orchestration == "contract_only"
    assert status.active_context_profiles == ["balanced"]
    assert status.active_orchestration_modes == ["critic"]
    assert "No runtime context compaction is executed." in status.limitations
    assert "No committee or adaptive agent runtime is executed." in status.limitations
