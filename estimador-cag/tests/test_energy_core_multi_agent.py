"""Tests for multi-agent governance contracts and deterministic boss.

Deterministic — no live API calls, no real provider calls required.
"""

from __future__ import annotations  # noqa: I001

from decimal import Decimal

from energy_core.multi_agent import (
    AgentBudget,
    AgentTask,
    ConcurrencyBudget,
    DeterministicBoss,
    DisagreementRecord,
    MultiAgentRun,
)


# ------------------------------------------------------------------
# Contract round-trips
# ------------------------------------------------------------------


def test_agent_budget_round_trips() -> None:
    budget = AgentBudget(max_cost_usd=Decimal("1.00"), max_latency_ms=5000)
    reloaded = AgentBudget.model_validate(budget.model_dump(mode="json"))
    assert reloaded.max_cost_usd == Decimal("1.00")


def test_concurrency_budget_round_trips() -> None:
    budget = ConcurrencyBudget(max_parallel_agents=8, max_total_cost_usd=Decimal("10.00"))
    reloaded = ConcurrencyBudget.model_validate(budget.model_dump(mode="json"))
    assert reloaded.max_parallel_agents == 8


def test_agent_task_round_trips() -> None:
    task = AgentTask(task_id="task-1", role="critic", owner="agent-a", objective="review")
    reloaded = AgentTask.model_validate(task.model_dump(mode="json"))
    assert reloaded.task_id == "task-1"


def test_disagreement_record_round_trips() -> None:
    dr = DisagreementRecord(
        record_id="dr-1",
        topic="finding-x",
        positions=("agent-a:accept", "agent-b:reject"),
        level="major",
    )
    reloaded = DisagreementRecord.model_validate(dr.model_dump(mode="json"))
    assert reloaded.level == "major"


def test_multi_agent_run_round_trips() -> None:
    run = MultiAgentRun(
        run_id="run-1",
        objective="test",
        tasks=(AgentTask(task_id="t1", role="critic", owner="a1", objective="review"),),
    )
    reloaded = MultiAgentRun.model_validate(run.model_dump(mode="json"))
    assert reloaded.run_id == "run-1"


# ------------------------------------------------------------------
# Deterministic boss
# ------------------------------------------------------------------


def test_boss_all_accept_yields_accept() -> None:
    boss = DeterministicBoss()
    run = MultiAgentRun(run_id="run-acc", objective="test")
    findings = [
        {"owner": "a", "disposition": "accept"},
        {"owner": "b", "disposition": "accept"},
    ]
    result = boss.aggregate(run, findings=findings)
    assert result.final_disposition == "accept"
    assert result.decided_by == "deterministic-boss"


def test_boss_any_reject_yields_reject() -> None:
    boss = DeterministicBoss()
    run = MultiAgentRun(run_id="run-rej", objective="test")
    findings = [
        {"owner": "a", "disposition": "accept"},
        {"owner": "b", "disposition": "reject"},
    ]
    result = boss.aggregate(run, findings=findings)
    assert result.final_disposition == "reject"


def test_boss_any_escalate_yields_escalate() -> None:
    boss = DeterministicBoss()
    run = MultiAgentRun(run_id="run-esc", objective="test")
    findings = [
        {"owner": "a", "disposition": "accept"},
        {"owner": "b", "disposition": "escalate"},
    ]
    result = boss.aggregate(run, findings=findings)
    assert result.final_disposition == "escalate"


def test_boss_mixed_yields_repair() -> None:
    boss = DeterministicBoss()
    run = MultiAgentRun(run_id="run-rep", objective="test")
    findings = [
        {"owner": "a", "disposition": "accept"},
        {"owner": "b", "disposition": "repair"},
    ]
    result = boss.aggregate(run, findings=findings)
    assert result.final_disposition == "repair"


def test_boss_records_disagreement() -> None:
    boss = DeterministicBoss()
    run = MultiAgentRun(run_id="run-dis", objective="test")
    findings = [
        {"owner": "a", "disposition": "accept"},
        {"owner": "b", "disposition": "reject"},
    ]
    result = boss.aggregate(run, findings=findings)
    assert len(result.disagreements) > 0
    assert result.disagreements[0].level == "major"


def test_boss_no_disagreement_when_all_same() -> None:
    boss = DeterministicBoss()
    run = MultiAgentRun(run_id="run-ok", objective="test")
    findings = [
        {"owner": "a", "disposition": "accept"},
        {"owner": "b", "disposition": "accept"},
    ]
    result = boss.aggregate(run, findings=findings)
    assert len(result.disagreements) == 0


def test_boss_blocking_disagreement_forces_escalate() -> None:
    boss = DeterministicBoss()
    run = MultiAgentRun(
        run_id="run-block",
        objective="test",
        disagreements=(
            DisagreementRecord(
                record_id="dr-block",
                topic="critical",
                positions=("a:reject",),
                level="blocking",
            ),
        ),
    )
    result = boss.aggregate(run, findings=[{"owner": "a", "disposition": "accept"}])
    assert result.final_disposition == "escalate"


def test_boss_validate_budget_within_limits() -> None:
    boss = DeterministicBoss()
    run = MultiAgentRun(
        run_id="run-budget",
        objective="test",
        tasks=tuple(
            AgentTask(task_id=f"t{i}", role="critic", owner=f"a{i}", objective="x")
            for i in range(3)
        ),
    )
    assert boss.validate_budget(run) is True


def test_boss_validate_budget_exceeded_parallel() -> None:
    boss = DeterministicBoss(budget=ConcurrencyBudget(max_parallel_agents=2))
    run = MultiAgentRun(
        run_id="run-over",
        objective="test",
        tasks=tuple(
            AgentTask(task_id=f"t{i}", role="critic", owner=f"a{i}", objective="x")
            for i in range(5)
        ),
    )
    assert boss.validate_budget(run) is False


def test_boss_validate_budget_exceeded_cost() -> None:
    boss = DeterministicBoss(budget=ConcurrencyBudget(max_total_cost_usd=Decimal("1.00")))
    run = MultiAgentRun(
        run_id="run-cost",
        objective="test",
        total_cost_usd=Decimal("10.00"),
    )
    assert boss.validate_budget(run) is False
