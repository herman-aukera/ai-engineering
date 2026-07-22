"""Fail-closed deterministic boss tests."""

from __future__ import annotations

from decimal import Decimal

from energy_core.multi_agent import (
    AgentBudget,
    AgentTask,
    ConcurrencyBudget,
    DeterministicBoss,
    MultiAgentRun,
)


def test_empty_findings_escalate_instead_of_accepting() -> None:
    result = DeterministicBoss().aggregate(
        MultiAgentRun(run_id="empty-findings"),
        findings=[],
    )
    assert result.final_disposition == "escalate"


def test_invalid_findings_escalate_instead_of_accepting() -> None:
    result = DeterministicBoss().aggregate(
        MultiAgentRun(run_id="invalid-findings"),
        findings=[{"owner": "critic-a", "disposition": "unknown"}],
    )
    assert result.final_disposition == "escalate"


def test_hard_constraint_violation_cannot_be_outvoted() -> None:
    result = DeterministicBoss().aggregate(
        MultiAgentRun(run_id="hard-violation"),
        findings=[
            {"owner": "critic-a", "disposition": "accept"},
            {
                "owner": "critic-b",
                "disposition": "accept",
                "hard_constraint_violation": True,
            },
        ],
    )
    assert result.final_disposition == "reject"


def test_per_agent_latency_budget_is_enforced() -> None:
    task = AgentTask(
        task_id="slow-task",
        owner="critic-a",
        budget=AgentBudget(max_latency_ms=100),
        latency_ms=101,
    )
    run = MultiAgentRun(run_id="slow-run", tasks=(task,))
    assert DeterministicBoss().validate_budget(run) is False


def test_per_agent_tool_budget_is_enforced() -> None:
    task = AgentTask(
        task_id="tool-heavy",
        owner="critic-a",
        budget=AgentBudget(max_tool_calls=1),
        tool_calls=2,
    )
    run = MultiAgentRun(run_id="tool-run", tasks=(task,))
    assert DeterministicBoss().validate_budget(run) is False


def test_global_latency_and_tool_budgets_are_enforced() -> None:
    run = MultiAgentRun(
        run_id="global-budget",
        total_latency_ms=1001,
        total_tool_calls=3,
        concurrency_budget=ConcurrencyBudget(
            max_total_latency_ms=1000,
            max_total_tool_calls=2,
        ),
    )
    assert DeterministicBoss().validate_budget(run) is False


def test_duplicate_task_ownership_is_rejected() -> None:
    run = MultiAgentRun(
        run_id="duplicate-owner",
        tasks=(
            AgentTask(task_id="a", owner="same-owner"),
            AgentTask(task_id="b", owner="same-owner"),
        ),
    )
    assert DeterministicBoss().validate_budget(run) is False


def test_budget_overrun_forces_escalation_even_when_findings_accept() -> None:
    task = AgentTask(
        task_id="expensive",
        owner="critic-a",
        budget=AgentBudget(max_cost_usd=Decimal("0.10")),
        cost_usd=Decimal("0.11"),
    )
    result = DeterministicBoss().aggregate(
        MultiAgentRun(run_id="budget-escalation", tasks=(task,)),
        findings=[{"owner": "critic-a", "disposition": "accept"}],
    )
    assert result.final_disposition == "escalate"
