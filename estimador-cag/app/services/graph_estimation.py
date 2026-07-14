"""Application service that invokes the compiled estimation graph."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, cast
from uuid import UUID, uuid4

from app.generation.graph.state import (
    EstimationGraphState,
    new_estimation_graph_state,
)

THREAD_ID_PREFIX = "estimate:"
MAX_THREAD_ID_LENGTH = 128


class GraphRunner(Protocol):
    """Minimal compiled-graph interface required by the service."""

    async def ainvoke(
        self,
        input: EstimationGraphState,
        config: dict[str, object] | None = None,
    ) -> Mapping[str, object]:
        """Execute one graph run and return its terminal state."""


class GraphResultContractError(RuntimeError):
    """Raised when a graph returns a malformed or nonterminal state."""


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
        """Run or resume the graph thread identified by estimation_id."""


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


@dataclass(frozen=True)
class GraphEstimationService:
    """Invoke a compiled graph behind a stable application boundary."""

    graph: GraphRunner
    graph_version: str = "session13.v1"

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

        initial_state = new_estimation_graph_state(
            transcript=transcript,
            estimation_id=resolved_estimation_id,
            graph_version=self.graph_version,
        )
        config: dict[str, object] = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        result = await self.graph.ainvoke(
            initial_state,
            config=config,
        )

        if not isinstance(result, Mapping):
            raise GraphResultContractError(
                "graph result must be a mapping"
            )

        final_state = cast(
            EstimationGraphState,
            dict(result),
        )

        if (
            final_state.get("estimation_id")
            != resolved_estimation_id
        ):
            raise GraphResultContractError(
                "graph result estimation_id does not match the request"
            )

        if final_state.get("graph_version") != self.graph_version:
            raise GraphResultContractError(
                "graph result graph_version does not match the service"
            )

        if final_state.get("status") not in {
            "validated",
            "needs_review",
        }:
            raise GraphResultContractError(
                "graph result is not terminal"
            )

        if not isinstance(
            final_state.get("review_required"),
            bool,
        ):
            raise GraphResultContractError(
                "graph result review_required must be boolean"
            )

        if not isinstance(
            final_state.get("estimate"),
            Mapping,
        ):
            raise GraphResultContractError(
                "graph result does not contain an estimate"
            )

        return GraphEstimationRun(
            estimation_id=resolved_estimation_id,
            thread_id=thread_id,
            state=final_state,
        )
