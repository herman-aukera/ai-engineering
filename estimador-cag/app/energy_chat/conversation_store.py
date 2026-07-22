"""Revision-guarded in-memory and encrypted PostgreSQL conversation stores."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Protocol

from app.energy_chat.conversation_models import ConversationRecord, ConversationTurn


class ConversationNotFoundError(LookupError):
    """Raised when a conversation identity is unknown."""


class ConversationAlreadyExistsError(RuntimeError):
    """Raised when a conversation identity is reused."""


class ConversationRevisionConflictError(RuntimeError):
    """Raised when a caller appends against a stale conversation revision."""


class ConversationTurnConflictError(RuntimeError):
    """Raised when an idempotency key is reused with different turn content."""


@dataclass(frozen=True)
class ConversationAppendResult:
    record: ConversationRecord
    replayed_idempotency_key: bool


class ConversationStore(Protocol):
    """Minimum durable-memory contract used by the conversation API."""

    restart_persistent: bool

    def setup(self) -> None: ...
    def create(self, conversation_id: str) -> ConversationRecord: ...
    def get(self, conversation_id: str) -> ConversationRecord: ...
    def append_turn(
        self,
        conversation_id: str,
        *,
        expected_revision: int,
        turn: ConversationTurn,
    ) -> ConversationAppendResult: ...
    def delete(self, conversation_id: str) -> None: ...
    def close(self) -> None: ...


class InMemoryConversationStore:
    """Process-local implementation used only by deterministic tests and demos."""

    restart_persistent = False

    def __init__(self) -> None:
        self._records: dict[str, ConversationRecord] = {}
        self._lock = RLock()

    def setup(self) -> None:
        return None

    def create(self, conversation_id: str) -> ConversationRecord:
        with self._lock:
            if conversation_id in self._records:
                raise ConversationAlreadyExistsError(conversation_id)
            record = ConversationRecord(conversation_id=conversation_id)
            self._records[conversation_id] = record
            return record.model_copy(deep=True)

    def get(self, conversation_id: str) -> ConversationRecord:
        with self._lock:
            record = self._records.get(conversation_id)
            if record is None:
                raise ConversationNotFoundError(conversation_id)
            return record.model_copy(deep=True)

    def append_turn(
        self,
        conversation_id: str,
        *,
        expected_revision: int,
        turn: ConversationTurn,
    ) -> ConversationAppendResult:
        with self._lock:
            record = self._records.get(conversation_id)
            if record is None:
                raise ConversationNotFoundError(conversation_id)
            duplicate = next(
                (item for item in record.turns if item.turn_id == turn.turn_id),
                None,
            )
            if duplicate is not None:
                if duplicate != turn:
                    raise ConversationTurnConflictError(turn.turn_id)
                return ConversationAppendResult(
                    record=record.model_copy(deep=True),
                    replayed_idempotency_key=True,
                )
            if record.revision != expected_revision:
                raise ConversationRevisionConflictError(
                    f"Expected revision {expected_revision}, current revision {record.revision}"
                )
            if turn.turn_index != record.revision + 1:
                raise ConversationRevisionConflictError(
                    "turn_index must equal the next conversation revision"
                )
            updated = record.model_copy(
                update={
                    "revision": record.revision + 1,
                    "turns": [*record.turns, turn],
                },
                deep=True,
            )
            self._records[conversation_id] = updated
            return ConversationAppendResult(
                record=updated.model_copy(deep=True),
                replayed_idempotency_key=False,
            )

    def delete(self, conversation_id: str) -> None:
        with self._lock:
            if self._records.pop(conversation_id, None) is None:
                raise ConversationNotFoundError(conversation_id)

    def close(self) -> None:
        return None


def _load_fernet_types():
    """Load the production-only encryption dependency without polluting keyless CI."""

    try:
        from cryptography.fernet import Fernet, InvalidToken
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Encrypted conversation storage requires the isolated EACHAT production "
            "dependency set."
        ) from exc
    return Fernet, InvalidToken


class ConversationCipher:
    """Application-level authenticated encryption for persisted turn payloads."""

    def __init__(self, key: str | bytes) -> None:
        encoded = key.encode("utf-8") if isinstance(key, str) else key
        fernet_type, invalid_token_type = _load_fernet_types()
        self._invalid_token_type = invalid_token_type
        try:
            self._fernet = fernet_type(encoded)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid EACHAT conversation encryption key") from exc

    def encrypt_turn(self, turn: ConversationTurn) -> bytes:
        return self._fernet.encrypt(turn.model_dump_json().encode("utf-8"))

    def decrypt_turn(self, payload: bytes) -> ConversationTurn:
        try:
            plaintext = self._fernet.decrypt(payload)
        except Exception as exc:
            if isinstance(exc, self._invalid_token_type):
                raise RuntimeError("Conversation payload authentication failed") from exc
            raise
        return ConversationTurn.model_validate_json(plaintext)


class PostgresConversationStore:
    """Encrypted durable conversation store with revision-guarded append semantics."""

    restart_persistent = True

    def __init__(
        self,
        connection_string: str,
        *,
        encryption_key: str | bytes,
        min_size: int = 1,
        max_size: int = 4,
    ) -> None:
        if not connection_string.strip():
            raise ValueError("PostgreSQL conversation storage requires a connection string")
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        self._cipher = ConversationCipher(encryption_key)
        self._pool = ConnectionPool(
            conninfo=connection_string,
            min_size=min_size,
            max_size=max_size,
            kwargs={"autocommit": False, "row_factory": dict_row},
            open=True,
        )
        self._closed = False

    def setup(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS eachat_conversations (
                conversation_id TEXT PRIMARY KEY,
                revision BIGINT NOT NULL DEFAULT 0 CHECK (revision >= 0),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS eachat_conversation_turns (
                conversation_id TEXT NOT NULL REFERENCES eachat_conversations(conversation_id)
                    ON DELETE CASCADE,
                turn_index BIGINT NOT NULL CHECK (turn_index >= 1),
                turn_id TEXT NOT NULL,
                graph_thread_id TEXT NOT NULL,
                encrypted_payload BYTEA NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (conversation_id, turn_index),
                UNIQUE (conversation_id, turn_id),
                UNIQUE (graph_thread_id)
            )
            """,
        )
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
            connection.commit()

    def create(self, conversation_id: str) -> ConversationRecord:
        from psycopg.errors import UniqueViolation

        try:
            with self._pool.connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO eachat_conversations (conversation_id) VALUES (%s)",
                        (conversation_id,),
                    )
                connection.commit()
        except UniqueViolation as exc:
            raise ConversationAlreadyExistsError(conversation_id) from exc
        return ConversationRecord(conversation_id=conversation_id)

    def get(self, conversation_id: str) -> ConversationRecord:
        with self._pool.connection() as connection:
            return self._get_with_connection(connection, conversation_id)

    def append_turn(
        self,
        conversation_id: str,
        *,
        expected_revision: int,
        turn: ConversationTurn,
    ) -> ConversationAppendResult:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT revision FROM eachat_conversations "
                    "WHERE conversation_id = %s FOR UPDATE",
                    (conversation_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ConversationNotFoundError(conversation_id)
                cursor.execute(
                    "SELECT encrypted_payload FROM eachat_conversation_turns "
                    "WHERE conversation_id = %s AND turn_id = %s",
                    (conversation_id, turn.turn_id),
                )
                duplicate_row = cursor.fetchone()
                if duplicate_row is not None:
                    duplicate = self._cipher.decrypt_turn(
                        bytes(duplicate_row["encrypted_payload"])
                    )
                    if duplicate != turn:
                        raise ConversationTurnConflictError(turn.turn_id)
                    connection.rollback()
                    return ConversationAppendResult(
                        record=self.get(conversation_id),
                        replayed_idempotency_key=True,
                    )
                current_revision = int(row["revision"])
                if current_revision != expected_revision:
                    raise ConversationRevisionConflictError(
                        f"Expected revision {expected_revision}, current revision "
                        f"{current_revision}"
                    )
                if turn.turn_index != current_revision + 1:
                    raise ConversationRevisionConflictError(
                        "turn_index must equal the next conversation revision"
                    )
                cursor.execute(
                    """
                    INSERT INTO eachat_conversation_turns (
                        conversation_id,
                        turn_index,
                        turn_id,
                        graph_thread_id,
                        encrypted_payload
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        conversation_id,
                        turn.turn_index,
                        turn.turn_id,
                        turn.graph_thread_id,
                        self._cipher.encrypt_turn(turn),
                    ),
                )
                cursor.execute(
                    "UPDATE eachat_conversations SET revision = %s, updated_at = NOW() "
                    "WHERE conversation_id = %s",
                    (current_revision + 1, conversation_id),
                )
            connection.commit()
        return ConversationAppendResult(
            record=self.get(conversation_id),
            replayed_idempotency_key=False,
        )

    def delete(self, conversation_id: str) -> None:
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM eachat_conversations WHERE conversation_id = %s",
                    (conversation_id,),
                )
                deleted = cursor.rowcount
            connection.commit()
        if deleted == 0:
            raise ConversationNotFoundError(conversation_id)

    def close(self) -> None:
        if not self._closed:
            self._pool.close()
            self._closed = True

    def _get_with_connection(self, connection, conversation_id: str) -> ConversationRecord:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT revision FROM eachat_conversations WHERE conversation_id = %s",
                (conversation_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ConversationNotFoundError(conversation_id)
            cursor.execute(
                "SELECT encrypted_payload FROM eachat_conversation_turns "
                "WHERE conversation_id = %s ORDER BY turn_index",
                (conversation_id,),
            )
            turns = [
                self._cipher.decrypt_turn(bytes(item["encrypted_payload"]))
                for item in cursor.fetchall()
            ]
        return ConversationRecord(
            conversation_id=conversation_id,
            revision=int(row["revision"]),
            turns=turns,
        )
