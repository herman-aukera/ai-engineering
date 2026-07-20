"""Milestone 11: in-memory checkpoint proof — thread isolation, replay, and resume."""

from __future__ import annotations

from app.energy_chat.candidate_provider import DeterministicCandidateProvider
from app.energy_chat.graph_runtime import build_energy_chat_graph
from app.energy_chat.graph_state import EnergyChatGraphState


def _state(**overrides: object) -> EnergyChatGraphState:
    values: dict[str, object] = {
        "thread_id": "thread-1",
        "request_id": "request-1",
        "trace_id": "trace-1",
        "user_request": "Explain the safe first implementation step.",
        "mode": "project",
        "policy_version": "unresolved",
        "constraints": ["no secrets"],
    }
    values.update(overrides)
    return EnergyChatGraphState.model_validate(values)


# ── checkpointer existence ──────────────────────────────────────────────


def test_graph_accepts_in_memory_checkpointer() -> None:
    """The compiled graph should accept an in-memory checkpointer without error."""
    from app.energy_chat.graph_checkpoint import InMemoryCheckpointer

    checkpointer = InMemoryCheckpointer()
    graph = build_energy_chat_graph(checkpointer=checkpointer.langgraph_saver)
    assert graph is not None


def test_in_memory_checkpointer_is_independent_per_thread() -> None:
    """Each thread_id should produce an independent checkpoint lineage."""
    from app.energy_chat.graph_checkpoint import InMemoryCheckpointer

    checkpointer = InMemoryCheckpointer()
    graph = build_energy_chat_graph(checkpointer=checkpointer.langgraph_saver)

    state_a = _state(thread_id="thread-a", request_id="req-a", trace_id="trace-a")
    state_b = _state(thread_id="thread-b", request_id="req-b", trace_id="trace-b")

    result_a = graph.invoke(
        _runtime_payload(state_a),
        {"configurable": {"thread_id": "thread-a"}},
    )
    result_b = graph.invoke(
        _runtime_payload(state_b),
        {"configurable": {"thread_id": "thread-b"}},
    )

    domain_a = EnergyChatGraphState.model_validate(result_a)
    domain_b = EnergyChatGraphState.model_validate(result_b)

    assert domain_a.thread_id == "thread-a"
    assert domain_b.thread_id == "thread-b"
    assert domain_a.request_id == "req-a"
    assert domain_b.request_id == "req-b"


# ── replay idempotency ──────────────────────────────────────────────────


def test_replay_same_thread_is_idempotent() -> None:
    """Invoking the same thread_id with the same initial state twice must not
    produce duplicate ledger entries or provider calls."""
    from app.energy_chat.graph_checkpoint import InMemoryCheckpointer

    checkpointer = InMemoryCheckpointer()
    graph = build_energy_chat_graph(checkpointer=checkpointer.langgraph_saver)
    provider = DeterministicCandidateProvider()
    state = _state()

    config = {"configurable": {"thread_id": "thread-replay"}}
    payload = _runtime_payload(state)

    first = EnergyChatGraphState.model_validate(graph.invoke(payload, config))
    second = EnergyChatGraphState.model_validate(graph.invoke(payload, config))

    # ledger entries must be identical, not duplicated
    assert len(first.decision_ledger_entries) == len(second.decision_ledger_entries)
    assert [e.ledger_entry_id for e in first.decision_ledger_entries] == [
        e.ledger_entry_id for e in second.decision_ledger_entries
    ]
    # candidate count must not grow
    assert len(first.candidate_versions) == len(second.candidate_versions)


# ── checkpoint retrieval ────────────────────────────────────────────────


def test_can_retrieve_checkpoint_after_graph_run() -> None:
    """After a graph run completes, the checkpointer must be able to return
    the stored state for that thread."""
    from app.energy_chat.graph_checkpoint import InMemoryCheckpointer

    checkpointer = InMemoryCheckpointer()
    graph = build_energy_chat_graph(checkpointer=checkpointer.langgraph_saver)
    state = _state()

    config = {"configurable": {"thread_id": "thread-retrieve"}}
    result = graph.invoke(_runtime_payload(state), config)
    domain = EnergyChatGraphState.model_validate(result)

    # retrieve via the graph's get_state
    retrieved = graph.get_state(config)
    assert retrieved is not None
    assert retrieved.values is not None
    retrieved_domain = EnergyChatGraphState.model_validate(retrieved.values)
    assert retrieved_domain.thread_id == domain.thread_id
    assert retrieved_domain.status == domain.status


# ── resume from awaiting evidence ───────────────────────────────────────


def test_awaiting_evidence_state_is_recoverable() -> None:
    """A thread that stopped at awaiting_evidence must be retrievable and its
    state must report the correct status and no fabricated output."""
    from app.energy_chat.graph_checkpoint import InMemoryCheckpointer

    checkpointer = InMemoryCheckpointer()
    graph = build_energy_chat_graph(checkpointer=checkpointer.langgraph_saver)
    state = _state(
        thread_id="thread-wait",
        request_id="req-wait",
        trace_id="trace-wait",
        user_request="What is the latest pricing for DeepSeek as of today?",
        mode="research",
    )

    config = {"configurable": {"thread_id": "thread-wait"}}
    result = graph.invoke(_runtime_payload(state), config)
    domain = EnergyChatGraphState.model_validate(result)

    assert domain.status == "awaiting_evidence"
    assert domain.final_answer is None
    assert domain.energy_card_v2 is None
    assert len(domain.candidate_versions) == 0

    # verify checkpoint is stored
    retrieved = graph.get_state(config)
    assert retrieved is not None
    retrieved_domain = EnergyChatGraphState.model_validate(retrieved.values)
    assert retrieved_domain.status == "awaiting_evidence"


# ── no duplicate provider calls on replay ───────────────────────────────


def test_provider_not_called_again_on_replay(monkeypatch) -> None:
    """When replaying a completed thread, the provider must not be called again."""
    from app.energy_chat.graph_checkpoint import InMemoryCheckpointer

    call_count = 0

    class CountingProvider:
        def generate(self, request):
            nonlocal call_count
            call_count += 1
            return DeterministicCandidateProvider().generate(request)

    checkpointer = InMemoryCheckpointer()
    graph = build_energy_chat_graph(checkpointer=checkpointer.langgraph_saver)
    provider = CountingProvider()
    state = _state(thread_id="thread-no-double-call")

    config = {"configurable": {"thread_id": "thread-no-double-call"}}
    payload = _runtime_payload(state)

    first = graph.invoke(payload, config)
    assert call_count == 1

    second = graph.invoke(payload, config)
    # replay must not trigger another provider call
    assert call_count == 1

    first_domain = EnergyChatGraphState.model_validate(first)
    second_domain = EnergyChatGraphState.model_validate(second)
    assert first_domain.final_answer == second_domain.final_answer


# ── helpers ─────────────────────────────────────────────────────────────


def _runtime_payload(state: EnergyChatGraphState) -> dict[str, object]:
    from app.energy_chat.graph_runtime import EnergyChatRuntimeState

    return {
        field_name: getattr(state, field_name)
        for field_name in EnergyChatRuntimeState.__annotations__
    }
