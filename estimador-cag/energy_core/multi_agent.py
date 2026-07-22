"""Bounded multi-agent governance contracts for EACODE.

Model consensus is evidence, never authority. The deterministic boss fails closed
on missing findings, preserves disagreements, rejects hard-constraint violations,
and enforces per-agent plus global cost/time/tool/concurrency budgets.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from energy_core.models import EnergyModel

AgentRole = Literal["critic", "proposer", "reviewer", "boss"]
Disposition = Literal["accept", "repair", "reject", "escalate"]
DisagreementLevel = Literal["none", "minor", "major", "blocking"]


class AgentBudget(EnergyModel):
    """Per-agent resource budget."""

    max_cost_usd: Decimal = Field(default=Decimal("0.50"), ge=0)
    max_latency_ms: int = Field(default=30_000, ge=1)
    max_tool_calls: int = Field(default=20, ge=0)


class ConcurrencyBudget(EnergyModel):
    """Global resource budget for one governed multi-agent run."""

    max_parallel_agents: int = Field(default=4, ge=1, le=16)
    max_total_agents: int = Field(default=12, ge=1, le=128)
    max_total_cost_usd: Decimal = Field(default=Decimal("5.00"), ge=0)
    max_total_latency_ms: int = Field(default=120_000, ge=1)
    max_total_tool_calls: int = Field(default=100, ge=0)


class AgentTask(EnergyModel):
    """One independently owned agent task and its measured resource use."""

    task_id: str = Field(min_length=1)
    role: AgentRole = "critic"
    owner: str = ""
    objective: str = ""
    budget: AgentBudget = Field(default_factory=AgentBudget)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    outcome_disposition: Disposition | None = None
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    error_message: str | None = None
    cost_usd: Decimal = Field(default=Decimal("0.0"), ge=0)
    latency_ms: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)


class DisagreementRecord(EnergyModel):
    """Recorded disagreement between agents about a finding."""

    record_id: str = Field(min_length=1)
    topic: str = ""
    positions: tuple[str, ...] = Field(default_factory=tuple)
    level: DisagreementLevel = "minor"
    resolved: bool = False
    resolution: str = ""
    resolved_by: str = ""


class MultiAgentRun(EnergyModel):
    """One bounded multi-agent run with typed shared state."""

    run_id: str = Field(min_length=1)
    objective: str = ""
    shared_state: dict[str, Any] = Field(default_factory=dict)
    tasks: tuple[AgentTask, ...] = Field(default_factory=tuple)
    concurrency_budget: ConcurrencyBudget = Field(default_factory=ConcurrencyBudget)
    disagreements: tuple[DisagreementRecord, ...] = Field(default_factory=tuple)
    final_disposition: Disposition | None = None
    decided_by: str = ""
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    total_cost_usd: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_latency_ms: int = Field(default=0, ge=0)
    total_tool_calls: int = Field(default=0, ge=0)


class DeterministicBoss:
    """Fail-closed deterministic owner of the final disposition."""

    def __init__(
        self,
        boss_id: str = "deterministic-boss",
        budget: ConcurrencyBudget | None = None,
    ) -> None:
        self.boss_id = boss_id
        self._budget = budget or ConcurrencyBudget()

    def aggregate(
        self,
        run: MultiAgentRun,
        *,
        findings: list[dict[str, Any]] | None = None,
    ) -> MultiAgentRun:
        """Aggregate findings without allowing consensus to bypass constraints."""

        raw_findings = findings or []
        dispositions: list[Disposition] = []
        disagreements: list[DisagreementRecord] = list(run.disagreements)
        hard_violation = False

        for finding in raw_findings:
            if finding.get("hard_constraint_violation") is True:
                hard_violation = True
            disposition = finding.get("disposition")
            if disposition in ("accept", "repair", "reject", "escalate"):
                dispositions.append(disposition)

        if len(set(dispositions)) > 1:
            disagreements.append(
                DisagreementRecord(
                    record_id=f"disagreement-{run.run_id}",
                    topic="final_disposition",
                    positions=tuple(
                        f"{finding.get('owner', 'unknown')}:"
                        f"{finding.get('disposition', '?')}"
                        for finding in raw_findings
                    ),
                    level="major",
                )
            )

        if hard_violation or "reject" in dispositions:
            final: Disposition = "reject"
        elif not dispositions:
            final = "escalate"
        elif not self.validate_budget(run):
            final = "escalate"
        elif "escalate" in dispositions:
            final = "escalate"
        elif "repair" in dispositions:
            final = "repair"
        elif all(disposition == "accept" for disposition in dispositions):
            final = "accept"
        else:
            final = "escalate"

        if any(record.level == "blocking" for record in disagreements):
            final = "escalate"

        return run.model_copy(
            update={
                "disagreements": tuple(disagreements),
                "final_disposition": final,
                "decided_by": self.boss_id,
                "completed_at": datetime.now(),
            }
        )

    def validate_budget(self, run: MultiAgentRun) -> bool:
        """Validate global budgets, task budgets, and independent ownership."""

        budget = run.concurrency_budget or self._budget
        # An explicitly configured boss budget is the governing upper bound.
        effective = ConcurrencyBudget(
            max_parallel_agents=min(
                budget.max_parallel_agents, self._budget.max_parallel_agents
            ),
            max_total_agents=min(budget.max_total_agents, self._budget.max_total_agents),
            max_total_cost_usd=min(
                budget.max_total_cost_usd, self._budget.max_total_cost_usd
            ),
            max_total_latency_ms=min(
                budget.max_total_latency_ms, self._budget.max_total_latency_ms
            ),
            max_total_tool_calls=min(
                budget.max_total_tool_calls, self._budget.max_total_tool_calls
            ),
        )

        active = sum(1 for task in run.tasks if task.completed_at is None)
        owners = [task.owner for task in run.tasks if task.owner]
        independent_owners = len(owners) == len(set(owners))
        task_budgets_ok = all(
            task.cost_usd <= task.budget.max_cost_usd
            and task.latency_ms <= task.budget.max_latency_ms
            and task.tool_calls <= task.budget.max_tool_calls
            for task in run.tasks
        )

        measured_cost = max(
            run.total_cost_usd,
            sum((task.cost_usd for task in run.tasks), Decimal("0.0")),
        )
        measured_latency = max(
            run.total_latency_ms,
            sum(task.latency_ms for task in run.tasks),
        )
        measured_tool_calls = max(
            run.total_tool_calls,
            sum(task.tool_calls for task in run.tasks),
        )

        return (
            active <= effective.max_parallel_agents
            and len(run.tasks) <= effective.max_total_agents
            and measured_cost <= effective.max_total_cost_usd
            and measured_latency <= effective.max_total_latency_ms
            and measured_tool_calls <= effective.max_total_tool_calls
            and independent_owners
            and task_budgets_ok
        )
