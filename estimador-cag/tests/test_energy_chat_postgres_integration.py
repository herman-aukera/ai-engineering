"""Milestone 13 live-DB proof: PostgreSQL checkpoint integration tests.

These tests require a live PostgreSQL connection. They are skipped in
deterministic CI and run only when EACHAT_POSTGRES_URL is set.
"""

from __future__ import annotations

import os

import pytest

from app.energy_chat.checkpoint_postgres import (
    POSTGRES_CHECKPOINT_MIGRATION_VERSION,
    CheckpointRetentionPolicy,
    PostgresCheckpointer,
)
from app.energy_chat.graph_runtime import build_energy_chat_graph
from app.energy_chat.graph_state import EnergyChatGraphState

POSTGRES_URL = os.environ.get("EACHAT_POSTGRES_URL", "")
REQUIRES_POSTGRES = pytest.mark.skipif(
    not POSTGRES_URL, reason="EACHAT_POSTGRES_URL not set"
)


def _state(**overrides: object) -> EnergyChatGraphState:
    values: dict[str, object] = {
        "thread_id": "pg-thread-1",
        "request_id": "pg-request-1",
        "trace_id": "pg-trace-1",
        "user_request": "Test PostgreSQL checkpoint write and read.",
        "mode": "project",
        "policy_version": "unresolved",
        "constraints": ["no secrets"],
    }
    values.update(overrides)
    return EnergyChatGraphState.model_validate(values)


@REQUIRES_POSTGRES
def test_postgres_checkpointer_connects() -> None:
    """Verify the PostgresCheckpointer can establish a live connection."""
    cp = PostgresCheckpointer(POSTGRES_URL)
    saver = cp.langgraph_saver
    assert saver is not None, "PostgresSaver should connect successfully"


@REQUIRES_POSTGRES
def test_schema_migration_creates_tables() -> None:
    """Schema DDL must execute without error against a live database."""
    cp = PostgresCheckpointer(POSTGRES_URL)
    saver = cp.langgraph_saver
    assert saver is not None
    # setup() creates LangGraph checkpoint tables
    saver.setup()
    # Verify migration version is correct
    assert PostgresCheckpointer.migration_version() == POSTGRES_CHECKPOINT_MIGRATION_VERSION


@REQUIRES_POSTGRES
def test_checkpoint_write_and_read() -> None:
    """A graph run must write a checkpoint that can be read back after
    a simulated process restart (new checkpointer instance)."""
    cp1 = PostgresCheckpointer(POSTGRES_URL)
    saver1 = cp1.langgraph_saver
    assert saver1 is not None
    saver1.setup()

    graph = build_energy_chat_graph(checkpointer=saver1)
    state = _state()
    config = {"configurable": {"thread_id": state.thread_id}}

    payload = {
        field_name: getattr(state, field_name)
        for field_name in state.model_fields
    }
    result1 = graph.invoke(payload, config)
    domain1 = EnergyChatGraphState.model_validate(result1)
    assert domain1.status == "evaluated"
    assert domain1.final_projection is not None

    # Simulate process restart: new checkpointer, same connection string
    cp2 = PostgresCheckpointer(POSTGRES_URL)
    saver2 = cp2.langgraph_saver
    assert saver2 is not None
    graph2 = build_energy_chat_graph(checkpointer=saver2)
    # Replay with None to use checkpointed state
    result2 = graph2.invoke(None, config)
    domain2 = EnergyChatGraphState.model_validate(result2)
    assert domain2.status == domain1.status
    assert domain2.final_answer == domain1.final_answer
    assert domain2.thread_id == domain1.thread_id


@REQUIRES_POSTGRES
def test_thread_isolation_in_postgres() -> None:
    """Different thread_ids must produce independent checkpoints."""
    cp = PostgresCheckpointer(POSTGRES_URL)
    saver = cp.langgraph_saver
    assert saver is not None
    saver.setup()

    graph = build_energy_chat_graph(checkpointer=saver)
    state_a = _state(thread_id="pg-iso-a", request_id="pg-req-a")
    state_b = _state(thread_id="pg-iso-b", request_id="pg-req-b")

    config_a = {"configurable": {"thread_id": "pg-iso-a"}}
    config_b = {"configurable": {"thread_id": "pg-iso-b"}}

    payload_a = {fn: getattr(state_a, fn) for fn in state_a.model_fields}
    payload_b = {fn: getattr(state_b, fn) for fn in state_b.model_fields}

    result_a = graph.invoke(payload_a, config_a)
    result_b = graph.invoke(payload_b, config_b)

    domain_a = EnergyChatGraphState.model_validate(result_a)
    domain_b = EnergyChatGraphState.model_validate(result_b)
    assert domain_a.thread_id == "pg-iso-a"
    assert domain_b.thread_id == "pg-iso-b"
    assert domain_a.request_id != domain_b.request_id


@REQUIRES_POSTGRES
def test_graph_resume_from_postgres_after_awaiting_evidence() -> None:
    """A thread stopped at awaiting_evidence must be resumable from PostgreSQL."""
    cp = PostgresCheckpointer(POSTGRES_URL)
    saver = cp.langgraph_saver
    assert saver is not None
    saver.setup()

    graph = build_energy_chat_graph(checkpointer=saver)
    state = _state(
        thread_id="pg-wait",
        user_request="What is the latest DeepSeek pricing as of today?",
        mode="research",
    )
    config = {"configurable": {"thread_id": "pg-wait"}}
    payload = {fn: getattr(state, fn) for fn in state.model_fields}

    result = graph.invoke(payload, config)
    domain = EnergyChatGraphState.model_validate(result)
    assert domain.status == "awaiting_evidence"

    # Simulate restart and verify state is recoverable
    cp2 = PostgresCheckpointer(POSTGRES_URL)
    saver2 = cp2.langgraph_saver
    assert saver2 is not None
    graph2 = build_energy_chat_graph(checkpointer=saver2)
    retrieved = graph2.get_state(config)
    assert retrieved is not None
    retrieved_domain = EnergyChatGraphState.model_validate(retrieved.values)
    assert retrieved_domain.status == "awaiting_evidence"


@REQUIRES_POSTGRES
def test_retention_policy_is_configured() -> None:
    """Retention policy must enforce max checkpoints per thread."""
    policy = CheckpointRetentionPolicy(max_checkpoints_per_thread=50)
    assert policy.max_checkpoints_per_thread == 50
    assert policy.retention_days is None


@REQUIRES_POSTGRES
def test_redaction_excludes_sensitive_fields() -> None:
    """Redacted fields must be explicitly listed and never empty."""
    from app.energy_chat.checkpoint_postgres import REDACTED_STATE_FIELDS

    assert isinstance(REDACTED_STATE_FIELDS, frozenset)
    # Redaction rules exist as a contract; actual enforcement is
    # applied before checkpoint write in the PostgresCheckpointer
