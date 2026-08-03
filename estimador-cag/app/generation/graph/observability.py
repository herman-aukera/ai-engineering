"""Sanitized Logfire spans for Session 13 graph execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractContextManager, nullcontext
from dataclasses import replace
from functools import lru_cache
from typing import Protocol, cast

import logfire
from langgraph.types import Command

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.generation.graph.state import EstimationGraphState
from app.schemas.provider_readiness import GraphStage, StageRouteDecision
from app.services.provider_readiness import graph_stage_inventory
from app.services.stage_routing_runtime import StageRoutingRuntime

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


@lru_cache(maxsize=1)
def get_stage_routing_runtime() -> StageRoutingRuntime:
    """Load one immutable policy snapshot for the application process."""

    return StageRoutingRuntime.from_settings()


GraphNode = Callable[
    [EstimationGraphState],
    Awaitable[EstimationGraphState],
]
ReviewedGraphNode = Callable[
    [ReviewedEstimationGraphState],
    Awaitable[ReviewedEstimationGraphState | Command],
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
    if not isinstance(state_update, Mapping):
        state_update = {}
    span.set_attribute(
        "state_delta_keys",
        sorted(str(key) for key in state_update),
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


def _with_stage_route(
    update: ReviewedEstimationGraphState | Command,
    route: StageRouteDecision,
) -> ReviewedEstimationGraphState | Command:
    route_event = route.model_dump(mode="json")
    if isinstance(update, Command):
        raw_update = update.update
        state_update = dict(raw_update) if isinstance(raw_update, Mapping) else {}
        state_update["stage_route_events"] = [route_event]
        return replace(update, update=state_update)
    state_update = dict(update)
    state_update["stage_route_events"] = [route_event]
    return cast(ReviewedEstimationGraphState, state_update)


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
    routing_runtime: StageRoutingRuntime | None = None,
) -> ReviewedGraphNode:
    """Wrap one Plus node, bind its route, and preserve Command routing."""

    known_stages = frozenset(graph_stage_inventory())

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
            if node_name not in known_stages:
                update = await node(state)
                _record_update_attributes(span=span, update=update)
                return update

            runtime = routing_runtime or get_stage_routing_runtime()
            route = runtime.resolve(
                stage=cast(GraphStage, node_name),
                state=state,
            )
            span.set_attribute("route.execution_kind", route.execution_kind)
            span.set_attribute("route.provider", route.provider)
            span.set_attribute("route.model", route.model)
            span.set_attribute("route.effort", route.effort)
            span.set_attribute("route.source", route.source)
            with runtime.bind(route):
                update = await node(state)
            routed_update = _with_stage_route(update, route)
            _record_update_attributes(span=span, update=routed_update)
            return routed_update

    return instrumented_node
