"""Bounded multi-agent governance contracts for EACODE.

Deterministic boss, typed shared state, independent ownership, disagreement
records, and cost/time/tool/concurrency budgets. No live provider calls.
No concurrent worktree edits.

Spec 0010 Slice F — additive module.
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
    """Global concurrency budget for a multi-agent run."""

    max_parallel_agents: int = Field(default=4, ge=1, le=16)
    max_total_agents: int = Field(default=12, ge=1, le=128)
    max_total_cost_usd: Decimal = Field(default=Decimal("5.00"), ge=0)
    max_total_latency_ms: int = Field(default=120_000, ge=1)


class AgentTask(EnergyModel):
    """One independent task assigned to an agent."""

    task_id: str = Field(min_length=1)
    role: AgentRole = "critic"
    owner: str = ""  # agent identity
    objective: str = ""
    budget: AgentBudget = Field(default_factory=AgentBudget)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    outcome_disposition: Disposition | None = None
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    error_message: str | None = None


class DisagreementRecord(EnergyModel):
    """Recorded disagreement between agents about a finding."""

    record_id: str = Field(min_length=1)
    topic: str = ""
    positions: tuple[str, ...] = Field(default_factory=tuple)  # agent:position
    level: DisagreementLevel = "minor"
    resolved: bool = False
    resolution: str = ""
    resolved_by: str = ""  # boss identity


class MultiAgentRun(EnergyModel):
    """One bounded multi-agent run with typed shared state."""

    run_id: str = Field(min_length=1)
    objective: str = ""
    shared_state: dict[str, Any] = Field(default_factory=dict)
    tasks: tuple[AgentTask, ...] = Field(default_factory=tuple)
    concurrency_budget: ConcurrencyBudget = Field(default_factory=ConcurrencyBudget)
    disagreements: tuple[DisagreementRecord, ...] = Field(default_factory=tuple)
    final_disposition: Disposition | None = None
    decided_by: str = ""  # boss identity
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    total_cost_usd: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_latency_ms: int = Field(default=0, ge=0)


# ------------------------------------------------------------------
# Deterministic boss
# ------------------------------------------------------------------


class DeterministicBoss:
    """Deterministic boss that owns final disposition.

    Aggregates agent findings, records disagreements, and decides
    accept/repair/reject/escalate. Model consensus is evidence, never authority.
    """

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
        """Aggregate independent agent findings into a final disposition.

        Returns an updated run with disagreements recorded and final disposition set.
        """
        findings = findings or []
        dispositions: list[Disposition] = []
        disagreements: list[DisagreementRecord] = list(run.disagreements)

        for finding in findings:
            disp = finding.get("disposition", "accept")
            if disp in ("accept", "repair", "reject", "escalate"):
                dispositions.append(disp)

        # Detect disagreements
        if len(set(dispositions)) > 1:
            disagreement = DisagreementRecord(
                record_id=f"disagreement-{run.run_id}",
                topic="final_disposition",
                positions=tuple(
                    f"{f.get('owner', 'unknown')}:{f.get('disposition', '?')}"
                    for f in findings
                ),
                level="major",
            )
            disagreements.append(disagreement)

        # Boss decides: accept only if all accept, reject if any reject
        if "reject" in dispositions:
            final: Disposition = "reject"
        elif "escalate" in dispositions:
            final = "escalate"
        elif "repair" in dispositions:
            final = "repair"
        elif all(d == "accept" for d in dispositions):
            final = "accept"
        else:
            final = "escalate"

        # Detect blocking disagreements
        for d in disagreements:
            if d.level == "blocking":
                final = "escalate"

        return run.model_copy(update={
            "disagreements": tuple(disagreements),
            "final_disposition": final,
            "decided_by": self.boss_id,
            "completed_at": datetime.now(),
        })

    def validate_budget(self, run: MultiAgentRun) -> bool:
        """Return True if the run is within concurrency budget."""
        active = sum(1 for t in run.tasks if t.completed_at is None)
        return (
            active <= self._budget.max_parallel_agents
            and len(run.tasks) <= self._budget.max_total_agents
            and run.total_cost_usd <= self._budget.max_total_cost_usd
        )
