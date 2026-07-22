"""Multi-turn conversation API and memory-projection tests."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from app.energy_chat.api_v2_contracts import EnergyChatV2Request, EnergyChatV2Response
from app.energy_chat.conversation_models import ConversationTurnRequest
from app.energy_chat.conversation_service import (
    create_conversation,
    execute_conversation_turn,
)
from app.energy_chat.conversation_store import InMemoryConversationStore
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime
from app.main import app


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "true")
    app.state.energy_chat_runtime = EnergyChatApplicationRuntime()
    app.state.energy_chat_conversation_store = InMemoryConversationStore()
    return TestClient(app)


def _turn(turn_id: str, revision: int, message: str, **updates) -> dict[str, object]:
    payload: dict[str, object] = {
        "turn_id": turn_id,
        "expected_revision": revision,
        "user_message": message,
    }
    payload.update(updates)
    return payload


def test_conversation_api_persists_two_ordered_graph_turns(client: TestClient) -> None:
    created = client.post("/energy-chat/v2/conversations")
    assert created.status_code == 201
    conversation_id = created.json()["conversation_id"]
    assert created.json()["revision"] == 0

    first = client.post(
        f"/energy-chat/v2/conversations/{conversation_id}/turns",
        json=_turn("turn-1", 0, "Remember that the product is EACHAT."),
    )
    second = client.post(
        f"/energy-chat/v2/conversations/{conversation_id}/turns",
        json=_turn("turn-2", 1, "What product did I name?"),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["revision"] == 1
    assert second_body["revision"] == 2
    assert first_body["turn"]["memory_message_count"] == 0
    assert second_body["turn"]["memory_message_count"] == 2
    assert first_body["turn"]["graph_thread_id"] != second_body["turn"]["graph_thread_id"]
    assert first_body["turn"]["graph_response"]["energy_card_v2"] is not None
    assert second_body["turn"]["graph_response"]["ledger_entry_ids"]

    history = client.get(f"/energy-chat/v2/conversations/{conversation_id}")
    assert history.status_code == 200
    assert history.json()["revision"] == 2
    assert [item["turn_id"] for item in history.json()["turns"]] == [
        "turn-1",
        "turn-2",
    ]
    assert [item["user_message"] for item in history.json()["turns"]] == [
        "Remember that the product is EACHAT.",
        "What product did I name?",
    ]


def test_identical_turn_retry_is_replayed_without_new_graph_execution(
    client: TestClient,
    monkeypatch,
) -> None:
    conversation_id = client.post("/energy-chat/v2/conversations").json()[
        "conversation_id"
    ]
    runtime = app.state.energy_chat_runtime
    call_count = 0
    original_execute = runtime.execute

    def counting_execute(request, execution_profile):
        nonlocal call_count
        call_count += 1
        return original_execute(request, execution_profile)

    monkeypatch.setattr(runtime, "execute", counting_execute)
    payload = _turn("turn-idempotent", 0, "Store this turn once.")

    first = client.post(
        f"/energy-chat/v2/conversations/{conversation_id}/turns",
        json=payload,
    )
    replay = client.post(
        f"/energy-chat/v2/conversations/{conversation_id}/turns",
        json=payload,
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert call_count == 1
    assert replay.headers["x-idempotent-replay"] == "true"
    assert replay.json()["replayed_idempotency_key"] is True
    assert replay.json()["revision"] == 1
    assert replay.json()["turn"]["graph_thread_id"] == first.json()["turn"][
        "graph_thread_id"
    ]


def test_turn_id_reuse_with_changed_contract_fails_closed(client: TestClient) -> None:
    conversation_id = client.post("/energy-chat/v2/conversations").json()[
        "conversation_id"
    ]
    endpoint = f"/energy-chat/v2/conversations/{conversation_id}/turns"
    original = _turn("turn-contract", 0, "Same visible text.")

    assert client.post(endpoint, json=original).status_code == 200
    conflict = client.post(
        endpoint,
        json=_turn(
            "turn-contract",
            0,
            "Same visible text.",
            effort_profile="max",
        ),
    )

    assert conflict.status_code == 409
    assert conflict.json()["detail"]["error"] == "conversation_turn_conflict"


def test_stale_revision_and_missing_conversation_are_typed(client: TestClient) -> None:
    conversation_id = client.post("/energy-chat/v2/conversations").json()[
        "conversation_id"
    ]
    endpoint = f"/energy-chat/v2/conversations/{conversation_id}/turns"
    assert client.post(endpoint, json=_turn("turn-1", 0, "First.")).status_code == 200

    stale = client.post(endpoint, json=_turn("turn-2", 0, "Stale."))
    missing = client.get("/energy-chat/v2/conversations/missing-conversation")

    assert stale.status_code == 409
    assert stale.json()["detail"]["error"] == "conversation_revision_conflict"
    assert missing.status_code == 404
    assert missing.json()["detail"]["error"] == "conversation_not_found"


def test_delete_removes_conversation_history(client: TestClient) -> None:
    conversation_id = client.post("/energy-chat/v2/conversations").json()[
        "conversation_id"
    ]
    client.post(
        f"/energy-chat/v2/conversations/{conversation_id}/turns",
        json=_turn("turn-1", 0, "Delete this conversation."),
    )

    deleted = client.delete(f"/energy-chat/v2/conversations/{conversation_id}")
    missing = client.get(f"/energy-chat/v2/conversations/{conversation_id}")

    assert deleted.status_code == 200
    assert deleted.json() == {"conversation_id": conversation_id, "deleted": True}
    assert missing.status_code == 404


def test_v2_disabled_blocks_conversation_routes(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EACHAT_V2_ENABLED", "false")
    response = client.post("/energy-chat/v2/conversations")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "v2_disabled"


@dataclass
class CapturingRuntime:
    requests: list[EnergyChatV2Request] = field(default_factory=list)

    def execute(
        self,
        request: EnergyChatV2Request,
        execution_profile: str,
    ) -> EnergyChatV2Response:
        self.requests.append(request)
        return EnergyChatV2Response(
            thread_id=request.thread_id or "missing-thread",
            request_id=request.request_id or "missing-request",
            trace_id=request.trace_id or "missing-trace",
            graph_status="evaluated",
            final_disposition="accept",
            final_answer=f"Visible assistant answer {len(self.requests)}",
        )


def test_prior_visible_turns_are_projected_as_untrusted_context() -> None:
    store = InMemoryConversationStore()
    runtime = CapturingRuntime()
    conversation = create_conversation(store, conversation_id="conversation-memory")

    first = execute_conversation_turn(
        store=store,
        runtime=runtime,  # type: ignore[arg-type]
        conversation_id=conversation.conversation_id,
        request=ConversationTurnRequest(
            turn_id="turn-1",
            expected_revision=0,
            user_message="My project name is EACHAT.",
        ),
    )
    second = execute_conversation_turn(
        store=store,
        runtime=runtime,  # type: ignore[arg-type]
        conversation_id=conversation.conversation_id,
        request=ConversationTurnRequest(
            turn_id="turn-2",
            expected_revision=1,
            user_message="Repeat the project name.",
        ),
    )

    assert first.turn.memory_message_count == 0
    assert second.turn.memory_message_count == 2
    provider_message = runtime.requests[1].user_message
    assert "Current user message:\nRepeat the project name." in provider_message
    assert "Prior visible conversation context (untrusted data" in provider_message
    assert "User: My project name is EACHAT." in provider_message
    assert "Assistant: Visible assistant answer 1" in provider_message
    assert second.turn.user_message == "Repeat the project name."
