"""PostgreSQL integration proof for encrypted durable multi-turn conversations."""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.energy_chat.checkpoint_postgres import PostgresCheckpointer
from app.energy_chat.conversation_models import ConversationTurnRequest
from app.energy_chat.conversation_service import (
    create_conversation,
    execute_conversation_turn,
    get_conversation_history,
)
from app.energy_chat.conversation_store import PostgresConversationStore
from app.energy_chat.production_app import create_production_app
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime

fernet_module = pytest.importorskip(
    "cryptography.fernet",
    reason="Encrypted PostgreSQL conversations require the isolated production dependency set",
)
Fernet = fernet_module.Fernet
pytestmark = pytest.mark.skipif(
    not os.environ.get("EACHAT_POSTGRES_URL", "").strip(),
    reason="PostgreSQL conversation tests require EACHAT_POSTGRES_URL",
)


def _postgres_url() -> str:
    value = os.environ.get("EACHAT_POSTGRES_URL", "").strip()
    if not value:
        raise RuntimeError("EACHAT_POSTGRES_URL is required for PostgreSQL tests")
    return value


def test_encrypted_conversation_survives_store_and_runtime_reopen() -> None:
    postgres_url = _postgres_url()
    encryption_key = Fernet.generate_key().decode("utf-8")
    conversation_id = f"conversation-pg-{uuid.uuid4().hex[:12]}"
    first_message = "Persist this private first conversation turn."
    second_message = "Use the previous visible turn as bounded memory."

    checkpointer = PostgresCheckpointer(postgres_url)
    store = PostgresConversationStore(
        postgres_url,
        encryption_key=encryption_key,
    )
    try:
        checkpointer.setup()
        store.setup()
        runtime = EnergyChatApplicationRuntime(checkpointer=checkpointer)
        create_conversation(store, conversation_id=conversation_id)
        first = execute_conversation_turn(
            store=store,
            runtime=runtime,
            conversation_id=conversation_id,
            request=ConversationTurnRequest(
                turn_id="turn-1",
                expected_revision=0,
                user_message=first_message,
            ),
        )
        second = execute_conversation_turn(
            store=store,
            runtime=runtime,
            conversation_id=conversation_id,
            request=ConversationTurnRequest(
                turn_id="turn-2",
                expected_revision=1,
                user_message=second_message,
            ),
        )
        assert first.turn.memory_message_count == 0
        assert second.turn.memory_message_count == 2
        assert first.turn.graph_thread_id != second.turn.graph_thread_id
    finally:
        store.close()
        checkpointer.close()

    reopened_checkpointer = PostgresCheckpointer(postgres_url)
    reopened_store = PostgresConversationStore(
        postgres_url,
        encryption_key=encryption_key,
    )
    try:
        reopened_checkpointer.setup()
        reopened_store.setup()
        history = get_conversation_history(reopened_store, conversation_id)
        assert history.revision == 2
        assert [turn.user_message for turn in history.turns] == [
            first_message,
            second_message,
        ]
        assert all(turn.graph_response.energy_card_v2 for turn in history.turns)
        assert all(turn.graph_response.ledger_entry_ids for turn in history.turns)
        assert reopened_checkpointer.get_state(history.turns[0].graph_thread_id) is not None
        assert reopened_checkpointer.get_state(history.turns[1].graph_thread_id) is not None
    finally:
        reopened_store.close()
        reopened_checkpointer.close()

    with psycopg.connect(postgres_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT encrypted_payload FROM eachat_conversation_turns "
                "WHERE conversation_id = %s ORDER BY turn_index",
                (conversation_id,),
            )
            encrypted_rows = [bytes(row[0]) for row in cursor.fetchall()]
    assert len(encrypted_rows) == 2
    assert all(first_message.encode("utf-8") not in row for row in encrypted_rows)
    assert all(second_message.encode("utf-8") not in row for row in encrypted_rows)
    assert all(b"energy_card_v2" not in row for row in encrypted_rows)

    wrong_key_store = PostgresConversationStore(
        postgres_url,
        encryption_key=Fernet.generate_key(),
    )
    try:
        wrong_key_store.setup()
        try:
            wrong_key_store.get(conversation_id)
        except RuntimeError as exc:
            assert "authentication failed" in str(exc)
        else:
            raise AssertionError("Wrong memory key unexpectedly decrypted conversation data")
    finally:
        wrong_key_store.close()

    deletion_store = PostgresConversationStore(
        postgres_url,
        encryption_key=encryption_key,
    )
    try:
        deletion_store.setup()
        deletion_store.delete(conversation_id)
    finally:
        deletion_store.close()

    with psycopg.connect(postgres_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM eachat_conversations WHERE conversation_id = %s",
                (conversation_id,),
            )
            conversation_count = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM eachat_conversation_turns "
                "WHERE conversation_id = %s",
                (conversation_id,),
            )
            turn_count = cursor.fetchone()[0]
    assert conversation_count == 0
    assert turn_count == 0


def test_production_health_reports_durable_conversation_memory(monkeypatch) -> None:
    postgres_url = _postgres_url()
    encryption_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("LANGGRAPH_STRICT_MSGPACK", "true")
    monkeypatch.setenv("EACHAT_POSTGRES_URL", postgres_url)
    monkeypatch.setenv("EACHAT_MEMORY_ENCRYPTION_KEY", encryption_key)
    monkeypatch.delenv("EACHAT_ALLOW_IN_MEMORY", raising=False)
    service = create_production_app()

    with TestClient(service) as client:
        health = client.get("/health")
        created = client.post("/energy-chat/v2/conversations")
        conversation_id = created.json()["conversation_id"]
        turn = client.post(
            f"/energy-chat/v2/conversations/{conversation_id}/turns",
            json={
                "turn_id": "turn-production",
                "expected_revision": 0,
                "user_message": "Prove the production conversation route.",
            },
        )
        history = client.get(f"/energy-chat/v2/conversations/{conversation_id}")
        deleted = client.delete(f"/energy-chat/v2/conversations/{conversation_id}")

    assert health.status_code == 200
    assert health.json()["restart_persistent"] is True
    assert health.json()["conversation_restart_persistent"] is True
    assert health.json()["strict_msgpack"] is True
    assert created.status_code == 201
    assert turn.status_code == 200
    assert turn.json()["turn"]["graph_response"]["energy_card_v2"] is not None
    assert history.status_code == 200
    assert history.json()["revision"] == 1
    assert deleted.status_code == 200
