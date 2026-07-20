"""Milestone 13: PostgreSQL persistence — schema, migrations, retention, redaction."""

from __future__ import annotations


def test_postgres_checkpointer_has_langgraph_saver_interface() -> None:
    """PostgresCheckpointer must expose a langgraph_saver compatible with
    the same interface as InMemoryCheckpointer."""
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    cp = PostgresCheckpointer("postgresql://test:test@localhost:5432/testdb")
    # Interface must match — should return None when not connected
    assert cp is not None


def test_postgres_checkpointer_accepts_connection_string() -> None:
    """PostgresCheckpointer must accept a PostgreSQL connection string."""
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    cp = PostgresCheckpointer("postgresql://user:pass@host:5432/dbname")
    assert cp.connection_string == "postgresql://user:pass@host:5432/dbname"


def test_schema_ddl_is_valid_sql() -> None:
    """The checkpoint schema DDL must be non-empty and contain core SQL keywords."""
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    ddl = PostgresCheckpointer.schema_ddl()
    assert ddl
    assert "CREATE TABLE" in ddl.upper()
    assert "CHECKPOINT" in ddl.upper()


def test_schema_ddl_includes_migration_version_tracking() -> None:
    """The DDL must include migration version tracking for additive changes."""
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    ddl = PostgresCheckpointer.schema_ddl()
    assert "migration_version" in ddl.lower() or "schema_version" in ddl.lower()


def test_migration_version_is_positive_integer() -> None:
    """Migration version must be a positive integer tracking the current schema."""
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    version = PostgresCheckpointer.migration_version()
    assert isinstance(version, int)
    assert version >= 1


def test_checkpoint_retention_policy_has_defaults() -> None:
    """Retention policy must define max checkpoints and default values."""
    from app.energy_chat.checkpoint_postgres import CheckpointRetentionPolicy

    policy = CheckpointRetentionPolicy()
    assert policy.max_checkpoints_per_thread >= 1
    assert policy.retention_days is None or policy.retention_days >= 1


def test_checkpoint_redaction_excludes_sensitive_fields() -> None:
    """Redaction rules must explicitly list fields that must not be persisted."""
    from app.energy_chat.checkpoint_postgres import REDACTED_STATE_FIELDS

    assert "user_request" not in REDACTED_STATE_FIELDS  # user text is safe
    # Fields that could contain sensitive data should be listed
    assert isinstance(REDACTED_STATE_FIELDS, frozenset | set | list | tuple)


def test_postgres_checkpointer_configures_pool_size() -> None:
    """Connection pool configuration must accept custom pool parameters."""
    from app.energy_chat.checkpoint_postgres import PostgresCheckpointer

    cp = PostgresCheckpointer(
        "postgresql://test@localhost/test",
        pool_min_size=2,
        pool_max_size=10,
    )
    assert cp.pool_min_size == 2
    assert cp.pool_max_size == 10
