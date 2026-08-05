import pytest

from app.energy_chat.candidate_node import apply_candidate_delta, generate_candidate
from app.energy_chat.candidate_provider import DeterministicCandidateProvider
from app.energy_chat.contracts import EnergyChatRequest
from app.energy_chat.evaluation_nodes import (
    apply_critic_delta,
    apply_decision_delta,
    apply_score_delta,
    calculate_energy,
    decide_candidate,
    run_critic_panel,
)
from app.energy_chat.evaluator import run_evaluation
from app.energy_chat.graph_state import CandidateVersion, EnergyChatGraphState


def _candidate_state() -> EnergyChatGraphState:
    initial = EnergyChatGraphState(
        thread_id="thread-1",
        request_id="request-1",
        trace_id="trace-1",
        user_request="Should this release proceed?",
        mode="project",
        policy_version="1.0.0",
        constraints=["mention rollback"],
        evidence_refs=["git:clean", "test:484-passed"],
        status="evidence_ready",
    )
    return apply_candidate_delta(
        initial,
        generate_candidate(initial, provider=DeterministicCandidateProvider()),
    )


def test_evaluation_nodes_preserve_current_evaluator_behavior() -> None:
    candidate_state = _candidate_state()
    criticized = apply_critic_delta(candidate_state, run_critic_panel(candidate_state))
    scored = apply_score_delta(criticized, calculate_energy(criticized))
    decided = apply_decision_delta(scored, decide_candidate(scored))
    candidate = candidate_state.candidate_versions[0]
    expected = run_evaluation(
        EnergyChatRequest(
            user_message=candidate_state.user_request,
            draft_answer=candidate.answer,
            mode=candidate_state.mode,
            required_constraints=candidate_state.constraints,
            evidence_refs=candidate.evidence_refs,
        )
    )

    panel = decided.critic_panels[0]
    score = decided.energy_scores[0]
    outcome = decided.decision_outcomes[0]
    assert panel.candidate_id == candidate.candidate_id
    assert panel.findings == expected.score.findings
    assert score.score == expected.score
    assert score.policy_version == expected.policy.version
    assert outcome.disposition == expected.decision.decision
    assert outcome.reason == expected.decision.reasoning_summary
    assert outcome.required_repairs == expected.decision.required_repairs
    assert outcome.evidence_refs == expected.decision.evidence_refs
    assert decided.status == "evaluated"


def test_score_rejects_panel_for_stale_candidate() -> None:
    candidate_state = _candidate_state()
    criticized = apply_critic_delta(candidate_state, run_critic_panel(candidate_state))
    second = CandidateVersion(
        candidate_id="request-1:candidate:2",
        version=2,
        answer="Second candidate",
        producer="repair_candidate",
    )
    stale = EnergyChatGraphState.model_validate(
        {
            **criticized.model_dump(mode="python"),
            "candidate_versions": [*criticized.candidate_versions, second],
            "active_candidate_id": second.candidate_id,
        }
    )

    with pytest.raises(ValueError, match="active candidate"):
        calculate_energy(stale)


def test_decision_rejects_score_for_stale_candidate() -> None:
    candidate_state = _candidate_state()
    criticized = apply_critic_delta(candidate_state, run_critic_panel(candidate_state))
    scored = apply_score_delta(criticized, calculate_energy(criticized))
    second = CandidateVersion(
        candidate_id="request-1:candidate:2",
        version=2,
        answer="Second candidate",
        producer="repair_candidate",
    )
    stale = EnergyChatGraphState.model_validate(
        {
            **scored.model_dump(mode="python"),
            "candidate_versions": [*scored.candidate_versions, second],
            "active_candidate_id": second.candidate_id,
        }
    )

    with pytest.raises(ValueError, match="active candidate"):
        decide_candidate(stale)


def test_evaluation_node_replay_is_idempotent() -> None:
    candidate_state = _candidate_state()
    criticized = apply_critic_delta(candidate_state, run_critic_panel(candidate_state))
    criticized = apply_critic_delta(criticized, run_critic_panel(criticized))
    scored = apply_score_delta(criticized, calculate_energy(criticized))
    scored = apply_score_delta(scored, calculate_energy(scored))
    decided = apply_decision_delta(scored, decide_candidate(scored))
    replayed = apply_decision_delta(decided, decide_candidate(decided))

    assert replayed == decided
    assert len(replayed.critic_panels) == 1
    assert len(replayed.energy_scores) == 1
    assert len(replayed.decision_outcomes) == 1
    assert [event.sequence for event in replayed.trace_events] == [1, 2, 3, 4]
