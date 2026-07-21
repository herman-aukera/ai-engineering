"""Real PostgreSQL integration proof for EACHAT checkpointing."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph

from app.energy_chat.api_v2_contracts import (
    EnergyChatV2HumanResumeRequest,
    EnergyChatV2Request,
)
from app.energy_chat.checkpoint_postgres import (
    REDACTION_SENTINEL,
    CheckpointRetentionPolicy,
    PostgresCheckpointer,
)
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime

POSTGRES_URL = os.getenv("EACHAT_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="EACHAT_POSTGRES_URL is required for PostgreSQL integration proof",
)


class CounterState(TypedDict):
    value: int


def _counter_graph(checkpointer):
    builder = StateGraph(CounterState)
    builder.add_node("increment", lambda state: {"value": state["value"] + 1})
    builder.add_edge(START, "increment")
    builder.add_edge("increment", END)
    return builder.compile(checkpointer=checkpointer)


def test_postgres_setup_migration_redaction_and_completed_replay_after_restart() -> None:
    thread_id = "pg-completed-restart"
    first = PostgresCheckpointer(POSTGRES_URL, pool_min_size=1, pool_max_size=2)
    try:
        first.setup()
        assert first.migration_applied() is True
        runtime = EnergyChatApplicationRuntime(checkpointer=first)
        response = runtime.execute(
            EnergyChatV2Request(
                user_message="Sensitive user request that must be redacted",
                thread_id=thread_id,
                request_id="request-pg-completed",
                trace_id="trace-pg-completed",
            ),
            "deterministic",
        )
        assert response.provider_metrics_summary.provider_call_count == 1
        assert first.get_state(thread_id).user_request == REDACTION_SENTINEL
    finally:
        first.close()

    reopened = PostgresCheckpointer(POSTGRES_URL, pool_min_size=1, pool_max_size=2)
    try:
        reopened.setup()
        replay = EnergyChatApplicationRuntime(checkpointer=reopened).replay(thread_id)
        assert replay.replayed_from_checkpoint is True
        assert replay.checkpoint_id
        assert replay.provider_metrics_summary.provider_call_count == 1
        assert replay.final_answer
    finally:
        reopened.delete_thread(thread_id)
        reopened.close()


def test_pending_human_interrupt_resumes_after_new_runtime_and_pool() -> None:
    thread_id = "pg-human-restart"
    first = PostgresCheckpointer(POSTGRES_URL, pool_min_size=1, pool_max_size=2)
    try:
        first.setup()
        started = EnergyChatApplicationRuntime(checkpointer=first).execute_human(
            EnergyChatV2Request(
                user_message="Approve the production release.",
                thread_id=thread_id,
                request_id="request-pg-human",
                trace_id="trace-pg-human",
            )
        )
        pending = started.human_action_request
        assert started.graph_status == "awaiting_human"
        assert pending is not None
        assert started.provider_metrics_summary.provider_call_count == 1
    finally:
        first.close()

    reopened = PostgresCheckpointer(POSTGRES_URL, pool_min_size=1, pool_max_size=2)
    try:
        reopened.setup()
        resumed = EnergyChatApplicationRuntime(checkpointer=reopened).resume_human(
            thread_id,
            EnergyChatV2HumanResumeRequest(
                action_id=pending.action_id,
                action=pending.action,
                expected_revision=pending.expected_revision,
                actor="postgres-restart-test",
                payload={"response": "approved after restart"},
            ),
        )
        assert resumed.graph_status == "completed"
        assert resumed.provider_metrics_summary.provider_call_count == 1
        assert len(resumed.ledger_entry_ids) == 1
        persisted = reopened.get_state(thread_id)
        assert persisted.user_request == REDACTION_SENTINEL
        assert persisted.human_action_response is None
    finally:
        reopened.close()

    final_reopen = PostgresCheckpointer(POSTGRES_URL, pool_min_size=1, pool_max_size=2)
    try:
        final_reopen.setup()
        replay = EnergyChatApplicationRuntime(checkpointer=final_reopen).replay(thread_id)
        assert replay.graph_status == "completed"
        assert replay.replayed_from_checkpoint is True
        assert replay.provider_metrics_summary.provider_call_count == 1
    finally:
        final_reopen.delete_thread(thread_id)
        final_reopen.close()


def test_postgres_retention_executes_count_and_time_deletion() -> None:
    thread_id = "pg-retention-count"
    checkpointer = PostgresCheckpointer(POSTGRES_URL, pool_min_size=1, pool_max_size=2)
    try:
        checkpointer.setup()
        graph = _counter_graph(checkpointer.langgraph_saver)
        config = checkpointer.config(thread_id)
        for value in range(5):
            graph.invoke({"value": value}, config)

        before = list(checkpointer.langgraph_saver.list(config))
        assert len(before) > 2
        deleted = checkpointer.enforce_retention(
            thread_id,
            CheckpointRetentionPolicy(max_checkpoints_per_thread=2),
        )
        after = list(checkpointer.langgraph_saver.list(config))
        assert deleted == len(before) - 2
        assert len(after) == 2
        assert checkpointer.langgraph_saver.get_tuple(config) is not None

        expired = checkpointer.enforce_retention(
            thread_id,
            CheckpointRetentionPolicy(
                max_checkpoints_per_thread=100,
                retention_days=1,
            ),
            now=datetime.now(UTC) + timedelta(days=2),
        )
        assert expired == 2
        assert checkpointer.langgraph_saver.get_tuple(config) is None
    finally:
        checkpointer.delete_thread(thread_id)
        checkpointer.close()
