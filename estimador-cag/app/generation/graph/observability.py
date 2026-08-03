"""Sanitized observability for mandatory, reviewed, and supervised graphs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractContextManager, nullcontext
from dataclasses import replace
from functools import lru_cache, wraps
from typing import Any, Protocol, cast

import logfire
from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from app.generation.graph.review_state import (
    ReviewedEstimationGraphState,
    Session14EstimationGraphState,
)
from app.generation.graph.state import EstimationGraphState
from app.schemas.provider_readiness import GraphStage, StageRouteDecision
from app.services.provider_readiness import graph_stage_inventory
from app.services.stage_routing_runtime import StageRoutingRuntime

ROOT_SPAN_NAME = "session13.graph.run"
NODE_SPAN_NAME = "session13.graph.node"
SESSION14_ROOT_SPAN_NAME = "session14.graph.run"
SESSION14_NODE_SPAN_NAME = "session14.graph.node"
UNIFIED_ROOT_SPAN_NAME = "session13_14_plus.graph.run"
UNIFIED_NODE_SPAN_NAME = "session13_14_plus.graph.node"


class GraphSpan(Protocol):
    """Minimal span handle required by graph instrumentation."""

    def set_attribute(self, name: str, value: object) -> None:
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
    def set_attribute(self, name: str, value: object) -> None:
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


def flush_logfire_graph_traces(*, timeout_millis: int = 5_000) -> bool:
    """Flush completed graph spans before the application process exits."""

    return logfire.force_flush(timeout_millis=timeout_millis)


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
Session14CommandNode = Callable[
    [Session14EstimationGraphState],
    Awaitable[Command[Any]],
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


def _record_session14_command_attributes(
    *,
    span: GraphSpan,
    command: Command[Any],
) -> None:
    update = command.update
    state_update = dict(update) if isinstance(update, Mapping) else {}
    _record_update_attributes(
        span=span,
        update=cast(Session14EstimationGraphState, state_update),
    )
    span.set_attribute("execution_status", "completed")
    span.set_attribute("goto", _safe_text(command.goto))

    for attribute_name in (
        "current_agent",
        "next_agent",
        "route_reason_code",
        "human_review_status",
    ):
        value = state_update.get(attribute_name)
        if isinstance(value, str) and value.strip():
            span.set_attribute(attribute_name, value.strip())

    routing_steps = state_update.get("routing_steps")
    if isinstance(routing_steps, int) and not isinstance(routing_steps, bool):
        span.set_attribute("routing_steps", routing_steps)

    route_events = state_update.get("route_events")
    if isinstance(route_events, list) and route_events:
        latest_route = route_events[-1]
        if isinstance(latest_route, Mapping):
            for attribute_name in (
                "route_source",
                "proposed_agent",
                "fallback_reason",
            ):
                value = latest_route.get(attribute_name)
                if isinstance(value, str) and value.strip():
                    span.set_attribute(attribute_name, value.strip())
            valid_candidates = latest_route.get("valid_candidates")
            if isinstance(valid_candidates, list):
                span.set_attribute(
                    "valid_candidates",
                    [value for value in valid_candidates if isinstance(value, str)],
                )

    actions = state_update.get("human_review_actions")
    if isinstance(actions, list) and actions:
        action = actions[-1]
        if isinstance(action, Mapping):
            action_name = action.get("action")
            if isinstance(action_name, str) and action_name.strip():
                span.set_attribute("human_review_action", action_name.strip())

    contributions = state_update.get("agent_contributions")
    if isinstance(contributions, list) and contributions:
        contribution = contributions[-1]
        if isinstance(contribution, Mapping):
            for attribute_name in (
                "agent_id",
                "action",
                "tool_name",
                "privilege_decision",
                "execution_status",
                "result_ref",
            ):
                value = contribution.get(attribute_name)
                if isinstance(value, str) and value.strip():
                    span.set_attribute(
                        f"action_audit.{attribute_name}",
                        value.strip(),
                    )
            duration_ms = contribution.get("duration_ms")
            if (
                isinstance(duration_ms, int)
                and not isinstance(duration_ms, bool)
                and duration_ms >= 0
            ):
                span.set_attribute("action_audit.duration_ms", duration_ms)
            input_shape = contribution.get("validated_input_shape")
            if isinstance(input_shape, Mapping):
                span.set_attribute(
                    "action_audit.validated_input_keys",
                    sorted(key for key in input_shape if isinstance(key, str)),
                )


def instrument_graph_node(
    *,
    graph_name: str,
    node_name: str,
    node: GraphNode,
    tracer: GraphTracer,
) -> GraphNode:
    """Wrap one mandatory graph node without recording state payloads."""

    async def instrumented_node(state: EstimationGraphState) -> EstimationGraphState:
        with tracer.span(
            NODE_SPAN_NAME,
            graph_name=graph_name,
            node_name=node_name,
            estimation_id=_safe_text(state.get("estimation_id")),
            graph_version=_safe_text(state.get("graph_version")),
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
    """Wrap one reviewed node and bind its capability-authorized stage route."""

    known_stages = frozenset(graph_stage_inventory())

    async def instrumented_node(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState | Command:
        with tracer.span(
            NODE_SPAN_NAME,
            graph_name=graph_name,
            node_name=node_name,
            estimation_id=_safe_text(state.get("estimation_id")),
            graph_version=_safe_text(state.get("graph_version")),
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


def instrument_session14_command_node(
    *,
    graph_name: str,
    node_name: str,
    node: Session14CommandNode,
    tracer: GraphTracer,
    span_name: str = SESSION14_NODE_SPAN_NAME,
) -> Session14CommandNode:
    """Trace a command node without persisting state or interrupt payloads."""

    @wraps(node)
    async def instrumented_node(
        state: Session14EstimationGraphState,
    ) -> Command[Any]:
        graph_interrupt: GraphInterrupt | None = None
        command: Command[Any] | None = None

        with tracer.span(
            span_name,
            graph_name=graph_name,
            node_name=node_name,
            estimation_id=_safe_text(state.get("estimation_id")),
            graph_version=_safe_text(state.get("graph_version")),
        ) as span:
            try:
                command = await node(state)
            except GraphInterrupt as exc:
                graph_interrupt = exc
                span.set_attribute(
                    "execution_status",
                    "awaiting_human_review",
                )
            else:
                _record_session14_command_attributes(
                    span=span,
                    command=command,
                )

        if graph_interrupt is not None:
            raise graph_interrupt
        if command is None:
            raise RuntimeError("Command node produced no command")
        return command

    return instrumented_node
