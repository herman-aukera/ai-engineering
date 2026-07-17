import ast
import json
from pathlib import Path

import pytest

from app.energy_chat.graph_state import (
    CandidateVersion,
    EnergyChatGraphState,
    TraceEvent,
    append_unique_records,
    deserialize_graph_state,
    serialize_graph_state,
)

FIXTURE = Path(__file__).parent / "fixtures" / "energy_chat_graph_state_v1.json"


def test_v1_fixture_round_trips_without_schema_drift() -> None:
    payload = FIXTURE.read_text(encoding="utf-8")

    state = deserialize_graph_state(payload)

    assert state.schema_version == "1.0.0"
    assert serialize_graph_state(state) == json.dumps(
        json.loads(payload), sort_keys=True, separators=(",", ":")
    )


def test_accumulating_reducer_is_retry_idempotent() -> None:
    event = TraceEvent(
        event_id="evt-1",
        event_type="request_interpreted",
        producer="interpret_request",
        sequence=1,
    )

    assert append_unique_records([event], [event], id_field="event_id") == [event]


def test_accumulating_reducer_rejects_conflicting_duplicate_ids() -> None:
    original = CandidateVersion(
        candidate_id="candidate-1", version=1, answer="first", producer="generate_candidate"
    )
    conflicting = original.model_copy(update={"answer": "different"})

    with pytest.raises(ValueError, match="candidate-1"):
        append_unique_records([original], [conflicting], id_field="candidate_id")


def test_singular_authoritative_fields_are_not_lists() -> None:
    fields = EnergyChatGraphState.model_fields

    assert fields["active_candidate_id"].annotation == str | None
    assert fields["final_answer"].annotation == str | None
    assert fields["status"].annotation != list[str]


def test_domain_state_has_no_langgraph_import_boundary() -> None:
    source = Path("app/energy_chat/graph_state.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert not any(name == "langgraph" or name.startswith("langgraph.") for name in imports)


def test_unknown_schema_version_is_rejected() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["schema_version"] = "2.0.0"

    with pytest.raises(ValueError, match="Unsupported Energy Chat graph state schema"):
        deserialize_graph_state(json.dumps(payload))
