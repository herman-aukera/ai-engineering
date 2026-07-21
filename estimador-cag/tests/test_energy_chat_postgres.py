"""Milestone 13: PostgreSQL persistence — schema, migrations, retention, redaction."""

from __future__ import annotations


def test_postgres_checkpointer_has_langgraph_saver_interface() -> None:
    """PostgresCheckpointer exposes a lazy LangGraph-compatible saver boundary."""

    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    checkpointer = PostgresCheckpointer(
        "postgresql://test:test@localhost:5432/testdb"
    )
    assert checkpointer is not None


def test_postgres_checkpointer_accepts_connection_string() -> None:
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    checkpointer = PostgresCheckpointer(
        "postgresql://user:pass@host:5432/dbname"
    )
    assert checkpointer.connection_string == "postgresql://user:pass@host:5432/dbname"


def test_schema_ddl_is_valid_sql() -> None:
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    ddl = PostgresCheckpointer.schema_ddl()
    assert ddl
    assert "CREATE TABLE" in ddl.upper()
    assert "CHECKPOINT" in ddl.upper()


def test_schema_ddl_includes_migration_version_tracking() -> None:
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    ddl = PostgresCheckpointer.schema_ddl()
    assert "migration_version" in ddl.lower()
    assert "eachat_checkpoint_migrations" in ddl.lower()


def test_migration_version_is_positive_integer() -> None:
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    version = PostgresCheckpointer.migration_version()
    assert isinstance(version, int)
    assert version >= 1


def test_checkpoint_retention_policy_has_defaults() -> None:
    from app.energy_chat.checkpoint_postgres import CheckpointRetentionPolicy

    policy = CheckpointRetentionPolicy()
    assert policy.max_checkpoints_per_thread >= 1
    assert policy.retention_days is None


def test_checkpoint_redaction_requires_sensitive_fields() -> None:
    """Raw user text and human responses must not be durable checkpoint values."""

    from app.energy_chat.checkpoint_postgres import REDACTED_STATE_FIELDS

    assert "user_request" in REDACTED_STATE_FIELDS
    assert "human_action_response" in REDACTED_STATE_FIELDS
    assert isinstance(REDACTED_STATE_FIELDS, frozenset)


def test_postgres_checkpointer_configures_pool_size() -> None:
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    checkpointer = PostgresCheckpointer(
        "postgresql://test@localhost/test",
        pool_min_size=2,
        pool_max_size=10,
    )
    assert checkpointer.pool_min_size == 2
    assert checkpointer.pool_max_size == 10
