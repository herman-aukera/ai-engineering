"""In-memory checkpointing for the Energy Aware Chat graph.

Provides thread-isolated checkpoint storage using LangGraph's MemorySaver and
safe domain-state inspection for application-lifetime replay. State remains
process-local and is lost after restart.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.energy_chat.checkpoint_strict import STRICT_MSGPACK_ALLOWLIST
from app.energy_chat.graph_state import EnergyChatGraphState


class InMemoryCheckpointer:
    """Product-local wrapper around LangGraph MemorySaver.

    Public thread IDs identify conversations while checkpoint namespaces identify
    individual requests within a thread. The wrapper exposes validated domain
    state only; raw checkpoint internals are never returned by the API.
    """

    def __init__(self) -> None:
        self._saver = MemorySaver(
            serde=JsonPlusSerializer(
                allowed_msgpack_modules=STRICT_MSGPACK_ALLOWLIST,
            )
        )

    @property
    def langgraph_saver(self) -> MemorySaver:
        """Return the underlying LangGraph checkpointer for graph compilation."""

        return self._saver

    @staticmethod
    def config(thread_id: str, checkpoint_namespace: str = "") -> dict[str, Any]:
        """Build one LangGraph checkpoint configuration."""

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
    ) -> EnergyChatGraphState | None:
        """Return the latest validated domain state for one checkpoint lineage."""

        checkpoint_tuple = self._saver.get_tuple(
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
        """Return the latest opaque checkpoint identifier for audit projection."""

        checkpoint_tuple = self._saver.get_tuple(
            self.config(thread_id, checkpoint_namespace)
        )
        if checkpoint_tuple is None:
            return None

        configurable = checkpoint_tuple.config.get("configurable", {})
        checkpoint_id = configurable.get("checkpoint_id")
        return str(checkpoint_id) if checkpoint_id is not None else None
