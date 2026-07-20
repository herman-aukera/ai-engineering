"""Sanitized Logfire spans for Session 13 graph execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager, nullcontext
from functools import lru_cache
from typing import Protocol, cast

import logfire
from langgraph.types import Command

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.generation.graph.state import EstimationGraphState

ROOT_SPAN_NAME = "session13.graph.run"
NODE_SPAN_NAME = "session13.graph.node"


class GraphSpan(Protocol):
    """Minimal span handle required by graph instrumentation."""

    def set_attribute(
        self,
        name: str,
        value: object,
    ) -> None:
        """Attach one sanitized attribute."""


class GraphTracer(Protocol):
    """Minimal tracer contract used by graph and service layers."""

    def span(
        self,
        name: str,
        **attributes: object,
    ) -> AbstractContextManager[GraphSpan]:
        """Create one telemetry span."""


class _NoopSpan:
    def set_attribute(
        self,
        name: str,
        value: object,
    ) -> None:
        return None


class NoopGraphTracer:
    """Tracer used by deterministic tests unless explicitly replaced."""

    def span(
        self,
        name: str,
        **attributes: object,
    ) -> AbstractContextManager[GraphSpan]:
        return nullcontext(_NoopSpan())


NOOP_GRAPH_TRACER = NoopGraphTracer()


class LogfireGraphTracer:
    """Production tracer backed by Logfire manual spans."""

    def span(
        self,
        name: str,
        **attributes: object,
    ) -> AbstractContextManager[GraphSpan]:
        return cast(
            AbstractContextManager[GraphSpan],
            logfire.span(name, **attributes),
        )


@lru_cache(maxsize=1)
def get_logfire_graph_tracer() -> LogfireGraphTracer:
    """Configure Logfire once without requiring remote credentials."""

    logfire.configure(
        send_to_logfire="if-token-present",
        service_name="estimador-cag",
        console=False,
        inspect_arguments=False,
    )
    return LogfireGraphTracer()


GraphNode = Callable[
    [EstimationGraphState],
    Awaitable[EstimationGraphState],
]
ReviewedGraphNode = Callable[
    [ReviewedEstimationGraphState],
    Awaitable[ReviewedEstimationGraphState],
]


def _safe_text(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unknown"


def _list_count(value: object) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def _record_update_attributes(
    *,
    span: GraphSpan,
    update: EstimationGraphState | ReviewedEstimationGraphState | Command,
) -> None:
    state_update = update.update if isinstance(update, Command) else update
    span.set_attribute(
        "state_delta_keys",
        sorted(state_update.keys()) if hasattr(state_update, "keys") else [],
    )
    span.set_attribute(
        "error_count",
        _list_count(state_update.get("errors")),
    )
    span.set_attribute(
        "trace_event_count",
        _list_count(state_update.get("trace_events")),
    )

    status = state_update.get("status")
    if isinstance(status, str):
        span.set_attribute("status", status)


def instrument_graph_node(
    *,
    graph_name: str,
    node_name: str,
    node: GraphNode,
    tracer: GraphTracer,
) -> GraphNode:
    """Wrap one mandatory graph node without recording state payloads."""

    async def instrumented_node(
        state: EstimationGraphState,
    ) -> EstimationGraphState:
        with tracer.span(
            NODE_SPAN_NAME,
            graph_name=graph_name,
            node_name=node_name,
            estimation_id=_safe_text(
                state.get("estimation_id")
            ),
            graph_version=_safe_text(
                state.get("graph_version")
            ),
        ) as span:
            update = await node(state)
            _record_update_attributes(span=span, update=update)
            return update

    return instrumented_node


def instrument_reviewed_graph_node(
    *,
    graph_name: str,
    node_name: str,
    node: ReviewedGraphNode,
    tracer: GraphTracer,
) -> ReviewedGraphNode:
    """Wrap one Plus node while preserving the reviewed-state schema.

    If the wrapped node returns a :class:`Command`, the instrumentation
    reads ``Command.update`` for span attributes and passes the Command
    through unchanged so routing (``goto``) works correctly.
    """

    async def instrumented_node(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState | Command:
        with tracer.span(
            NODE_SPAN_NAME,
            graph_name=graph_name,
            node_name=node_name,
            estimation_id=_safe_text(
                state.get("estimation_id")
            ),
            graph_version=_safe_text(
                state.get("graph_version")
            ),
        ) as span:
            update = await node(state)
            _record_update_attributes(span=span, update=update)
            return update

    return instrumented_node
