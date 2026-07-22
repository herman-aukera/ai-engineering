"""Authoritative approve, adjust, and reject policy for protected chat outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.energy_chat.evaluation_nodes import (
    apply_critic_delta,
    apply_decision_delta,
    apply_score_delta,
    calculate_energy,
    decide_candidate,
    run_critic_panel,
)
from app.energy_chat.evidence_hardening import validate_candidate_citations
from app.energy_chat.finalization_nodes import (
    apply_decision_ledger_delta,
    apply_final_projection_delta,
    build_final_projection,
    record_decision,
)
from app.energy_chat.graph_state import (
    CandidateVersion,
    DecisionOutcome,
    EnergyChatGraphState,
    append_unique_records,
    build_trace_event,
    validated_state_update,
)
from app.energy_chat.human_gate import HumanActionRequest


@dataclass(frozen=True)
class HumanAuthorityResult:
    """Post-review domain state and the minimal reducer-safe checkpoint update."""

    state: EnergyChatGraphState
    checkpoint_update: dict[str, Any]


def apply_human_authority(
    state: EnergyChatGraphState,
    action: HumanActionRequest,
) -> HumanAuthorityResult:
    """Apply one validated human decision and persist only authoritative deltas."""

    if action.decision is None:
        raise ValueError("Human authority requires approve, adjust, or reject")
    event = build_trace_event(
        state,
        event_type="human_authority_applied",
        event_key=f"human_authority_applied:{action.action_id}:{action.idempotency_key}",
        producer="human_authority",
        payload={
            "action_id": action.action_id,
            "decision": action.decision,
            "actor": action.actor,
            "expected_revision": action.expected_revision,
        },
    )
    reviewed = validated_state_update(
        state,
        human_action_result=action,
        status="evaluated",
        trace_events=append_unique_records(
            state.trace_events,
            [event],
            id_field="event_id",
        ),
    )
    if action.decision == "approve":
        completed = reviewed.model_copy(update={"status": "completed"})
        return HumanAuthorityResult(
            state=completed,
            checkpoint_update={
                "human_action_result": action,
                "status": "completed",
                "trace_events": [event],
            },
        )
    if action.decision == "reject":
        return _reject(reviewed, action, event)
    return _adjust(reviewed, action, event)


def _reject(
    state: EnergyChatGraphState,
    action: HumanActionRequest,
    authority_event,
) -> HumanAuthorityResult:
    if state.active_candidate_id is None:
        raise ValueError("Human rejection requires an active candidate")
    score = next(
        item
        for item in reversed(state.energy_scores)
        if item.candidate_id == state.active_candidate_id
    )
    source = next(
        item
        for item in reversed(state.decision_outcomes)
        if item.candidate_id == state.active_candidate_id
    )
    decision = DecisionOutcome(
        decision_id=f"{source.decision_id}:human-reject:{action.expected_revision}",
        candidate_id=state.active_candidate_id,
        score_id=score.score_id,
        disposition="reject",
        reason=f"Human reviewer rejected the protected outcome: {action.decision_reason}",
        evidence_refs=source.evidence_refs,
        policy_rule_id="human_authority_reject_v1",
    )
    decided = validated_state_update(
        state,
        decision_outcomes=append_unique_records(
            state.decision_outcomes,
            [decision],
            id_field="decision_id",
        ),
    )
    return _finalize_authority(
        original=state,
        evaluated=decided,
        action=action,
        authority_event=authority_event,
        new_candidate=None,
        new_citation=None,
        new_panel=None,
        new_score=None,
        new_decision=decision,
    )


def _adjust(
    state: EnergyChatGraphState,
    action: HumanActionRequest,
    authority_event,
) -> HumanAuthorityResult:
    if action.adjustments is None:
        raise ValueError("Adjust requires a typed revised answer")
    if state.active_candidate_id is None:
        raise ValueError("Human adjustment requires an active candidate")
    source = next(
        item for item in state.candidate_versions if item.candidate_id == state.active_candidate_id
    )
    version = max(item.version for item in state.candidate_versions) + 1
    candidate = CandidateVersion(
        candidate_id=(
            f"{state.request_id}:candidate:human-adjust:"
            f"{action.expected_revision}:{action.idempotency_key}"
        ),
        version=version,
        answer=action.adjustments.revised_answer,
        producer="human_authority",
        evidence_refs=source.evidence_refs,
        provider_call_id=None,
    )
    citation = validate_candidate_citations(
        candidate_id=candidate.candidate_id,
        answer_text=candidate.answer,
        known_evidence_refs=candidate.evidence_refs,
    )
    adjusted = validated_state_update(
        state,
        candidate_versions=append_unique_records(
            state.candidate_versions,
            [candidate],
            id_field="candidate_id",
        ),
        active_candidate_id=candidate.candidate_id,
        citation_validations=append_unique_records(
            state.citation_validations,
            [citation],
            id_field="candidate_id",
        ),
        status="candidate_ready",
    )
    critic_delta = run_critic_panel(adjusted)
    criticized = apply_critic_delta(adjusted, critic_delta)
    score_delta = calculate_energy(criticized)
    scored = apply_score_delta(criticized, score_delta)
    decision_delta = decide_candidate(scored)
    evaluated = apply_decision_delta(scored, decision_delta)
    return _finalize_authority(
        original=state,
        evaluated=evaluated,
        action=action,
        authority_event=authority_event,
        new_candidate=candidate,
        new_citation=citation,
        new_panel=critic_delta.critic_panels[0],
        new_score=score_delta.energy_scores[0],
        new_decision=decision_delta.decision_outcomes[0],
        evaluation_events=[
            *critic_delta.trace_events,
            *score_delta.trace_events,
            *decision_delta.trace_events,
        ],
    )


def _finalize_authority(
    *,
    original: EnergyChatGraphState,
    evaluated: EnergyChatGraphState,
    action: HumanActionRequest,
    authority_event,
    new_candidate,
    new_citation,
    new_panel,
    new_score,
    new_decision,
    evaluation_events: list | None = None,
) -> HumanAuthorityResult:
    ledger_delta = record_decision(evaluated)
    ledger_state = apply_decision_ledger_delta(evaluated, ledger_delta)
    projection_delta = build_final_projection(ledger_state)
    finalized = apply_final_projection_delta(ledger_state, projection_delta).model_copy(
        update={"status": "completed", "human_action_result": action}
    )
    existing_ledger_ids = {
        item.ledger_entry_id for item in original.decision_ledger_entries
    }
    new_ledger_entries = [
        item
        for item in ledger_delta.decision_ledger_entries
        if item.ledger_entry_id not in existing_ledger_ids
    ]
    trace_events = [
        authority_event,
        *(evaluation_events or []),
        *ledger_delta.trace_events,
        *projection_delta.trace_events,
    ]
    update: dict[str, Any] = {
        "human_action_result": action,
        "decision_outcomes": [new_decision],
        "decision_ledger_entries": new_ledger_entries,
        "final_answer": projection_delta.final_answer,
        "energy_card": projection_delta.energy_card,
        "energy_card_v2": projection_delta.energy_card_v2,
        "final_projection": projection_delta.final_projection,
        "status": "completed",
        "trace_events": trace_events,
    }
    if new_candidate is not None:
        update.update(
            {
                "candidate_versions": [new_candidate],
                "active_candidate_id": new_candidate.candidate_id,
                "citation_validations": [new_citation],
                "critic_panels": [new_panel],
                "critic_findings": new_panel.findings,
                "energy_scores": [new_score],
            }
        )
    return HumanAuthorityResult(state=finalized, checkpoint_update=update)
