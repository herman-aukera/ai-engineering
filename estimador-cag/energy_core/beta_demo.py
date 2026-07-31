"""Keyless, network-free EACODE beta demonstration journey."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import Field

from energy_core.coding_agent import CodingProposal
from energy_core.models import EnergyModel
from energy_core.semantic_jury import (
    ActionGovernor,
    DeterministicHardGateResult,
    GovernorDecision,
    SemanticJudgeResult,
    SemanticJury,
)


class RepairRecord(EnergyModel):
    revision: int = Field(ge=1)
    summary: str
    before_patch: str
    after_patch: str


class AuthorizationRecord(EnergyModel):
    proposal_id: str
    authorized: bool
    actor: str | None = None
    scope: tuple[tuple[str, ...], ...] = Field(default_factory=tuple)


class DemoExecutionEvidence(EnergyModel):
    execution_performed: bool
    adapter: str = "deterministic-simulated-runner"
    exit_code: int | None = None
    summary: str
    sanitized: bool = True


class RollbackState(EnergyModel):
    available: bool
    boundary: str
    performed: bool = False


class TimelineRecord(EnergyModel):
    event_type: Literal[
        "proposal", "hard_gate", "jury", "repair", "authorization", "execution", "reevaluation"
    ]
    summary: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BetaDemoResult(EnergyModel):
    active_specification: str
    proposal: CodingProposal
    initial_decision: GovernorDecision
    final_decision: GovernorDecision
    repair_history: tuple[RepairRecord, ...]
    authorization: AuthorizationRecord
    execution: DemoExecutionEvidence
    rollback: RollbackState
    timeline: tuple[TimelineRecord, ...]


class BetaDemoRunner:
    """Exercises contracts without calling a provider or creating a process."""

    def run(self, proposal: CodingProposal, *, human_authorization: bool) -> BetaDemoResult:
        timeline = [TimelineRecord(event_type="proposal", summary="Typed proposal received.")]
        hard_gate = DeterministicHardGateResult(candidate_id=proposal.proposal_id)
        timeline.append(TimelineRecord(event_type="hard_gate", summary="Hard gates passed."))

        defect = "todo" in proposal.patch.lower()
        initial_jury = SemanticJury().aggregate(
            (
                self._judge("semantic-correctness", "repair" if defect else "accept"),
                self._judge("semantic-maintainability", "repair" if defect else "accept"),
            )
        )
        timeline.append(TimelineRecord(event_type="jury", summary="Independent jury recorded."))
        initial = ActionGovernor().decide(hard_gate=hard_gate, jury=initial_jury)

        repairs: tuple[RepairRecord, ...] = ()
        if initial.disposition == "repair":
            repaired = proposal.patch.replace("'todo'", "'ok'").replace('"todo"', '"ok"')
            repairs = (
                RepairRecord(
                    revision=1,
                    summary="Replaced the deterministic semantic defect fixture.",
                    before_patch=proposal.patch,
                    after_patch=repaired,
                ),
            )
            timeline.append(TimelineRecord(event_type="repair", summary=repairs[0].summary))

        authorization = AuthorizationRecord(
            proposal_id=proposal.proposal_id,
            authorized=human_authorization,
            actor="demo-human" if human_authorization else None,
            scope=proposal.proposed_commands if human_authorization else (),
        )
        timeline.append(
            TimelineRecord(event_type="authorization", summary="Authorization decision recorded.")
        )
        execution = DemoExecutionEvidence(
            execution_performed=human_authorization,
            exit_code=0 if human_authorization else None,
            summary=(
                "Bounded simulated test execution passed."
                if human_authorization
                else "Execution blocked pending human authorization."
            ),
        )
        timeline.append(TimelineRecord(event_type="execution", summary=execution.summary))

        if human_authorization:
            final_jury = SemanticJury().aggregate(
                (self._judge("semantic-correctness"), self._judge("semantic-maintainability"))
            )
            final = ActionGovernor().decide(hard_gate=hard_gate, jury=final_jury)
        else:
            final = GovernorDecision(
                disposition="escalate",
                human_review_required=True,
                reason="Protected action lacks human authorization.",
            )
        timeline.append(TimelineRecord(event_type="reevaluation", summary="Governor reevaluated evidence."))
        return BetaDemoResult(
            active_specification=proposal.spec_id,
            proposal=proposal,
            initial_decision=initial,
            final_decision=final,
            repair_history=repairs,
            authorization=authorization,
            execution=execution,
            rollback=RollbackState(
                available=True,
                boundary=f"before:{proposal.proposal_id}",
            ),
            timeline=tuple(timeline),
        )

    @staticmethod
    def _judge(judge_id: str, disposition: str = "accept") -> SemanticJudgeResult:
        return SemanticJudgeResult(
            judge_id=judge_id,
            provider="fixture",
            model="deterministic-fixture",
            disposition=disposition,
            summary=f"{judge_id} evaluated the proposal.",
        )
