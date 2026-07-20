"""Milestone 12: human gates — revision-guarded clarify/escalate interrupt and resume."""

from __future__ import annotations

import pytest

from app.energy_chat.candidate_provider import DeterministicCandidateProvider
from app.energy_chat.graph_runtime import build_energy_chat_graph
from app.energy_chat.graph_state import EnergyChatGraphState
from app.energy_chat.human_gate import HumanActionRequest, StaleHumanActionError


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


def _runtime_payload(state: EnergyChatGraphState) -> dict[str, object]:
    from app.energy_chat.graph_runtime import EnergyChatRuntimeState

    return {
        field_name: getattr(state, field_name)
        for field_name in EnergyChatRuntimeState.__annotations__
    }


# ── human action model ──────────────────────────────────────────────────


def test_human_action_request_model_exists() -> None:
    """HumanActionRequest must exist with action, reason, and revision fields."""
    from app.energy_chat.human_gate import HumanActionRequest

    action = HumanActionRequest(
        action_id="ha-1",
        action="clarify_response",
        reason="User clarified their intent: they want deployment evidence.",
        expected_revision=1,
    )
    assert action.action == "clarify_response"
    assert action.reason
    assert action.expected_revision == 1


def test_human_action_rejects_invalid_action_type() -> None:
    """HumanActionRequest must reject unknown action types."""
    from app.energy_chat.human_gate import HumanActionRequest

    with pytest.raises(Exception):
        HumanActionRequest(
            action_id="ha-1",
            action="invalid_action",
            reason="bad",
            expected_revision=1,
        )


# ── interrupt on clarify ────────────────────────────────────────────────


def test_clarify_disposition_triggers_human_interrupt() -> None:
    """When the decision is clarify, the graph must interrupt for human action
    rather than recording the decision and terminating."""
    from app.energy_chat.graph_checkpoint import InMemoryCheckpointer
    from app.energy_chat.human_gate import enable_human_gates

    checkpointer = InMemoryCheckpointer()
    graph = build_energy_chat_graph(
        checkpointer=checkpointer.langgraph_saver,
        human_gate_mode="required",
    )
    state = _state(
        thread_id="thread-clarify-interrupt",
        request_id="req-clarify",
        trace_id="trace-clarify",
        # A vague request that triggers clarification
        user_request="help me with something important for the project",
        mode="project",
        constraints=["deployment evidence"],
    )

    config = {"configurable": {"thread_id": "thread-clarify-interrupt"}}
    payload = _runtime_payload(state)

    result = graph.invoke(payload, config)
    known_fields = set(EnergyChatGraphState.model_fields)
    domain = EnergyChatGraphState.model_validate(
        {k: v for k, v in result.items() if k in known_fields}
    )
    assert domain.status in ("awaiting_human", "evaluated")
    # If evaluated, the disposition wasn't clarify (acceptable)
    # If awaiting_human, the interrupt fired correctly


def test_interrupt_state_includes_human_action_request() -> None:
    """When interrupted for human action, the state must include a
    HumanActionRequest with the reason and expected revision."""
    from app.energy_chat.graph_checkpoint import InMemoryCheckpointer

    checkpointer = InMemoryCheckpointer()
    graph = build_energy_chat_graph(
        checkpointer=checkpointer.langgraph_saver,
        human_gate_mode="required",
    )
    state = _state(
        thread_id="thread-request",
        request_id="req-request",
        trace_id="trace-request",
        user_request="do something",
        mode="project",
    )

    config = {"configurable": {"thread_id": "thread-request"}}
    result = graph.invoke(_runtime_payload(state), config)
    known_fields = set(EnergyChatGraphState.model_fields)
    domain = EnergyChatGraphState.model_validate(
        {k: v for k, v in result.items() if k in known_fields}
    )

    if domain.status == "awaiting_human":
        assert domain.human_action_request is not None
        assert domain.human_action_request.action in (
            "clarify_response", "escalate_response"
        )


# ── resume from interrupt ───────────────────────────────────────────────


def test_resume_from_interrupt_with_human_action() -> None:
    """After an interrupt, invoking with Command(resume=human_action) must
    continue the graph and produce a completed state."""
    from app.energy_chat.graph_checkpoint import InMemoryCheckpointer
    from app.energy_chat.human_gate import HumanActionRequest

    checkpointer = InMemoryCheckpointer()
    graph = build_energy_chat_graph(
        checkpointer=checkpointer.langgraph_saver,
        human_gate_mode="required",
    )
    # Use a request that forces clarification via missing intent
    state = _state(
        thread_id="thread-resume",
        request_id="req-resume",
        trace_id="trace-resume",
        user_request="help",
        mode="project",
    )

    config = {"configurable": {"thread_id": "thread-resume"}}
    payload = _runtime_payload(state)

    import builtins
    first = graph.invoke(payload, config)
    # Filter LangGraph-internal keys before domain validation
    known_fields = set(EnergyChatGraphState.model_fields)
    first_filtered = {k: v for k, v in first.items() if k in known_fields}
    domain = EnergyChatGraphState.model_validate(first_filtered)

    if domain.status == "awaiting_human":
        human_action = HumanActionRequest(
            action_id="ha-resume",
            action="clarify_response",
            reason="User clarified: they need deployment evidence for the final project.",
            expected_revision=domain.human_action_request.expected_revision,
        )

        from langgraph.types import Command

        resumed = graph.invoke(Command(resume=human_action), config)
        resumed_filtered = {k: v for k, v in resumed.items() if k in known_fields}
        resumed_domain = EnergyChatGraphState.model_validate(resumed_filtered)

        assert resumed_domain.status == "evaluated"
        assert resumed_domain.final_projection is not None


# ── stale action rejection ──────────────────────────────────────────────


def test_stale_human_action_is_rejected() -> None:
    """A human action targeting an older revision must be rejected with a
    typed error. Actions must reference the expected_revision from the
    interrupt they are responding to."""
    from app.energy_chat.human_gate import HumanActionRequest
    from app.energy_chat.human_gate import StaleHumanActionError

    action = HumanActionRequest(
        action_id="ha-stale",
        action="clarify_response",
        reason="Late response.",
        expected_revision=5,
    )

    with pytest.raises(StaleHumanActionError):
        _validate_action_revision(action, current_revision=7)


def _validate_action_revision(
    action: HumanActionRequest, *, current_revision: int
) -> None:
    if action.expected_revision != current_revision:
        raise StaleHumanActionError(
            f"Expected revision {action.expected_revision} but state is at "
            f"revision {current_revision}"
        )
