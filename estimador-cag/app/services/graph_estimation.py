"""Application service that safely invokes a checkpointed estimation graph."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from langgraph.types import Command

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
from app.schemas.session14_human_review import (
    Session14HumanReviewDecision,
)
from app.services.session14_human_review import (
    action_record_matches_decision,
)

THREAD_ID_PREFIX = "estimate:"
MAX_THREAD_ID_LENGTH = 128


class GraphStateSnapshot(Protocol):
    """Latest checkpoint state required for execution routing."""

    values: Mapping[str, object]
    next: tuple[str, ...]
    interrupts: tuple[object, ...]


class GraphRunner(Protocol):
    """Minimal checkpointed-graph interface required by the service."""

    async def aget_state(
        self,
        config: dict[str, object],
    ) -> GraphStateSnapshot:
        """Return the latest state snapshot for one thread."""

    async def ainvoke(
        self,
        input: EstimationGraphState | Command | None,
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


class GraphEstimationNotFoundError(LookupError):
    """Raised when a resume target has no persisted checkpoint."""


class GraphHumanReviewConflictError(RuntimeError):
    """Raised for stale, conflicting, or non-pending review actions."""


@dataclass(frozen=True)
class GraphEstimationRun:
    """One completed or human-paused graph invocation."""

    estimation_id: str
    thread_id: str
    state: EstimationGraphState
    execution_status: Literal[
        "completed",
        "awaiting_human_review",
    ] = "completed"
    interrupts: tuple[dict[str, Any], ...] = ()


class GraphEstimationApplication(Protocol):
    """Router-facing application-service contract."""

    async def estimate(
        self,
        *,
        transcript: str,
        estimation_id: UUID | None = None,
    ) -> GraphEstimationRun:
        """Create, resume, or return one estimation thread."""

    async def resume_human_review(
        self,
        *,
        estimation_id: UUID,
        decision: Session14HumanReviewDecision,
    ) -> GraphEstimationRun:
        """Resume the persisted Session 14 interrupt on the same thread."""


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
    transcript: str | None,
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

    if transcript is not None and state.get("transcript") != transcript:
        raise GraphResultContractError(
            "graph state transcript does not match the request"
        )


def _validate_terminal_state(
    value: object,
    *,
    estimation_id: str,
    transcript: str | None,
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


def _validate_paused_state(
    value: object,
    *,
    estimation_id: str,
    transcript: str | None,
    graph_version: str,
) -> EstimationGraphState:
    state = _state_from_mapping(value, context="paused graph state")
    _validate_state_identity(
        state,
        estimation_id=estimation_id,
        transcript=transcript,
        graph_version=graph_version,
    )
    if state.get("review_required") is not True:
        raise GraphResultContractError(
            "paused graph state must require review"
        )
    if not isinstance(state.get("estimate"), Mapping):
        raise GraphResultContractError(
            "paused graph state does not contain an estimate"
        )
    return state


def _serialize_interrupt(raw_interrupt: object) -> dict[str, Any]:
    value = getattr(raw_interrupt, "value", raw_interrupt)
    interrupt_id = getattr(raw_interrupt, "id", None)
    return {
        "id": str(interrupt_id) if interrupt_id is not None else None,
        "value": value,
    }


def _interrupts(
    result: Mapping[str, object] | None,
    snapshot: GraphStateSnapshot,
) -> tuple[dict[str, Any], ...]:
    raw: object = result.get("__interrupt__") if result else None
    if not raw:
        raw = getattr(snapshot, "interrupts", ())
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(_serialize_interrupt(item) for item in raw)


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
    root_span_name: str = ROOT_SPAN_NAME
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
            self.root_span_name,
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
        saved_interrupts = _interrupts(None, snapshot)
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

        if saved_state is not None and saved_interrupts:
            span.set_attribute(
                "execution_mode",
                "awaiting_human_review",
            )
            paused_state = _validate_paused_state(
                saved_state,
                estimation_id=resolved_estimation_id,
                transcript=transcript,
                graph_version=self.graph_version,
            )
            run = GraphEstimationRun(
                estimation_id=resolved_estimation_id,
                thread_id=thread_id,
                state=paused_state,
                execution_status="awaiting_human_review",
                interrupts=saved_interrupts,
            )
            span.set_attribute(
                "execution_status",
                run.execution_status,
            )
            _record_terminal_span_attributes(span, paused_state)
            return run

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

            run = await self._run_after_invoke(
                estimation_id=resolved_estimation_id,
                thread_id=thread_id,
                transcript=transcript,
                result=result,
            )
            span.set_attribute(
                "execution_status",
                run.execution_status,
            )
            _record_terminal_span_attributes(span, run.state)
            return run

        _record_terminal_span_attributes(
            span,
            final_state,
        )
        span.set_attribute("execution_status", "completed")

        return GraphEstimationRun(
            estimation_id=resolved_estimation_id,
            thread_id=thread_id,
            state=final_state,
        )

    async def _run_after_invoke(
        self,
        *,
        estimation_id: str,
        thread_id: str,
        transcript: str | None,
        result: Mapping[str, object],
    ) -> GraphEstimationRun:
        if not isinstance(result, Mapping):
            raise GraphResultContractError(
                "graph result must be a mapping"
            )
        raw_interrupts = result.get("__interrupt__")
        if not raw_interrupts:
            state = _validate_terminal_state(
                result,
                estimation_id=estimation_id,
                transcript=transcript,
                graph_version=self.graph_version,
            )
            return GraphEstimationRun(
                estimation_id=estimation_id,
                thread_id=thread_id,
                state=state,
            )

        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await self.graph.aget_state(config)
        interrupts = _interrupts(result, snapshot)

        if interrupts:
            value: object = (
                snapshot.values if snapshot.values else result
            )
            state = _validate_paused_state(
                value,
                estimation_id=estimation_id,
                transcript=transcript,
                graph_version=self.graph_version,
            )
            return GraphEstimationRun(
                estimation_id=estimation_id,
                thread_id=thread_id,
                state=state,
                execution_status="awaiting_human_review",
                interrupts=interrupts,
            )

        raise GraphResultContractError(
            "graph returned an empty interrupt payload"
        )

    async def resume_human_review(
        self,
        *,
        estimation_id: UUID,
        decision: Session14HumanReviewDecision,
    ) -> GraphEstimationRun:
        resolved_estimation_id = str(estimation_id)
        thread_id = thread_id_from_estimation_id(
            resolved_estimation_id
        )
        with self.tracer.span(
            self.root_span_name,
            graph_name=self.graph_name,
            graph_version=self.graph_version,
            estimation_id=resolved_estimation_id,
            thread_id=thread_id,
            execution_mode="human_review_resume",
            human_review_action=decision.action,
            expected_revision=decision.expected_revision,
        ) as span:
            run = await self._resume_human_review(
                resolved_estimation_id=resolved_estimation_id,
                thread_id=thread_id,
                decision=decision,
            )
            span.set_attribute(
                "execution_status",
                run.execution_status,
            )
            _record_terminal_span_attributes(span, run.state)
            human_review_status = run.state.get(
                "human_review_status"
            )
            if isinstance(human_review_status, str):
                span.set_attribute(
                    "human_review_status",
                    human_review_status,
                )
            return run

    async def _resume_human_review(
        self,
        *,
        resolved_estimation_id: str,
        thread_id: str,
        decision: Session14HumanReviewDecision,
    ) -> GraphEstimationRun:
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await self.graph.aget_state(config)

        if not isinstance(snapshot.values, Mapping) or not snapshot.values:
            raise GraphEstimationNotFoundError(
                "estimation checkpoint was not found"
            )

        state = _state_from_mapping(
            snapshot.values,
            context="graph snapshot",
        )
        _validate_state_identity(
            state,
            estimation_id=resolved_estimation_id,
            transcript=None,
            graph_version=self.graph_version,
        )

        actions = state.get("human_review_actions", [])
        if isinstance(actions, list):
            existing = next(
                (
                    item
                    for item in actions
                    if isinstance(item, Mapping)
                    and item.get("idempotency_key")
                    == decision.idempotency_key
                ),
                None,
            )
            if existing is not None:
                if not action_record_matches_decision(
                    existing,
                    decision,
                ):
                    raise GraphHumanReviewConflictError(
                        "idempotency key was already used for a "
                        "different review action"
                    )
                if tuple(snapshot.next):
                    result = await self.graph.ainvoke(None, config=config)
                    return await self._run_after_invoke(
                        estimation_id=resolved_estimation_id,
                        thread_id=thread_id,
                        transcript=None,
                        result=result,
                    )
                final_state = _validate_terminal_state(
                    state,
                    estimation_id=resolved_estimation_id,
                    transcript=None,
                    graph_version=self.graph_version,
                )
                return GraphEstimationRun(
                    estimation_id=resolved_estimation_id,
                    thread_id=thread_id,
                    state=final_state,
                )

        if not _interrupts(None, snapshot):
            raise GraphHumanReviewConflictError(
                "estimation is not awaiting human review"
            )

        revision = state.get("human_review_revision")
        if revision != decision.expected_revision:
            raise GraphHumanReviewConflictError(
                "human review revision "
                f"{decision.expected_revision} does not match {revision}"
            )

        result = await self.graph.ainvoke(
            Command(
                resume=decision.model_dump(
                    mode="json",
                    exclude_none=True,
                )
            ),
            config=config,
        )
        return await self._run_after_invoke(
            estimation_id=resolved_estimation_id,
            thread_id=thread_id,
            transcript=None,
            result=result,
        )
