"""Application service that safely invokes a checkpointed estimation graph."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from app.generation.graph.build import GRAPH_NAME
from app.generation.graph.observability import (
    NOOP_GRAPH_TRACER,
    ROOT_SPAN_NAME,
    GraphSpan,
    GraphTracer,
)
from app.generation.graph.state import (
    EstimationGraphState,
    new_estimation_graph_state,
)

THREAD_ID_PREFIX = "estimate:"
MAX_THREAD_ID_LENGTH = 128


class GraphStateSnapshot(Protocol):
    """Latest checkpoint state required for execution routing."""

    values: Mapping[str, object]
    next: tuple[str, ...]


class GraphRunner(Protocol):
    """Minimal checkpointed-graph interface required by the service."""

    async def aget_state(
        self,
        config: dict[str, object],
    ) -> GraphStateSnapshot:
        """Return the latest state snapshot for one thread."""

    async def ainvoke(
        self,
        input: EstimationGraphState | None,
        config: dict[str, object] | None = None,
    ) -> Mapping[str, object]:
        """Start or resume one graph execution."""


class GraphStateFactory(Protocol):
    """Build one checkpoint-safe initial state for a graph version."""

    def __call__(
        self,
        *,
        transcript: str,
        estimation_id: str,
        graph_version: str,
    ) -> EstimationGraphState:
        """Return a new independent graph state."""


class GraphResultContractError(RuntimeError):
    """Raised when graph state violates the application contract."""


@dataclass(frozen=True)
class GraphEstimationRun:
    """One completed application-service graph invocation."""

    estimation_id: str
    thread_id: str
    state: EstimationGraphState


class GraphEstimationApplication(Protocol):
    """Router-facing application-service contract."""

    async def estimate(
        self,
        *,
        transcript: str,
        estimation_id: UUID | None = None,
    ) -> GraphEstimationRun:
        """Create, resume, or return one estimation thread."""


def thread_id_from_estimation_id(
    estimation_id: str,
) -> str:
    """Derive a stable, bounded checkpoint thread identifier."""

    normalized = estimation_id.strip()

    if not normalized:
        raise ValueError("estimation_id must not be blank")

    thread_id = f"{THREAD_ID_PREFIX}{normalized}"

    if len(thread_id) > MAX_THREAD_ID_LENGTH:
        raise ValueError(
            "derived thread_id exceeds the storage-safe limit"
        )

    return thread_id


def _state_from_mapping(
    value: object,
    *,
    context: str,
) -> EstimationGraphState:
    if not isinstance(value, Mapping):
        raise GraphResultContractError(
            f"{context} must be a mapping"
        )

    return EstimationGraphState(**dict(value))


def _validate_state_identity(
    state: EstimationGraphState,
    *,
    estimation_id: str,
    transcript: str,
    graph_version: str,
) -> None:
    if state.get("estimation_id") != estimation_id:
        raise GraphResultContractError(
            "graph state estimation_id does not match the request"
        )

    if state.get("graph_version") != graph_version:
        raise GraphResultContractError(
            "graph state graph_version does not match the service"
        )

    if state.get("transcript") != transcript:
        raise GraphResultContractError(
            "graph state transcript does not match the request"
        )


def _validate_terminal_state(
    value: object,
    *,
    estimation_id: str,
    transcript: str,
    graph_version: str,
) -> EstimationGraphState:
    state = _state_from_mapping(
        value,
        context="graph result",
    )

    _validate_state_identity(
        state,
        estimation_id=estimation_id,
        transcript=transcript,
        graph_version=graph_version,
    )

    if state.get("status") not in {
        "validated",
        "needs_review",
    }:
        raise GraphResultContractError(
            "graph result is not terminal"
        )

    if not isinstance(
        state.get("review_required"),
        bool,
    ):
        raise GraphResultContractError(
            "graph result review_required must be boolean"
        )

    if not isinstance(
        state.get("estimate"),
        Mapping,
    ):
        raise GraphResultContractError(
            "graph result does not contain an estimate"
        )

    return state


def _record_terminal_span_attributes(
    span: GraphSpan,
    state: EstimationGraphState,
) -> None:
    status = state.get("status")
    if isinstance(status, str):
        span.set_attribute("terminal_status", status)

    review_required = state.get("review_required")
    if isinstance(review_required, bool):
        span.set_attribute(
            "review_required",
            review_required,
        )

    for attribute_name, state_key in (
        ("requirement_count", "requirements"),
        ("component_count", "components"),
        ("budget_match_count", "budget_matches"),
        ("error_count", "errors"),
        ("trace_event_count", "trace_events"),
    ):
        value = state.get(state_key)
        span.set_attribute(
            attribute_name,
            len(value) if isinstance(value, list) else 0,
        )

    estimate = state.get("estimate")
    if isinstance(estimate, Mapping):
        total_hours = estimate.get("total_hours")
        if (
            isinstance(total_hours, (int, float))
            and not isinstance(total_hours, bool)
        ):
            span.set_attribute(
                "total_hours",
                float(total_hours),
            )


@dataclass(frozen=True)
class GraphEstimationService:
    """Run checkpointed graph threads without duplicating completed work."""

    graph: GraphRunner
    tracer: GraphTracer = NOOP_GRAPH_TRACER
    graph_version: str = "session13.v1"
    graph_name: str = GRAPH_NAME
    state_factory: GraphStateFactory = new_estimation_graph_state

    async def estimate(
        self,
        *,
        transcript: str,
        estimation_id: UUID | None = None,
    ) -> GraphEstimationRun:
        resolved_estimation_id = str(
            estimation_id or uuid4()
        )
        thread_id = thread_id_from_estimation_id(
            resolved_estimation_id
        )

        with self.tracer.span(
            ROOT_SPAN_NAME,
            graph_name=self.graph_name,
            graph_version=self.graph_version,
            estimation_id=resolved_estimation_id,
            thread_id=thread_id,
        ) as span:
            return await self._estimate_with_span(
                transcript=transcript,
                resolved_estimation_id=(
                    resolved_estimation_id
                ),
                thread_id=thread_id,
                span=span,
            )

    async def _estimate_with_span(
        self,
        *,
        transcript: str,
        resolved_estimation_id: str,
        thread_id: str,
        span: GraphSpan,
    ) -> GraphEstimationRun:
        config: dict[str, object] = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        snapshot = await self.graph.aget_state(config)

        if not isinstance(snapshot.values, Mapping):
            raise GraphResultContractError(
                "graph snapshot values must be a mapping"
            )

        next_nodes = tuple(snapshot.next)
        saved_state: EstimationGraphState | None = None

        if snapshot.values:
            saved_state = _state_from_mapping(
                snapshot.values,
                context="graph snapshot",
            )
            _validate_state_identity(
                saved_state,
                estimation_id=resolved_estimation_id,
                transcript=transcript,
                graph_version=self.graph_version,
            )
        elif next_nodes:
            raise GraphResultContractError(
                "empty graph snapshot cannot have pending nodes"
            )

        if saved_state is not None and not next_nodes:
            span.set_attribute(
                "execution_mode",
                "completed",
            )
            final_state = _validate_terminal_state(
                saved_state,
                estimation_id=resolved_estimation_id,
                transcript=transcript,
                graph_version=self.graph_version,
            )
        else:
            if saved_state is None:
                span.set_attribute(
                    "execution_mode",
                    "new",
                )
                graph_input: EstimationGraphState | None = (
                    self.state_factory(
                        transcript=transcript,
                        estimation_id=resolved_estimation_id,
                        graph_version=self.graph_version,
                    )
                )
            else:
                span.set_attribute(
                    "execution_mode",
                    "resume",
                )
                # Resume the checkpointed pending nodes. Supplying a fresh
                # state here would start another run and replay reducers.
                graph_input = None

            result = await self.graph.ainvoke(
                graph_input,
                config=config,
            )

            final_state = _validate_terminal_state(
                result,
                estimation_id=resolved_estimation_id,
                transcript=transcript,
                graph_version=self.graph_version,
            )

        _record_terminal_span_attributes(
            span,
            final_state,
        )

        return GraphEstimationRun(
            estimation_id=resolved_estimation_id,
            thread_id=thread_id,
            state=final_state,
        )
