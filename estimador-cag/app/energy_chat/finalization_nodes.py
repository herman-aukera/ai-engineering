"""Deterministic decision-ledger and user-safe final projection nodes."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import Field

from app.energy_chat.audit_models import (
    DecisionLedgerEntry,
    EnergyCardV2,
    EvidenceIntegrityMetadata,
    FinalAnswerProjection,
)
from app.energy_chat.contracts import EnergyCard
from app.energy_chat.evidence_hardening import check_evidence_freshness
from app.energy_chat.graph_state import (
    DecisionOutcome,
    EnergyChatGraphState,
    GraphStateRecord,
    TraceEvent,
    append_unique_records,
    append_unique_values,
    build_trace_event,
    validated_state_update,
)


class DecisionLedgerDelta(GraphStateRecord):
    decision_ledger_entries: list[DecisionLedgerEntry] = Field(min_length=1)
    status: Literal["evaluated"] = "evaluated"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


class FinalProjectionDelta(GraphStateRecord):
    final_answer: str = Field(min_length=1)
    energy_card: EnergyCard
    energy_card_v2: EnergyCardV2
    final_projection: FinalAnswerProjection
    status: Literal["evaluated"] = "evaluated"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


def record_decision(state: EnergyChatGraphState) -> DecisionLedgerDelta:
    if not state.decision_outcomes:
        raise ValueError("Decision ledger requires at least one authoritative decision")
    entries = [
        _build_ledger_entry(state, decision, sequence=index)
        for index, decision in enumerate(state.decision_outcomes, start=1)
    ]
    final_entry = entries[-1]
    event = build_trace_event(
        state,
        event_type="decision_ledger_recorded",
        event_key=f"decision_ledger_recorded:{final_entry.ledger_entry_id}",
        producer="record_decision",
        payload={
            "entry_count": len(entries),
            "final_disposition": final_entry.disposition,
            "final_ledger_entry_id": final_entry.ledger_entry_id,
            "evidence_integrity_count": len(final_entry.evidence_integrity),
        },
    )
    return DecisionLedgerDelta(decision_ledger_entries=entries, trace_events=[event])


def build_final_projection(state: EnergyChatGraphState) -> FinalProjectionDelta:
    if not state.decision_ledger_entries:
        raise ValueError("Final projection requires a decision-ledger entry")
    if state.active_candidate_id is None:
        raise ValueError("Final projection requires an active candidate")

    candidate = next(
        item for item in state.candidate_versions if item.candidate_id == state.active_candidate_id
    )
    entry = next(
        item
        for item in reversed(state.decision_ledger_entries)
        if item.candidate_id == candidate.candidate_id
    )
    repair_outcomes = [result.outcome for result in state.repair_results]
    card_v2 = EnergyCardV2(
        ledger_entry_id=entry.ledger_entry_id,
        candidate_id=entry.candidate_id,
        decision=entry.disposition,
        policy_version=entry.policy_version,
        policy_rule_id=entry.policy_rule_id,
        hard_constraints_passed=not entry.hard_reject_violations,
        hard_constraint_violations=[
            *entry.hard_reject_violations,
            *entry.hard_repair_violations,
        ],
        soft_quality_findings=entry.soft_violations,
        energy_before=entry.energy_before,
        energy_after=entry.energy_after,
        energy_delta=entry.energy_delta,
        repair_attempts=state.retry_budget.attempts_used,
        repair_outcomes=repair_outcomes,
        evidence_refs=entry.evidence_refs,
        reason_summary=entry.reason_summary,
        limitations=entry.limitations,
    )
    final_answer = _safe_final_answer(candidate.answer, entry)
    legacy_card = EnergyCard(
        decision=entry.disposition,
        energy=entry.energy_after,
        hard_constraints_passed=card_v2.hard_constraints_passed,
        repairs=state.retry_budget.attempts_used,
        evidence=entry.evidence_refs or ["policy", "critic_results"],
        remaining_caveats=entry.limitations,
    )
    projection = FinalAnswerProjection(
        ledger_entry_id=entry.ledger_entry_id,
        candidate_id=entry.candidate_id,
        disposition=entry.disposition,
        answer=final_answer,
        energy_card=card_v2,
        execution_markers=_execution_markers(state),
    )
    event = build_trace_event(
        state,
        event_type="final_answer_projected",
        event_key=f"final_answer_projected:{entry.ledger_entry_id}",
        producer="build_final_projection",
        payload={
            "candidate_id": candidate.candidate_id,
            "disposition": entry.disposition,
            "ledger_entry_id": entry.ledger_entry_id,
        },
    )
    return FinalProjectionDelta(
        final_answer=final_answer,
        energy_card=legacy_card,
        energy_card_v2=card_v2,
        final_projection=projection,
        trace_events=[event],
    )


def apply_decision_ledger_delta(
    state: EnergyChatGraphState, delta: DecisionLedgerDelta
) -> EnergyChatGraphState:
    return validated_state_update(
        state,
        decision_ledger_entries=append_unique_records(
            state.decision_ledger_entries,
            delta.decision_ledger_entries,
            id_field="ledger_entry_id",
        ),
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def apply_final_projection_delta(
    state: EnergyChatGraphState, delta: FinalProjectionDelta
) -> EnergyChatGraphState:
    return validated_state_update(
        state,
        final_answer=delta.final_answer,
        energy_card=delta.energy_card,
        energy_card_v2=delta.energy_card_v2,
        final_projection=delta.final_projection,
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def _build_ledger_entry(
    state: EnergyChatGraphState,
    decision: DecisionOutcome,
    *,
    sequence: int,
) -> DecisionLedgerEntry:
    candidate = next(
        item for item in state.candidate_versions if item.candidate_id == decision.candidate_id
    )
    panel = next(
        item
        for item in reversed(state.critic_panels)
        if item.candidate_id == candidate.candidate_id
    )
    score = next(item for item in state.energy_scores if item.score_id == decision.score_id)
    evidence_refs = append_unique_values(candidate.evidence_refs, decision.evidence_refs)
    repair_requests = [
        item
        for item in state.repair_requests
        if item.candidate_id == candidate.candidate_id
        or item.target_candidate_id == candidate.candidate_id
    ]
    repair_results = [
        item
        for item in state.repair_results
        if item.source_candidate_id == candidate.candidate_id
        or item.target_candidate_id == candidate.candidate_id
    ]
    energy_before = _energy_before(state, candidate.candidate_id, score.score.total_energy)
    provider_call_ids = [candidate.provider_call_id] if candidate.provider_call_id else []
    return DecisionLedgerEntry(
        ledger_entry_id=f"{decision.decision_id}:ledger:v1",
        sequence=sequence,
        thread_id=state.thread_id,
        request_id=state.request_id,
        trace_id=state.trace_id,
        candidate_id=candidate.candidate_id,
        critic_panel_id=panel.panel_id,
        score_id=score.score_id,
        decision_id=decision.decision_id,
        policy_version=score.policy_version,
        policy_rule_id=decision.policy_rule_id,
        disposition=decision.disposition,
        reason_summary=decision.reason,
        energy_before=energy_before,
        energy_after=score.score.total_energy,
        energy_delta=score.score.total_energy - energy_before,
        hard_reject_violations=score.score.hard_reject_violations,
        hard_repair_violations=score.score.hard_repair_violations,
        soft_violations=score.score.soft_violations,
        evidence_refs=evidence_refs,
        evidence_integrity=[
            _evidence_integrity(state, evidence_ref) for evidence_ref in evidence_refs
        ],
        provider_call_ids=provider_call_ids,
        repair_request_ids=[item.repair_id for item in repair_requests],
        repair_result_ids=[item.result_id for item in repair_results],
        limitations=_limitations(state, decision),
    )


def _energy_before(state: EnergyChatGraphState, candidate_id: str, fallback: int) -> int:
    repair_request = next(
        (
            item
            for item in reversed(state.repair_requests)
            if item.target_candidate_id == candidate_id
        ),
        None,
    )
    if repair_request is None:
        return fallback
    source_score = next(
        item
        for item in reversed(state.energy_scores)
        if item.candidate_id == repair_request.candidate_id
    )
    return source_score.score.total_energy


def _evidence_integrity(
    state: EnergyChatGraphState,
    evidence_ref: str,
) -> EvidenceIntegrityMetadata:
    reference_hash = f"sha256:{hashlib.sha256(evidence_ref.encode('utf-8')).hexdigest()}"
    trusted = evidence_ref.startswith(("source:", "git:", "test:", "ci:", "file:"))
    body_metadata = next(
        (
            item
            for item in state.evidence_body_metadata
            if item.evidence_ref == evidence_ref
        ),
        None,
    )
    freshness = (
        body_metadata.freshness_status
        if body_metadata is not None
        else check_evidence_freshness(evidence_ref=evidence_ref)
    )
    return EvidenceIntegrityMetadata(
        evidence_ref=evidence_ref,
        reference_hash=reference_hash,
        trust_status="trusted" if trusted else "unknown",
        freshness_status=freshness,
        redaction_status="reference_only",
        body_hash=body_metadata.body_hash if body_metadata else None,
        body_hash_status=(
            body_metadata.body_hash_status if body_metadata else "unavailable"
        ),
        verification_status=(
            body_metadata.verification_status if body_metadata else "not_checked"
        ),
        byte_count=body_metadata.byte_count if body_metadata else None,
    )


def _limitations(state: EnergyChatGraphState, decision: DecisionOutcome) -> list[str]:
    limitations: list[str] = []
    if decision.disposition == "clarify":
        limitations.append("Material user intent is still missing and requires clarification.")
    elif decision.disposition == "reject":
        limitations.append("The evaluated candidate is not safe or valid to present as the answer.")
    elif decision.disposition == "refuse":
        limitations.append("The request is declined by the recorded request-policy rule.")
    elif decision.disposition == "escalate":
        limitations.append("An accountable human decision is required before continuation.")
    elif decision.disposition == "repair":
        limitations.append("The candidate still requires a repair that was not completed safely.")
    if state.source_need is not None and state.source_need.missing_evidence:
        limitations.append("Required evidence remains missing.")
    if any(result.outcome == "no_improvement" for result in state.repair_results):
        limitations.append("The attempted repair did not reduce constraint energy.")
    citation_validation = next(
        (
            item.validation
            for item in state.citation_validations
            if item.candidate_id == decision.candidate_id
        ),
        None,
    )
    if citation_validation and citation_validation.has_fabricated_citations:
        limitations.append(
            "The candidate contained citation references that were not present in the evidence allow-list."
        )
    if any(item.freshness_status == "stale" for item in state.evidence_body_metadata):
        limitations.append("At least one evidence item is stale under the active freshness policy.")
    return list(dict.fromkeys(limitations))


def _safe_final_answer(candidate_answer: str, entry: DecisionLedgerEntry) -> str:
    if entry.disposition == "accept":
        return candidate_answer.strip()
    if entry.disposition == "reject":
        return (
            "The generated candidate was rejected because it violated a hard constraint. "
            f"{entry.reason_summary}"
        ).strip()
    if entry.disposition == "repair":
        return f"The candidate still requires repair. {entry.reason_summary}".strip()
    return entry.reason_summary.strip()


def _execution_markers(state: EnergyChatGraphState) -> list[str]:
    external = any(
        item.provider not in {"deterministic_local", "fake"}
        for item in state.provider_metrics
    )
    markers = [
        "external_provider_called" if external else "no_external_provider_call",
        "no_tool_execution",
    ]
    if state.node_spans:
        markers.append("graph_node_spans_recorded")
    if state.evidence_body_metadata:
        markers.append("evidence_integrity_recorded")
    return markers
