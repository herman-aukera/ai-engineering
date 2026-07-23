from evals.session13_plus_evaluation_matrix import run_evaluation_matrix

REQUIRED_SCENARIOS = {
    "happy_path",
    "no_data_component",
    "low_confidence_component",
    "conflicting_evidence",
    "recovery_success",
    "recovery_exhaustion",
    "provider_timeout",
    "rate_limit",
    "malformed_tool_call",
    "duplicate_tool_call",
    "cost_budget_exhaustion",
    "latency_budget_exhaustion",
    "human_edit",
    "stale_human_revision",
    "reject_regenerate",
    "restart_and_resume",
    "sequential_parallel_parity",
    "shadow_legacy_graph_comparison",
    "scenario_branch_comparison",
}


def test_matrix_covers_every_required_plus_scenario_with_metrics() -> None:
    outcomes = run_evaluation_matrix()

    assert {outcome.scenario for outcome in outcomes} == REQUIRED_SCENARIOS
    assert len(outcomes) == len(REQUIRED_SCENARIOS)
    for outcome in outcomes:
        assert outcome.final_status
        assert outcome.critic_verdict
        assert outcome.boss_action
        assert 0 <= outcome.provenance_completeness <= 1
        assert outcome.tool_calls >= 0
        assert outcome.iterations >= 0
        assert outcome.latency_ms >= 0
        assert outcome.estimated_cost_usd >= 0
        assert outcome.provider
        assert outcome.checkpoint_count >= 1


def test_failure_and_budget_scenarios_never_silently_accept() -> None:
    by_name = {outcome.scenario: outcome for outcome in run_evaluation_matrix()}
    guarded = {
        "malformed_tool_call",
        "duplicate_tool_call",
        "cost_budget_exhaustion",
        "latency_budget_exhaustion",
        "stale_human_revision",
    }

    for name in guarded:
        assert by_name[name].review_required is True
        assert by_name[name].boss_action != "accept"


def test_provider_fallback_is_explicit_and_only_on_seeded_failures() -> None:
    outcomes = run_evaluation_matrix()
    fallbacks = {row.scenario: row for row in outcomes if row.fallback_provider}

    assert set(fallbacks) == {"provider_timeout", "rate_limit"}
    assert all(row.boss_action == "fallback_provider" for row in fallbacks.values())
