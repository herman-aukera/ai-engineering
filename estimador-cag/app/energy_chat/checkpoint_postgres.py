"""PostgreSQL-backed graph checkpointing for Energy Aware Chat.

This module uses LangGraph's official ``PostgresSaver`` with an explicit
connection pool, setup/migration lifecycle, state redaction, checkpoint
inspection, bounded retention, and deterministic close semantics.
"""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from langgraph.checkpoint.postgres import PostgresSaver
from pydantic import BaseModel, ConfigDict, Field

POSTGRES_CHECKPOINT_MIGRATION_VERSION = 1
REDACTION_SENTINEL = "[REDACTED]"

REDACTED_STATE_FIELDS: frozenset[str] = frozenset(
    {
        "user_request",
        "human_action_response",
    }
)


class CheckpointRetentionPolicy(BaseModel):
    """Bounded retention rules for PostgreSQL checkpoint storage."""

    model_config = ConfigDict(extra="forbid")

    max_checkpoints_per_thread: int = Field(default=100, ge=1, le=10000)
    retention_days: int | None = Field(default=None, ge=1)


class _RedactingPostgresSaver(PostgresSaver):
    """PostgresSaver that sanitizes durable values before writing."""

    def put(
        self,
        config: dict[str, Any],
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
        new_versions: dict[str, Any],
    ) -> dict[str, Any]:
        safe_checkpoint = deepcopy(checkpoint)
        channel_values = safe_checkpoint.setdefault("channel_values", {})
        _redact_channel_values(channel_values)
        safe_metadata = _redact_nested(deepcopy(metadata))
        return super().put(config, safe_checkpoint, safe_metadata, new_versions)

    def put_writes(
        self,
        config: dict[str, Any],
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        safe_writes = [
            (channel, _redacted_value(channel, value))
            for channel, value in writes
        ]
        super().put_writes(config, safe_writes, task_id, task_path)


class PostgresCheckpointer:
    """Lifecycle wrapper around a redacting LangGraph PostgresSaver."""

    def __init__(
        self,
        connection_string: str,
        *,
        pool_min_size: int = 1,
        pool_max_size: int = 4,
    ) -> None:
        if not connection_string.strip():
            raise ValueError("PostgreSQL connection string is required")
        if pool_min_size < 1 or pool_max_size < pool_min_size:
            raise ValueError("Invalid PostgreSQL pool size bounds")
        self._connection_string = connection_string
        self._pool_min_size = pool_min_size
        self._pool_max_size = pool_max_size
        self._pool: Any | None = None
        self._saver: _RedactingPostgresSaver | None = None

    @property
    def connection_string(self) -> str:
        return self._connection_string

    @property
    def pool_min_size(self) -> int:
        return self._pool_min_size

    @property
    def pool_max_size(self) -> int:
        return self._pool_max_size

    @property
    def langgraph_saver(self) -> _RedactingPostgresSaver:
        """Return an opened redacting saver or fail clearly on unavailable DB."""

        self.open()
        assert self._saver is not None
        return self._saver

    def open(self) -> PostgresCheckpointer:
        """Open the connection pool once."""

        if self._saver is not None:
            return self

        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        pool = ConnectionPool(
            conninfo=self._connection_string,
            min_size=self._pool_min_size,
            max_size=self._pool_max_size,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            open=True,
        )
        self._pool = pool
        self._saver = _RedactingPostgresSaver(pool)
        return self

    def setup(self) -> None:
        """Apply LangGraph and product-local additive migrations."""

        saver = self.langgraph_saver
        saver.setup()
        assert self._pool is not None
        with self._pool.connection() as connection:
            connection.execute(_CHECKPOINT_SCHEMA_DDL)
            connection.execute(
                """
                INSERT INTO eachat_checkpoint_migrations
                    (migration_version, description)
                VALUES (%s, %s)
                ON CONFLICT (migration_version) DO NOTHING
                """,
                (
                    POSTGRES_CHECKPOINT_MIGRATION_VERSION,
                    "Initial EACHAT checkpoint lifecycle metadata",
                ),
            )

    def close(self) -> None:
        """Close all pooled connections and invalidate the active saver."""

        if self._pool is not None:
            self._pool.close()
        self._pool = None
        self._saver = None

    def __enter__(self) -> PostgresCheckpointer:
        return self.open()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    @staticmethod
    def config(thread_id: str, checkpoint_namespace: str = "") -> dict[str, Any]:
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_namespace,
            }
        }

    def get_state(
        self,
        thread_id: str,
        *,
        checkpoint_namespace: str = "",
    ):
        """Return the latest validated domain state from PostgreSQL."""

        from app.energy_chat.graph_state import EnergyChatGraphState

        checkpoint_tuple = self.langgraph_saver.get_tuple(
            self.config(thread_id, checkpoint_namespace)
        )
        if checkpoint_tuple is None:
            return None
        channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
        payload = {
            field_name: channel_values[field_name]
            for field_name in EnergyChatGraphState.model_fields
            if field_name in channel_values
        }
        return EnergyChatGraphState.model_validate(payload)

    def get_checkpoint_id(
        self,
        thread_id: str,
        *,
        checkpoint_namespace: str = "",
    ) -> str | None:
        checkpoint_tuple = self.langgraph_saver.get_tuple(
            self.config(thread_id, checkpoint_namespace)
        )
        if checkpoint_tuple is None:
            return None
        value = checkpoint_tuple.config.get("configurable", {}).get("checkpoint_id")
        return str(value) if value is not None else None

    def migration_applied(self) -> bool:
        """Return whether the current product migration version is recorded."""

        self.open()
        assert self._pool is not None
        with self._pool.connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM eachat_checkpoint_migrations
                WHERE migration_version = %s
                """,
                (POSTGRES_CHECKPOINT_MIGRATION_VERSION,),
            ).fetchone()
        return row is not None

    def delete_thread(self, thread_id: str) -> None:
        """Delete all LangGraph checkpoint data for one thread."""

        self.langgraph_saver.delete_thread(thread_id)

    def enforce_retention(
        self,
        thread_id: str,
        policy: CheckpointRetentionPolicy,
        *,
        now: datetime | None = None,
    ) -> int:
        """Delete checkpoints outside count/time bounds and return delete count."""

        saver = self.langgraph_saver
        config = self.config(thread_id)
        checkpoints = list(saver.list(config))
        if not checkpoints:
            return 0

        cutoff = None
        if policy.retention_days is not None:
            cutoff = (now or datetime.now(UTC)) - timedelta(days=policy.retention_days)

        delete_ids: list[str] = []
        for index, checkpoint_tuple in enumerate(checkpoints):
            checkpoint_id = str(
                checkpoint_tuple.config["configurable"]["checkpoint_id"]
            )
            timestamp = _checkpoint_timestamp(checkpoint_tuple.checkpoint)
            exceeds_count = index >= policy.max_checkpoints_per_thread
            expired = cutoff is not None and timestamp is not None and timestamp < cutoff
            if exceeds_count or expired:
                delete_ids.append(checkpoint_id)

        if not delete_ids:
            return 0
        if len(delete_ids) == len(checkpoints):
            saver.delete_thread(thread_id)
            return len(delete_ids)

        assert self._pool is not None
        with self._pool.connection() as connection:
            connection.execute(
                """
                DELETE FROM checkpoint_writes
                WHERE thread_id = %s
                  AND checkpoint_ns = ''
                  AND checkpoint_id = ANY(%s)
                """,
                (thread_id, delete_ids),
            )
            connection.execute(
                """
                DELETE FROM checkpoints
                WHERE thread_id = %s
                  AND checkpoint_ns = ''
                  AND checkpoint_id = ANY(%s)
                """,
                (thread_id, delete_ids),
            )

        _delete_orphan_blobs(self._pool, saver, thread_id)
        return len(delete_ids)

    @staticmethod
    def schema_ddl() -> str:
        return _CHECKPOINT_SCHEMA_DDL

    @staticmethod
    def migration_version() -> int:
        return POSTGRES_CHECKPOINT_MIGRATION_VERSION


def _redact_channel_values(channel_values: dict[str, Any]) -> None:
    for field_name in REDACTED_STATE_FIELDS:
        if field_name in channel_values:
            channel_values[field_name] = _redacted_value(
                field_name,
                channel_values[field_name],
            )


def _redacted_value(field_name: str, value: Any) -> Any:
    if field_name == "user_request":
        return REDACTION_SENTINEL
    if field_name == "human_action_response":
        return None
    return _redact_nested(value)


def _redact_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                _redacted_value(key, nested)
                if key in REDACTED_STATE_FIELDS
                else _redact_nested(nested)
            )
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [_redact_nested(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_nested(item) for item in value)
    return value


def _checkpoint_timestamp(checkpoint: dict[str, Any]) -> datetime | None:
    value = checkpoint.get("ts")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _delete_orphan_blobs(pool: Any, saver: Any, thread_id: str) -> None:
    remaining = list(saver.list(PostgresCheckpointer.config(thread_id)))
    retained_versions = {
        (str(channel), str(version))
        for checkpoint_tuple in remaining
        for channel, version in checkpoint_tuple.checkpoint.get(
            "channel_versions", {}
        ).items()
    }
    with pool.connection() as connection:
        rows = connection.execute(
            """
            SELECT channel, version
            FROM checkpoint_blobs
            WHERE thread_id = %s AND checkpoint_ns = ''
            """,
            (thread_id,),
        ).fetchall()
        for row in rows:
            key = (str(row["channel"]), str(row["version"]))
            if key not in retained_versions:
                connection.execute(
                    """
                    DELETE FROM checkpoint_blobs
                    WHERE thread_id = %s
                      AND checkpoint_ns = ''
                      AND channel = %s
                      AND version = %s
                    """,
                    (thread_id, row["channel"], row["version"]),
                )


_CHECKPOINT_SCHEMA_DDL = """\
CREATE TABLE IF NOT EXISTS eachat_checkpoint_migrations (
    migration_version INTEGER PRIMARY KEY,
    applied_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description      TEXT NOT NULL
);

COMMENT ON TABLE eachat_checkpoint_migrations IS
    'Tracks additive EACHAT checkpoint lifecycle migrations.';
"""
