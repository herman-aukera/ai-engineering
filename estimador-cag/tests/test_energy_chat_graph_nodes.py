from app.energy_chat.graph_nodes import (
    apply_interpretation_delta,
    apply_policy_delta,
    interpret_request,
    load_policy_and_constraints,
)
from app.energy_chat.graph_state import EnergyChatGraphState
from app.energy_chat.policies import default_chat_lite_policy


def _state(**updates: object) -> EnergyChatGraphState:
    values = {
        "thread_id": "thread-1",
        "request_id": "request-1",
        "trace_id": "trace-1",
        "user_request": "  Compare   the safe\n options.  ",
        "mode": "project",
        "policy_version": "unresolved",
        "constraints": ["  Preserve evidence  ", "preserve EVIDENCE", "No secrets"],
    }
    values.update(updates)
    return EnergyChatGraphState.model_validate(values)


def test_interpret_request_returns_typed_delta_without_identity_fields() -> None:
    delta = interpret_request(_state())

    assert delta.user_request == "Compare the safe options."
    assert delta.mode == "project"
    assert delta.status == "interpreted"
    assert not {"thread_id", "request_id", "trace_id"} & delta.model_fields_set
    assert delta.trace_events[0].payload == {
        "mode": "project",
        "normalized_request_chars": 25,
    }


def test_interpretation_replay_is_idempotent_and_preserves_identity() -> None:
    original = _state()
    first = apply_interpretation_delta(original, interpret_request(original))
    replayed = apply_interpretation_delta(first, interpret_request(first))

    assert replayed == first
    assert replayed.thread_id == original.thread_id
    assert replayed.request_id == original.request_id
    assert replayed.trace_id == original.trace_id


def test_policy_node_matches_existing_default_and_normalizes_constraints() -> None:
    state = apply_interpretation_delta(_state(), interpret_request(_state()))

    delta = load_policy_and_constraints(state)

    assert delta.policy_version == default_chat_lite_policy().version
    assert delta.constraints == ["Preserve evidence", "No secrets"]
    assert delta.status == "policy_ready"
    assert delta.trace_events[0].payload == {
        "constraint_count": 2,
        "policy_id": default_chat_lite_policy().policy_id,
        "policy_version": default_chat_lite_policy().version,
    }


def test_policy_replay_is_idempotent() -> None:
    interpreted = apply_interpretation_delta(_state(), interpret_request(_state()))
    first = apply_policy_delta(interpreted, load_policy_and_constraints(interpreted))
    replayed = apply_policy_delta(first, load_policy_and_constraints(first))

    assert replayed == first
    assert [event.sequence for event in replayed.trace_events] == [1, 2]


def test_trace_payloads_do_not_persist_user_request_or_constraints() -> None:
    interpreted = apply_interpretation_delta(_state(), interpret_request(_state()))
    ready = apply_policy_delta(interpreted, load_policy_and_constraints(interpreted))
    payload_text = repr([event.payload for event in ready.trace_events])

    assert "Compare the safe options" not in payload_text
    assert "Preserve evidence" not in payload_text
    assert "No secrets" not in payload_text


def test_explicit_supported_modes_are_preserved() -> None:
    for mode in ("chat_lite", "research", "project", "tutor"):
        assert interpret_request(_state(mode=mode)).mode == mode
