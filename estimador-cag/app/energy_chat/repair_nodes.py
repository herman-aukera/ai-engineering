"""Explicit bounded deterministic repair nodes for Energy Aware Chat."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import Field, model_validator

from app.energy_chat.contracts import EnergyChatRequest, EvaluationResult
from app.energy_chat.evaluator import run_evaluation
from app.energy_chat.graph_state import (
    CandidateVersion,
    EnergyChatGraphState,
    GraphStateRecord,
    RepairRequest,
    RepairResultRecord,
    RetryBudget,
    TraceEvent,
    append_unique_records,
    build_trace_event,
    validated_state_update,
)
from app.energy_chat.repairs import build_repaired_request


class RepairProposal(GraphStateRecord):
    """Auditable proposed candidate revision from a repair strategy."""

    proposed_answer: str = Field(min_length=1)
    instructions: list[str] = Field(min_length=1)
    repairs_applied: list[str] = Field(min_length=1)


class RepairStrategy(Protocol):
    """Provider-free repair proposal boundary."""

    def propose(
        self, request: EnergyChatRequest, evaluation: EvaluationResult
    ) -> RepairProposal | None:
        """Return one explicit repair proposal or report it is not repairable."""


class DeterministicRepairStrategy:
    """Adapter preserving the existing one-pass deterministic repair behavior."""

    def propose(
        self, request: EnergyChatRequest, evaluation: EvaluationResult
    ) -> RepairProposal | None:
        repaired, repairs_applied = build_repaired_request(request, evaluation)
        if repaired is None:
            return None
        return RepairProposal(
            proposed_answer=repaired.draft_answer,
            instructions=evaluation.decision.required_repairs,
            repairs_applied=repairs_applied,
        )


class RepairPlanDelta(GraphStateRecord):
    """Either one explicit repair request or a terminal non-repairable result."""

    repair_requests: list[RepairRequest] = Field(default_factory=list, max_length=1)
    repair_results: list[RepairResultRecord] = Field(default_factory=list, max_length=1)
    status: Literal["repair_requested", "evaluated"]
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)

    @model_validator(mode="after")
    def exactly_one_plan_outcome(self) -> RepairPlanDelta:
        if bool(self.repair_requests) == bool(self.repair_results):
            raise ValueError("Repair planning must request repair or terminate")
        return self


class ApplyRepairDelta(GraphStateRecord):
    """Candidate-history and retry-budget update for one applied repair."""

    candidate_versions: list[CandidateVersion] = Field(min_length=1, max_length=1)
    active_candidate_id: str = Field(min_length=1)
    retry_budget: RetryBudget
    status: Literal["candidate_ready"] = "candidate_ready"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


class RepairFinalizationDelta(GraphStateRecord):
    """Terminal assessment of a completed or blocked repair cycle."""

    repair_results: list[RepairResultRecord] = Field(min_length=1, max_length=1)
    status: Literal["evaluated"] = "evaluated"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


def plan_repair(
    state: EnergyChatGraphState,
    *,
    strategy: RepairStrategy | None = None,
) -> RepairPlanDelta:
    """Create one explicit repair request from the active repair disposition."""

    candidate, score, decision = _active_evaluation_records(state)
    if decision.disposition != "repair":
        raise ValueError("Repair planning requires a repair disposition")
    attempt = state.retry_budget.attempts_used + 1
    repair_id = f"{candidate.candidate_id}:repair:{attempt}"
    if state.retry_budget.remaining < 1:
        result = _terminal_result(
            repair_id=repair_id,
            candidate_id=candidate.candidate_id,
            energy=score.score.total_energy,
            outcome="budget_exhausted",
        )
        return _terminal_plan_delta(state, result)

    request = EnergyChatRequest(
        user_message=state.user_request,
        draft_answer=candidate.answer,
        mode=state.mode,
        required_constraints=state.constraints,
        evidence_refs=candidate.evidence_refs,
    )
    evaluation = run_evaluation(request)
    if evaluation.score != score.score or evaluation.decision.decision != decision.disposition:
        raise ValueError("Retained evaluation does not match deterministic repair input")
    proposal = (strategy or DeterministicRepairStrategy()).propose(request, evaluation)
    if proposal is None:
        result = _terminal_result(
            repair_id=repair_id,
            candidate_id=candidate.candidate_id,
            energy=score.score.total_energy,
            outcome="not_repairable",
        )
        return _terminal_plan_delta(state, result)

    target_candidate_id = f"{state.request_id}:candidate:{candidate.version + 1}"
    repair_request = RepairRequest(
        repair_id=repair_id,
        candidate_id=candidate.candidate_id,
        source_decision_id=decision.decision_id,
        target_candidate_id=target_candidate_id,
        instructions=proposal.instructions,
        proposed_answer=proposal.proposed_answer,
        repairs_applied=proposal.repairs_applied,
    )
    event = build_trace_event(
        state,
        event_type="repair_requested",
        event_key=f"repair_requested:{repair_id}",
        producer="plan_repair",
        payload={
            "repair_id": repair_id,
            "repair_instruction_count": len(proposal.instructions),
            "source_candidate_id": candidate.candidate_id,
            "target_candidate_id": target_candidate_id,
        },
    )
    return RepairPlanDelta(
        repair_requests=[repair_request],
        status="repair_requested",
        trace_events=[event],
    )


def apply_repair(state: EnergyChatGraphState) -> ApplyRepairDelta:
    """Apply the retained explicit proposal as a new immutable candidate version."""

    if state.retry_budget.remaining < 1:
        raise ValueError("Retry budget exhausted before repair application")
    request = _pending_repair_request(state)
    if request.proposed_answer is None or request.target_candidate_id is None:
        raise ValueError("Repair request is missing its proposed candidate")
    source = next(
        item for item in state.candidate_versions if item.candidate_id == request.candidate_id
    )
    candidate = CandidateVersion(
        candidate_id=request.target_candidate_id,
        version=source.version + 1,
        answer=request.proposed_answer,
        producer="apply_repair",
        evidence_refs=source.evidence_refs,
    )
    retry_budget = state.retry_budget.model_copy(
        update={"attempts_used": state.retry_budget.attempts_used + 1}
    )
    event = build_trace_event(
        state,
        event_type="repair_applied",
        event_key=f"repair_applied:{request.repair_id}",
        producer="apply_repair",
        payload={
            "repair_id": request.repair_id,
            "target_candidate_id": candidate.candidate_id,
            "retry_attempts_used": retry_budget.attempts_used,
        },
    )
    return ApplyRepairDelta(
        candidate_versions=[candidate],
        active_candidate_id=candidate.candidate_id,
        retry_budget=retry_budget,
        trace_events=[event],
    )


def finalize_repair(state: EnergyChatGraphState) -> RepairFinalizationDelta:
    """Record improvement, no improvement, or exhausted budget and stop the loop."""

    active = next(
        candidate
        for candidate in state.candidate_versions
        if candidate.candidate_id == state.active_candidate_id
    )
    matching_request = next(
        (
            request
            for request in reversed(state.repair_requests)
            if request.target_candidate_id == active.candidate_id
        ),
        None,
    )
    if matching_request is None:
        score = next(
            item for item in reversed(state.energy_scores) if item.candidate_id == active.candidate_id
        )
        result = _terminal_result(
            repair_id=f"{active.candidate_id}:repair:{state.retry_budget.attempts_used + 1}",
            candidate_id=active.candidate_id,
            energy=score.score.total_energy,
            outcome="budget_exhausted",
        )
    else:
        before = next(
            item
            for item in state.energy_scores
            if item.candidate_id == matching_request.candidate_id
        )
        after = next(
            item
            for item in reversed(state.energy_scores)
            if item.candidate_id == active.candidate_id
        )
        final_decision = next(
            item
            for item in reversed(state.decision_outcomes)
            if item.candidate_id == active.candidate_id
        )
        if after.score.total_energy >= before.score.total_energy:
            outcome = "no_improvement"
        elif final_decision.disposition == "repair" and state.retry_budget.remaining == 0:
            outcome = "budget_exhausted"
        else:
            outcome = "improved"
        result = RepairResultRecord(
            result_id=f"{matching_request.repair_id}:result",
            repair_id=matching_request.repair_id,
            source_candidate_id=matching_request.candidate_id,
            target_candidate_id=active.candidate_id,
            energy_before=before.score.total_energy,
            energy_after=after.score.total_energy,
            outcome=outcome,
        )
    event = build_trace_event(
        state,
        event_type="repair_finalized",
        event_key=f"repair_finalized:{result.result_id}",
        producer="finalize_repair",
        payload={
            "energy_after": result.energy_after,
            "energy_before": result.energy_before,
            "outcome": result.outcome,
            "repair_id": result.repair_id,
        },
    )
    return RepairFinalizationDelta(repair_results=[result], trace_events=[event])


def apply_repair_plan_delta(
    state: EnergyChatGraphState, delta: RepairPlanDelta
) -> EnergyChatGraphState:
    return validated_state_update(
        state,
        repair_requests=append_unique_records(
            state.repair_requests, delta.repair_requests, id_field="repair_id"
        ),
        repair_results=append_unique_records(
            state.repair_results, delta.repair_results, id_field="result_id"
        ),
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def apply_repair_delta(
    state: EnergyChatGraphState, delta: ApplyRepairDelta
) -> EnergyChatGraphState:
    return validated_state_update(
        state,
        candidate_versions=append_unique_records(
            state.candidate_versions, delta.candidate_versions, id_field="candidate_id"
        ),
        active_candidate_id=delta.active_candidate_id,
        retry_budget=delta.retry_budget,
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def apply_repair_finalization_delta(
    state: EnergyChatGraphState, delta: RepairFinalizationDelta
) -> EnergyChatGraphState:
    return validated_state_update(
        state,
        repair_results=append_unique_records(
            state.repair_results, delta.repair_results, id_field="result_id"
        ),
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def _active_evaluation_records(state: EnergyChatGraphState):
    candidate = next(
        item
        for item in state.candidate_versions
        if item.candidate_id == state.active_candidate_id
    )
    score = next(
        item for item in reversed(state.energy_scores) if item.candidate_id == candidate.candidate_id
    )
    decision = next(
        item
        for item in reversed(state.decision_outcomes)
        if item.candidate_id == candidate.candidate_id
    )
    return candidate, score, decision


def _pending_repair_request(state: EnergyChatGraphState) -> RepairRequest:
    applied_targets = {candidate.candidate_id for candidate in state.candidate_versions}
    return next(
        request
        for request in reversed(state.repair_requests)
        if request.target_candidate_id not in applied_targets
    )


def _terminal_result(
    *, repair_id: str, candidate_id: str, energy: int, outcome: str
) -> RepairResultRecord:
    return RepairResultRecord(
        result_id=f"{repair_id}:result",
        repair_id=repair_id,
        source_candidate_id=candidate_id,
        target_candidate_id=candidate_id,
        energy_before=energy,
        energy_after=energy,
        outcome=outcome,  # type: ignore[arg-type]
    )


def _terminal_plan_delta(
    state: EnergyChatGraphState, result: RepairResultRecord
) -> RepairPlanDelta:
    event = build_trace_event(
        state,
        event_type="repair_terminated",
        event_key=f"repair_terminated:{result.result_id}",
        producer="plan_repair",
        payload={"outcome": result.outcome, "repair_id": result.repair_id},
    )
    return RepairPlanDelta(
        repair_results=[result], status="evaluated", trace_events=[event]
    )
