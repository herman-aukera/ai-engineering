"""Conversation store revision, idempotency, encryption, and deletion tests."""

from __future__ import annotations

import pytest

from app.energy_chat.api_v2_contracts import EnergyChatV2Response
from app.energy_chat.conversation_models import ConversationTurn
from app.energy_chat.conversation_store import (
    ConversationCipher,
    ConversationNotFoundError,
    ConversationRevisionConflictError,
    ConversationTurnConflictError,
    InMemoryConversationStore,
)


def _fernet_type():
    module = pytest.importorskip(
        "cryptography.fernet",
        reason="Cipher assertions require the isolated EACHAT production dependency set",
    )
    return module.Fernet


def _turn(
    turn_id: str,
    turn_index: int,
    *,
    message: str = "Visible user message",
    fingerprint_suffix: str = "a",
) -> ConversationTurn:
    thread_id = f"thread-{turn_id}"
    return ConversationTurn(
        turn_id=turn_id,
        turn_index=turn_index,
        request_fingerprint=f"sha256:{fingerprint_suffix * 64}",
        graph_thread_id=thread_id,
        user_message=message,
        assistant_message="Visible assistant message",
        graph_response=EnergyChatV2Response(
            thread_id=thread_id,
            request_id=f"request-{turn_id}",
            trace_id=f"trace-{turn_id}",
            graph_status="evaluated",
            final_disposition="accept",
            final_answer="Visible assistant message",
        ),
    )


def test_in_memory_store_is_revision_guarded_and_idempotent() -> None:
    store = InMemoryConversationStore()
    created = store.create("conversation-store")
    turn = _turn("turn-1", 1)

    first = store.append_turn(
        created.conversation_id,
        expected_revision=0,
        turn=turn,
    )
    replay = store.append_turn(
        created.conversation_id,
        expected_revision=0,
        turn=turn,
    )

    assert first.record.revision == 1
    assert replay.record.revision == 1
    assert replay.replayed_idempotency_key is True
    assert store.get(created.conversation_id).turns == [turn]


def test_in_memory_store_rejects_stale_revision_and_conflicting_turn_id() -> None:
    store = InMemoryConversationStore()
    store.create("conversation-conflict")
    store.append_turn(
        "conversation-conflict",
        expected_revision=0,
        turn=_turn("turn-1", 1),
    )

    with pytest.raises(ConversationRevisionConflictError):
        store.append_turn(
            "conversation-conflict",
            expected_revision=0,
            turn=_turn("turn-2", 2),
        )
    with pytest.raises(ConversationTurnConflictError):
        store.append_turn(
            "conversation-conflict",
            expected_revision=1,
            turn=_turn("turn-1", 1, fingerprint_suffix="b"),
        )


def test_in_memory_store_delete_is_final() -> None:
    store = InMemoryConversationStore()
    store.create("conversation-delete")
    store.delete("conversation-delete")

    with pytest.raises(ConversationNotFoundError):
        store.get("conversation-delete")
    with pytest.raises(ConversationNotFoundError):
        store.delete("conversation-delete")


def test_conversation_cipher_round_trip_excludes_plaintext() -> None:
    fernet_type = _fernet_type()
    cipher = ConversationCipher(fernet_type.generate_key())
    turn = _turn(
        "turn-secret",
        1,
        message="Sensitive conversation body must be encrypted at rest.",
    )

    encrypted = cipher.encrypt_turn(turn)
    decrypted = cipher.decrypt_turn(encrypted)

    assert decrypted == turn
    assert turn.user_message.encode("utf-8") not in encrypted
    assert turn.assistant_message.encode("utf-8") not in encrypted
    assert b"energy_card_v2" not in encrypted


def test_wrong_conversation_key_fails_authentication() -> None:
    fernet_type = _fernet_type()
    writer = ConversationCipher(fernet_type.generate_key())
    reader = ConversationCipher(fernet_type.generate_key())
    encrypted = writer.encrypt_turn(_turn("turn-wrong-key", 1))

    with pytest.raises(RuntimeError, match="authentication failed"):
        reader.decrypt_turn(encrypted)


def test_invalid_conversation_key_fails_startup() -> None:
    _fernet_type()
    with pytest.raises(ValueError, match="Invalid EACHAT conversation encryption key"):
        ConversationCipher("not-a-fernet-key")
