"""Application service for starting, inspecting, and resuming reviewed graphs."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from langgraph.types import Command

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.generation.graph.state import new_estimation_graph_state
from app.schemas.human_review import (
    FinalEstimateReviewDecision,
    HumanReviewMode,
    StructureReviewDecision,
)
from app.schemas.review_policy import ExecutionBudgetSnapshot
from app.services.checkpoint_scenarios import (
    CheckpointRecord,
    ScenarioSnapshot,
    branch_checkpoint,
    compare_scenario_states,
    list_checkpoint_records,
    read_checkpoint,
)
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

    def aget_state_history(
        self,
        config: dict[str, object],
        *,
        limit: int | None = None,
    ) -> AsyncIterator[ScenarioSnapshot]:
        """Iterate persisted snapshots newest first."""

    async def aupdate_state(
        self,
        config: dict[str, object],
        values: dict[str, object],
        as_node: str | None = None,
    ) -> dict[str, object]:
        """Create a checkpoint on the selected thread."""

    def astream(
        self,
        input: ReviewedEstimationGraphState,
        config: dict[str, object] | None = None,
        *,
        stream_mode: str,
    ) -> AsyncIterator[Mapping[str, object]]:
        """Stream graph updates for one reviewed execution."""


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
    graph: ReviewedGraphRunner

    async def start(
        self,
        *,
        transcript: str,
        human_review_mode: HumanReviewMode,
        estimation_id: UUID | None = None,
        v2_profile: str | None = None,
        project_context: dict[str, object] | None = None,
        execution_budgets: dict[str, object] | None = None,
        execution_metadata: dict[str, object] | None = None,
        provider: str | None = None,
        reasoning: str | None = None,
        context_detail: str | None = None,
    ) -> ReviewedGraphRun:
        """Start a reviewed graph and return either a pause or terminal state."""

    async def resume_structure_review(
        self,
        *,
        estimation_id: UUID,
        decision: StructureReviewDecision,
    ) -> ReviewedGraphRun:
        """Resume the same persisted thread with one validated human decision."""

    async def resume_final_review(
        self,
        *,
        estimation_id: UUID,
        decision: FinalEstimateReviewDecision,
    ) -> ReviewedGraphRun:
        """Resume the final estimate gate on the same persisted thread."""

    async def inspect(
        self,
        *,
        estimation_id: UUID,
    ) -> ReviewedGraphRun:
        """Read the latest persisted reviewed-graph state without executing nodes."""

    async def checkpoint_history(
        self, *, estimation_id: UUID, limit: int = 50
    ) -> tuple[CheckpointRecord, ...]:
        """List checkpoint history without mutating the graph."""

    async def inspect_checkpoint(
        self, *, estimation_id: UUID, checkpoint_id: str
    ) -> CheckpointRecord:
        """Read one exact historical checkpoint."""

    async def branch_scenario(
        self,
        *,
        estimation_id: UUID,
        checkpoint_id: str,
        scenario_id: str,
    ) -> ReviewedGraphRun:
        """Create a new scenario thread from one checkpoint."""

    async def compare_scenarios(
        self, *, left_estimation_id: UUID, right_estimation_id: UUID
    ) -> dict[str, object]:
        """Compare product-relevant state across two scenarios."""


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
        v2_profile: str | None = None,
        project_context: dict[str, object] | None = None,
        execution_budgets: dict[str, object] | None = None,
        execution_metadata: dict[str, object] | None = None,
        provider: str | None = None,
        reasoning: str | None = None,
        context_detail: str | None = None,
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
                "final_review_revision": 0,
                "execution_budgets": execution_budgets
                or ExecutionBudgetSnapshot().model_dump(mode="json"),
            }
        )
        if v2_profile is not None:
            initial_state["v2_profile"] = v2_profile
        if project_context is not None:
            initial_state["project_context"] = project_context
        if execution_metadata is not None:
            initial_state["execution_metadata"] = execution_metadata
        if provider is not None or reasoning is not None or context_detail is not None:
            initial_state["provider_selection"] = {
                "provider": provider or "deepseek",
                "reasoning": reasoning or "medium",
                "context_detail": context_detail or "medium",
            }
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
    async def resume_final_review(
        self,
        *,
        estimation_id: UUID,
        decision: FinalEstimateReviewDecision,
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

    async def checkpoint_history(
        self, *, estimation_id: UUID, limit: int = 50
    ) -> tuple[CheckpointRecord, ...]:
        return await list_checkpoint_records(
            self.graph,
            estimation_id=str(estimation_id),
            limit=limit,
        )

    async def inspect_checkpoint(
        self, *, estimation_id: UUID, checkpoint_id: str
    ) -> CheckpointRecord:
        return await read_checkpoint(
            self.graph,
            estimation_id=str(estimation_id),
            checkpoint_id=checkpoint_id,
        )

    async def branch_scenario(
        self,
        *,
        estimation_id: UUID,
        checkpoint_id: str,
        scenario_id: str,
    ) -> ReviewedGraphRun:
        branch = await branch_checkpoint(
            self.graph,
            estimation_id=str(estimation_id),
            checkpoint_id=checkpoint_id,
            scenario_id=scenario_id,
        )
        return ReviewedGraphRun(
            estimation_id=branch.estimation_id,
            thread_id=branch.thread_id,
            execution_status="completed",
            state=branch.state,
            next_nodes=(),
            interrupts=(),
        )

    async def compare_scenarios(
        self, *, left_estimation_id: UUID, right_estimation_id: UUID
    ) -> dict[str, object]:
        left = await self.inspect(estimation_id=left_estimation_id)
        right = await self.inspect(estimation_id=right_estimation_id)
        return compare_scenario_states(left.state, right.state)

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
