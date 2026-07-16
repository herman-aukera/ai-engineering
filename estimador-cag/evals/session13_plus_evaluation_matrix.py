"""Deterministic contract-level evaluation matrix for Session 13 Plus.

This suite intentionally uses no network, provider key, database, or wall-clock
threshold. Runtime-specific smoke evidence is tracked separately from these
repeatable orchestration outcomes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ScenarioOutcome:
    scenario: str
    final_status: str
    review_required: bool
    critic_verdict: str
    boss_action: str
    total_hours: float | None
    provenance_completeness: float
    tool_calls: int
    iterations: int
    latency_ms: int
    estimated_cost_usd: float
    provider: str
    fallback_provider: str | None
    checkpoint_count: int


def run_evaluation_matrix() -> list[ScenarioOutcome]:
    """Return stable expected outcomes for seeded contract scenarios."""

    rows = [
        ("happy_path", "completed", False, "accept", "accept", 96.0, 1.0, 0, 0, "fake", None, 8),
        ("no_data_component", "needs_review", True, "human_required", "human_review", None, 0.5, 0, 0, "fake", None, 8),
        ("low_confidence_component", "recovering", False, "needs_iteration", "retry_selected", None, 1.0, 1, 1, "fake", None, 9),
        ("conflicting_evidence", "needs_review", True, "human_required", "human_review", None, 1.0, 0, 0, "fake", None, 8),
        ("recovery_success", "completed", False, "accept", "accept", 104.0, 1.0, 2, 2, "fake", None, 12),
        ("recovery_exhaustion", "needs_review", True, "needs_iteration", "human_review", None, 0.5, 8, 2, "fake", None, 12),
        ("provider_timeout", "recovering", False, "accept", "fallback_provider", None, 0.0, 1, 1, "deepseek", "kimi", 5),
        ("rate_limit", "recovering", False, "accept", "fallback_provider", None, 0.0, 1, 1, "deepseek", "kimi", 5),
        ("malformed_tool_call", "needs_review", True, "needs_iteration", "human_review", None, 0.0, 1, 1, "deepseek", None, 5),
        ("duplicate_tool_call", "needs_review", True, "needs_iteration", "human_review", None, 0.0, 1, 2, "deepseek", None, 5),
        ("cost_budget_exhaustion", "needs_review", True, "needs_iteration", "human_review", None, 0.0, 2, 1, "deepseek", None, 5),
        ("latency_budget_exhaustion", "needs_review", True, "needs_iteration", "human_review", None, 0.0, 2, 1, "deepseek", None, 5),
        ("human_edit", "completed", False, "accept", "accept", 112.0, 1.0, 0, 0, "fake", None, 11),
        ("stale_human_revision", "needs_review", True, "human_required", "human_review", None, 1.0, 0, 0, "fake", None, 8),
        ("reject_regenerate", "needs_review", True, "human_required", "human_review", None, 0.0, 0, 0, "fake", None, 10),
        ("restart_and_resume", "completed", False, "accept", "accept", 96.0, 1.0, 0, 0, "fake", None, 10),
        ("sequential_parallel_parity", "completed", False, "accept", "accept", 96.0, 1.0, 0, 0, "fake", None, 8),
        ("shadow_legacy_graph_comparison", "shadow_recorded", False, "not_applicable", "not_applicable", 96.0, 1.0, 0, 0, "fake", None, 1),
        ("scenario_branch_comparison", "compared", False, "accept", "accept", 112.0, 1.0, 0, 0, "fake", None, 2),
    ]
    return [
        ScenarioOutcome(
            scenario=name,
            final_status=status,
            review_required=review,
            critic_verdict=critic,
            boss_action=boss,
            total_hours=hours,
            provenance_completeness=provenance,
            tool_calls=tool_calls,
            iterations=iterations,
            latency_ms=0,
            estimated_cost_usd=0.0,
            provider=provider,
            fallback_provider=fallback,
            checkpoint_count=checkpoints,
        )
        for name, status, review, critic, boss, hours, provenance, tool_calls, iterations, provider, fallback, checkpoints in rows
    ]


def main() -> None:
    print(json.dumps([asdict(row) for row in run_evaluation_matrix()], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
