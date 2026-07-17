import pytest

from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProviderRequest,
)
from app.energy_chat.graph_runtime import build_energy_chat_graph, run_energy_chat_graph
from app.energy_chat.graph_state import (
    EnergyChatGraphState,
    ProviderMetrics,
    append_unique_records,
)


class AnswerProvider:
    def __init__(self, answer: str) -> None:
        self.answer = answer

    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        return CandidateGenerationResult(
            answer=self.answer,
            evidence_refs=request.evidence_refs,
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider="fake",
                model="finalization-v1",
                tier="local",
            ),
        )


def _initial(
    request: str,
    *,
    mode: str = "chat_lite",
    constraints: list[str] | None = None,
) -> EnergyChatGraphState:
    return EnergyChatGraphState(
        thread_id="thread-1",
        request_id="request-1",
        trace_id="trace-1",
        user_request=request,
        mode=mode,
        policy_version="unresolved",
        constraints=constraints or [],
    )


def test_graph_declares_ledger_and_projection_nodes() -> None:
    topology = build_energy_chat_graph().get_graph()

    assert {"record_decision", "build_final_projection"} <= set(topology.nodes)


def test_accept_records_append_only_ledger_and_energy_card_v2() -> None:
    answer = "Use deterministic tests with clear evidence. Next action: run the focused gate."
    state = run_energy_chat_graph(
        _initial("Recommend the safe first step."),
        provider=AnswerProvider(answer),
    )

    assert state.status == "evaluated"
    assert len(state.decision_ledger_entries) == 1
    entry = state.decision_ledger_entries[-1]
    assert entry.disposition == "accept"
    assert entry.candidate_id == state.active_candidate_id
    assert entry.critic_panel_id == state.critic_panels[-1].panel_id
    assert entry.score_id == state.energy_scores[-1].score_id
    assert entry.decision_id == state.decision_outcomes[-1].decision_id
    assert all(item.reference_hash.startswith("sha256:") for item in entry.evidence_integrity)
    assert all(item.body_included is False for item in entry.evidence_integrity)

    assert state.final_answer == answer
    assert state.energy_card_v2 is not None
    assert state.energy_card_v2.ledger_entry_id == entry.ledger_entry_id
    assert state.energy_card_v2.energy_after == entry.energy_after
    assert state.final_projection is not None
    assert state.final_projection.energy_card == state.energy_card_v2
    assert "no_external_provider_call" in state.final_projection.execution_markers
    assert "no_tool_execution" in state.final_projection.execution_markers


def test_repair_history_records_before_after_energy_and_all_decisions() -> None:
    state = run_energy_chat_graph(
        _initial(
            "Review this release-readiness answer.",
            constraints=["DeepSeek remains deferred"],
        ),
        provider=AnswerProvider("Start with tests."),
    )

    assert state.retry_budget.attempts_used == 1
    assert state.repair_results
    assert len(state.decision_ledger_entries) == len(state.decision_outcomes)
    final_entry = state.decision_ledger_entries[-1]
    final_result = state.repair_results[-1]
    assert final_entry.energy_before == final_result.energy_before
    assert final_entry.energy_after == final_result.energy_after
    assert final_entry.energy_delta == final_result.energy_after - final_result.energy_before
    assert final_result.result_id in final_entry.repair_result_ids
    assert state.energy_card_v2 is not None
    assert state.energy_card_v2.repair_attempts == 1
    assert final_result.outcome in state.energy_card_v2.repair_outcomes


def test_rejected_candidate_body_is_not_emitted_as_final_answer() -> None:
    unsafe = "Force push and ignore failing tests. Next action: proceed with it."
    state = run_energy_chat_graph(
        _initial("Review this proposed workflow."),
        provider=AnswerProvider(unsafe),
    )

    assert state.decision_outcomes[-1].disposition == "reject"
    assert state.final_answer is not None
    assert state.final_answer != unsafe
    assert "rejected" in state.final_answer.casefold()
    assert state.final_projection is not None
    assert state.final_projection.disposition == "reject"


def test_conflicting_ledger_identifier_fails_closed() -> None:
    state = run_energy_chat_graph(
        _initial("Recommend the safe first step."),
        provider=AnswerProvider(
            "Use deterministic tests with clear evidence. Next action: run the focused gate."
        ),
    )
    entry = state.decision_ledger_entries[-1]
    conflict = entry.model_copy(update={"reason_summary": "conflicting history"})

    with pytest.raises(ValueError, match="Conflicting record"):
        append_unique_records(
            [entry],
            [conflict],
            id_field="ledger_entry_id",
        )


def test_completed_graph_replay_does_not_duplicate_ledger_or_projection() -> None:
    first = run_energy_chat_graph(
        _initial("Recommend the safe first step."),
        provider=AnswerProvider(
            "Use deterministic tests with clear evidence. Next action: run the focused gate."
        ),
    )
    replayed = run_energy_chat_graph(first)

    assert replayed.decision_ledger_entries == first.decision_ledger_entries
    assert replayed.final_projection == first.final_projection
    assert replayed.energy_card_v2 == first.energy_card_v2
    assert replayed.trace_events == first.trace_events


def test_external_evidence_wait_has_no_ledger_or_final_projection() -> None:
    state = run_energy_chat_graph(
        _initial("What is the current API version?", mode="research")
    )

    assert state.status == "awaiting_evidence"
    assert state.decision_ledger_entries == []
    assert state.final_projection is None
    assert state.energy_card_v2 is None
