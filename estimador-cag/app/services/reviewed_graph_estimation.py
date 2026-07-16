"""Application service for starting, inspecting, and resuming reviewed graphs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from langgraph.types import Command

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.generation.graph.state import new_estimation_graph_state
from app.schemas.human_review import HumanReviewMode, StructureReviewDecision
from app.schemas.review_policy import ExecutionBudgetSnapshot
from app.services.graph_estimation import (
    GraphStateSnapshot,
    thread_id_from_estimation_id,
)

ReviewedExecutionStatus = Literal["paused", "completed"]


class ReviewedGraphRunner(Protocol):
    async def aget_state(
        self,
        config: dict[str, object],
    ) -> GraphStateSnapshot:
        """Return the latest persisted state for one reviewed thread."""

    async def ainvoke(
        self,
        input: ReviewedEstimationGraphState | Command,
        config: dict[str, object] | None = None,
    ) -> Mapping[str, object]:
        """Start or resume one reviewed graph execution."""


class ReviewedGraphNotFoundError(LookupError):
    """Raised when no checkpoint exists for a requested estimation identity."""


@dataclass(frozen=True)
class ReviewedGraphRun:
    """One paused or completed reviewed graph execution snapshot."""

    estimation_id: str
    thread_id: str
    execution_status: ReviewedExecutionStatus
    state: ReviewedEstimationGraphState
    next_nodes: tuple[str, ...]
    interrupts: tuple[dict[str, Any], ...]


class ReviewedGraphEstimationApplication(Protocol):
    async def start(
        self,
        *,
        transcript: str,
        human_review_mode: HumanReviewMode,
        estimation_id: UUID | None = None,
    ) -> ReviewedGraphRun:
        """Start a reviewed graph and return either a pause or terminal state."""

    async def resume_structure_review(
        self,
        *,
        estimation_id: UUID,
        decision: StructureReviewDecision,
    ) -> ReviewedGraphRun:
        """Resume the same persisted thread with one validated human decision."""

    async def inspect(
        self,
        *,
        estimation_id: UUID,
    ) -> ReviewedGraphRun:
        """Read the latest persisted reviewed-graph state without executing nodes."""


def _config(thread_id: str) -> dict[str, object]:
    return {"configurable": {"thread_id": thread_id}}


def _state_from_snapshot(snapshot: GraphStateSnapshot) -> ReviewedEstimationGraphState:
    if not isinstance(snapshot.values, Mapping) or not snapshot.values:
        raise ReviewedGraphNotFoundError("reviewed graph checkpoint was not found")
    return ReviewedEstimationGraphState(**dict(snapshot.values))


def _serialize_interrupt(raw_interrupt: object) -> dict[str, Any]:
    value = getattr(raw_interrupt, "value", raw_interrupt)
    interrupt_id = getattr(raw_interrupt, "id", None)
    return {
        "id": str(interrupt_id) if interrupt_id is not None else None,
        "value": value,
    }


def _interrupts_from_result(
    result: Mapping[str, object] | None,
    snapshot: GraphStateSnapshot,
) -> tuple[dict[str, Any], ...]:
    raw_interrupts: object = None
    if isinstance(result, Mapping):
        raw_interrupts = result.get("__interrupt__")
    if not raw_interrupts:
        raw_interrupts = getattr(snapshot, "interrupts", ())
    if not isinstance(raw_interrupts, (list, tuple)):
        return ()
    return tuple(_serialize_interrupt(item) for item in raw_interrupts)


def _validate_state_identity(
    state: ReviewedEstimationGraphState,
    *,
    estimation_id: str,
    graph_version: str,
) -> None:
    if state.get("estimation_id") != estimation_id:
        raise RuntimeError("reviewed graph estimation_id does not match the checkpoint")
    if state.get("graph_version") != graph_version:
        raise RuntimeError("reviewed graph version does not match the service")


@dataclass(frozen=True)
class ReviewedGraphEstimationService:
    """Drive durable human gates using a stable checkpoint thread identity."""

    graph: ReviewedGraphRunner
    graph_version: str = "session13.plus.v1"

    async def start(
        self,
        *,
        transcript: str,
        human_review_mode: HumanReviewMode,
        estimation_id: UUID | None = None,
    ) -> ReviewedGraphRun:
        resolved_estimation_id = str(estimation_id or uuid4())
        thread_id = thread_id_from_estimation_id(resolved_estimation_id)
        initial_state = ReviewedEstimationGraphState(
            **new_estimation_graph_state(
                transcript=transcript,
                estimation_id=resolved_estimation_id,
                graph_version=self.graph_version,
            )
        )
        initial_state.update(
            {
                "human_review_mode": human_review_mode,
                "structure_review_revision": 0,
                "execution_budgets": ExecutionBudgetSnapshot().model_dump(mode="json"),
            }
        )
        result = await self.graph.ainvoke(
            initial_state,
            config=_config(thread_id),
        )
        return await self._read_run(
            estimation_id=resolved_estimation_id,
            thread_id=thread_id,
            result=result,
        )

    async def resume_structure_review(
        self,
        *,
        estimation_id: UUID,
        decision: StructureReviewDecision,
    ) -> ReviewedGraphRun:
        resolved_estimation_id = str(estimation_id)
        thread_id = thread_id_from_estimation_id(resolved_estimation_id)
        await self.inspect(estimation_id=estimation_id)
        result = await self.graph.ainvoke(
            Command(resume=decision.model_dump(mode="json", exclude_none=True)),
            config=_config(thread_id),
        )
        return await self._read_run(
            estimation_id=resolved_estimation_id,
            thread_id=thread_id,
            result=result,
        )

    async def inspect(
        self,
        *,
        estimation_id: UUID,
    ) -> ReviewedGraphRun:
        resolved_estimation_id = str(estimation_id)
        thread_id = thread_id_from_estimation_id(resolved_estimation_id)
        return await self._read_run(
            estimation_id=resolved_estimation_id,
            thread_id=thread_id,
            result=None,
        )

    async def _read_run(
        self,
        *,
        estimation_id: str,
        thread_id: str,
        result: Mapping[str, object] | None,
    ) -> ReviewedGraphRun:
        snapshot = await self.graph.aget_state(_config(thread_id))
        state = _state_from_snapshot(snapshot)
        _validate_state_identity(
            state,
            estimation_id=estimation_id,
            graph_version=self.graph_version,
        )
        next_nodes = tuple(snapshot.next)
        interrupts = _interrupts_from_result(result, snapshot)
        execution_status: ReviewedExecutionStatus = (
            "paused" if next_nodes or interrupts else "completed"
        )
        return ReviewedGraphRun(
            estimation_id=estimation_id,
            thread_id=thread_id,
            execution_status=execution_status,
            state=state,
            next_nodes=next_nodes,
            interrupts=interrupts,
        )
