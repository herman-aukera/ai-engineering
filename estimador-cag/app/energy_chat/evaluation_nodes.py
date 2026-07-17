"""Candidate-linked critic, energy, and decision nodes."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.energy_chat.contracts import EnergyChatRequest, EnergyPolicy
from app.energy_chat.critics import run_chat_lite_critics
from app.energy_chat.decider import decide
from app.energy_chat.graph_state import (
    CriticPanelRecord,
    DecisionOutcome,
    EnergyChatGraphState,
    EnergyScoreRecord,
    GraphStateRecord,
    TraceEvent,
    append_unique_records,
    build_trace_event,
    validated_state_update,
)
from app.energy_chat.policies import default_chat_lite_policy
from app.energy_chat.scorer import score_findings
from app.energy_chat.source_guard import source_need_findings

CRITIC_PANEL_VERSION = "energy-chat-deterministic-critics-v1"


class CriticDelta(GraphStateRecord):
    """Fields owned by the deterministic critic panel node."""

    critic_panels: list[CriticPanelRecord] = Field(min_length=1, max_length=1)
    status: Literal["criticized"] = "criticized"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


class ScoreDelta(GraphStateRecord):
    """Fields owned by the authoritative energy calculation node."""

    energy_scores: list[EnergyScoreRecord] = Field(min_length=1, max_length=1)
    status: Literal["scored"] = "scored"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


class DecisionDelta(GraphStateRecord):
    """Fields owned by the authoritative deterministic decision node."""

    decision_outcomes: list[DecisionOutcome] = Field(min_length=1, max_length=1)
    status: Literal["evaluated"] = "evaluated"
    trace_events: list[TraceEvent] = Field(min_length=1, max_length=1)


def run_critic_panel(
    state: EnergyChatGraphState, policy: EnergyPolicy | None = None
) -> CriticDelta:
    """Evaluate the active candidate with the existing deterministic critics."""

    candidate = _active_candidate(state)
    active_policy = _active_policy(state, policy)
    panel_id = f"{candidate.candidate_id}:critic-panel:{CRITIC_PANEL_VERSION}"
    retained = next((panel for panel in state.critic_panels if panel.panel_id == panel_id), None)
    if retained is None:
        request = EnergyChatRequest(
            user_message=state.user_request,
            draft_answer=candidate.answer,
            mode=state.mode,
            required_constraints=state.constraints,
            evidence_refs=candidate.evidence_refs,
        )
        findings = [
            *run_chat_lite_critics(request, active_policy),
            *source_need_findings(request, active_policy),
        ]
        retained = CriticPanelRecord(
            panel_id=panel_id,
            candidate_id=candidate.candidate_id,
            critic_version=CRITIC_PANEL_VERSION,
            findings=findings,
        )
    event = build_trace_event(
        state,
        event_type="critic_panel_completed",
        event_key=f"critic_panel_completed:{panel_id}",
        producer="run_critic_panel",
        payload={
            "candidate_id": candidate.candidate_id,
            "critic_version": CRITIC_PANEL_VERSION,
            "finding_count": len(retained.findings),
        },
    )
    return CriticDelta(critic_panels=[retained], trace_events=[event])


def calculate_energy(
    state: EnergyChatGraphState, policy: EnergyPolicy | None = None
) -> ScoreDelta:
    """Calculate authoritative energy for the active candidate's retained panel."""

    candidate = _active_candidate(state)
    active_policy = _active_policy(state, policy)
    panel = _panel_for_active_candidate(state, candidate.candidate_id)
    score_id = f"{candidate.candidate_id}:score:{active_policy.version}"
    retained = next((score for score in state.energy_scores if score.score_id == score_id), None)
    if retained is None:
        retained = EnergyScoreRecord(
            score_id=score_id,
            candidate_id=candidate.candidate_id,
            policy_version=active_policy.version,
            score=score_findings(panel.findings),
        )
    event = build_trace_event(
        state,
        event_type="energy_calculated",
        event_key=f"energy_calculated:{score_id}",
        producer="calculate_energy",
        payload={
            "candidate_id": candidate.candidate_id,
            "policy_version": active_policy.version,
            "score_id": score_id,
            "total_energy": retained.score.total_energy,
        },
    )
    return ScoreDelta(energy_scores=[retained], trace_events=[event])


def decide_candidate(
    state: EnergyChatGraphState, policy: EnergyPolicy | None = None
) -> DecisionDelta:
    """Apply the existing deterministic decider to the active candidate's score."""

    candidate = _active_candidate(state)
    active_policy = _active_policy(state, policy)
    score = _score_for_active_candidate(state, candidate.candidate_id, active_policy.version)
    decision_id = f"{candidate.candidate_id}:decision:{score.score_id}"
    retained = next(
        (outcome for outcome in state.decision_outcomes if outcome.decision_id == decision_id),
        None,
    )
    if retained is None:
        domain_decision = decide(score.score, active_policy, candidate.evidence_refs)
        retained = DecisionOutcome(
            decision_id=decision_id,
            candidate_id=candidate.candidate_id,
            score_id=score.score_id,
            disposition=domain_decision.decision,
            reason=domain_decision.reasoning_summary,
            required_repairs=domain_decision.required_repairs,
            evidence_refs=domain_decision.evidence_refs,
        )
    event = build_trace_event(
        state,
        event_type="candidate_decided",
        event_key=f"candidate_decided:{decision_id}",
        producer="decide_candidate",
        payload={
            "candidate_id": candidate.candidate_id,
            "decision_id": decision_id,
            "disposition": retained.disposition,
            "score_id": score.score_id,
        },
    )
    return DecisionDelta(decision_outcomes=[retained], trace_events=[event])


def apply_critic_delta(state: EnergyChatGraphState, delta: CriticDelta) -> EnergyChatGraphState:
    """Append critic history and project the active panel's findings."""

    return validated_state_update(
        state,
        critic_panels=append_unique_records(
            state.critic_panels, delta.critic_panels, id_field="panel_id"
        ),
        critic_findings=delta.critic_panels[0].findings,
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def apply_score_delta(state: EnergyChatGraphState, delta: ScoreDelta) -> EnergyChatGraphState:
    """Append immutable candidate-linked score history."""

    return validated_state_update(
        state,
        energy_scores=append_unique_records(
            state.energy_scores, delta.energy_scores, id_field="score_id"
        ),
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def apply_decision_delta(
    state: EnergyChatGraphState, delta: DecisionDelta
) -> EnergyChatGraphState:
    """Append immutable candidate-linked deterministic decision history."""

    return validated_state_update(
        state,
        decision_outcomes=append_unique_records(
            state.decision_outcomes, delta.decision_outcomes, id_field="decision_id"
        ),
        status=delta.status,
        trace_events=append_unique_records(
            state.trace_events, delta.trace_events, id_field="event_id"
        ),
    )


def _active_candidate(state: EnergyChatGraphState):
    if state.active_candidate_id is None:
        raise ValueError("Evaluation requires an active candidate")
    return next(
        candidate
        for candidate in state.candidate_versions
        if candidate.candidate_id == state.active_candidate_id
    )


def _active_policy(state: EnergyChatGraphState, policy: EnergyPolicy | None) -> EnergyPolicy:
    active = policy or default_chat_lite_policy()
    if state.policy_version != active.version:
        raise ValueError("State policy version does not match the active policy")
    return active


def _panel_for_active_candidate(
    state: EnergyChatGraphState, candidate_id: str
) -> CriticPanelRecord:
    matches = [panel for panel in state.critic_panels if panel.candidate_id == candidate_id]
    if not matches:
        raise ValueError("No critic panel exists for the active candidate")
    return matches[-1]


def _score_for_active_candidate(
    state: EnergyChatGraphState, candidate_id: str, policy_version: str
) -> EnergyScoreRecord:
    matches = [
        score
        for score in state.energy_scores
        if score.candidate_id == candidate_id and score.policy_version == policy_version
    ]
    if not matches:
        raise ValueError("No energy score exists for the active candidate and policy")
    return matches[-1]
