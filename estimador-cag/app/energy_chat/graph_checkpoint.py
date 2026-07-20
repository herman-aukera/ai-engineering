"""In-memory checkpointing for the Energy Aware Chat graph.

Provides thread-isolated checkpoint storage using LangGraph's MemorySaver.
No disk persistence, PostgreSQL, or human-interrupt lifecycle claimed.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver


class InMemoryCheckpointer:
    """Product-local wrapper around LangGraph MemorySaver.

    Provides thread isolation through LangGraph's built-in checkpoint
    mechanism. Each thread_id gets an independent checkpoint lineage.
    State is stored in memory only — process restart loses all checkpoints.
    """

    def __init__(self) -> None:
        self._saver = MemorySaver()

    @property
    def langgraph_saver(self) -> MemorySaver:
        """Return the underlying LangGraph checkpointer for graph compilation."""
        return self._saver
