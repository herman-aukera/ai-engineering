"""Read-only checkpoint history and non-destructive scenario branching."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.services.graph_estimation import thread_id_from_estimation_id


class ScenarioSnapshot(Protocol):
    values: Mapping[str, object]
    next: tuple[str, ...]
    config: Mapping[str, object]
    created_at: str | None


class ScenarioGraph(Protocol):
    def aget_state_history(
        self,
        config: dict[str, object],
        *,
        limit: int | None = None,
    ) -> AsyncIterator[ScenarioSnapshot]: ...

    async def aget_state(self, config: dict[str, object]) -> ScenarioSnapshot: ...

    async def aupdate_state(
        self,
        config: dict[str, object],
        values: dict[str, object],
        as_node: str | None = None,
    ) -> dict[str, object]: ...


@dataclass(frozen=True)
class CheckpointRecord:
    checkpoint_id: str
    created_at: str | None
    next_nodes: tuple[str, ...]
    state: ReviewedEstimationGraphState


@dataclass(frozen=True)
class ScenarioBranch:
    estimation_id: str
    thread_id: str
    scenario_id: str
    parent_estimation_id: str
    parent_checkpoint_id: str
    state: ReviewedEstimationGraphState


def _config(thread_id: str, checkpoint_id: str | None = None) -> dict[str, object]:
    configurable = {"thread_id": thread_id}
    if checkpoint_id is not None:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}


def _checkpoint_id(snapshot: ScenarioSnapshot) -> str:
    configurable = snapshot.config.get("configurable", {})
    value = configurable.get("checkpoint_id") if isinstance(configurable, Mapping) else None
    if not isinstance(value, str) or not value:
        raise ValueError("checkpoint snapshot is missing checkpoint_id")
    return value


def _state(snapshot: ScenarioSnapshot) -> ReviewedEstimationGraphState:
    if not snapshot.values:
        raise LookupError("checkpoint state was not found")
    return ReviewedEstimationGraphState(**deepcopy(dict(snapshot.values)))


async def list_checkpoint_records(
    graph: ScenarioGraph,
    *,
    estimation_id: str,
    limit: int = 50,
) -> tuple[CheckpointRecord, ...]:
    """List immutable snapshots without invoking or updating the graph."""

    if limit <= 0 or limit > 200:
        raise ValueError("checkpoint history limit must be between 1 and 200")
    thread_id = thread_id_from_estimation_id(estimation_id)
    records: list[CheckpointRecord] = []
    async for snapshot in graph.aget_state_history(_config(thread_id), limit=limit):
        records.append(
            CheckpointRecord(
                checkpoint_id=_checkpoint_id(snapshot),
                created_at=snapshot.created_at,
                next_nodes=tuple(snapshot.next),
                state=_state(snapshot),
            )
        )
    if not records:
        raise LookupError("checkpoint history was not found")
    return tuple(records)


async def read_checkpoint(
    graph: ScenarioGraph,
    *,
    estimation_id: str,
    checkpoint_id: str,
) -> CheckpointRecord:
    """Read one selected checkpoint without altering canonical history."""

    thread_id = thread_id_from_estimation_id(estimation_id)
    snapshot = await graph.aget_state(_config(thread_id, checkpoint_id))
    return CheckpointRecord(
        checkpoint_id=_checkpoint_id(snapshot),
        created_at=snapshot.created_at,
        next_nodes=tuple(snapshot.next),
        state=_state(snapshot),
    )


async def branch_checkpoint(
    graph: ScenarioGraph,
    *,
    estimation_id: str,
    checkpoint_id: str,
    scenario_id: str,
) -> ScenarioBranch:
    """Clone selected state into a new thread while preserving lineage."""

    normalized_scenario = scenario_id.strip()
    if not normalized_scenario:
        raise ValueError("scenario_id must not be blank")
    source = await read_checkpoint(
        graph,
        estimation_id=estimation_id,
        checkpoint_id=checkpoint_id,
    )
    new_estimation_id = str(uuid4())
    new_thread_id = thread_id_from_estimation_id(new_estimation_id)
    state = deepcopy(source.state)
    state.update(
        {
            "estimation_id": new_estimation_id,
            "scenario_id": normalized_scenario,
            "parent_estimation_id": estimation_id,
            "parent_checkpoint_id": checkpoint_id,
            "trace_events": [
                *deepcopy(source.state.get("trace_events", [])),
                {
                    "event_type": "scenario_branched",
                    "node": "scenario_branch",
                    "summary": f"Created scenario {normalized_scenario} from a checkpoint.",
                    "evidence_refs": [estimation_id, checkpoint_id],
                    "state_delta_keys": [
                        "scenario_id",
                        "parent_estimation_id",
                        "parent_checkpoint_id",
                        "trace_events",
                    ],
                }
            ],
        }
    )
    await graph.aupdate_state(_config(new_thread_id), dict(state))
    return ScenarioBranch(
        estimation_id=new_estimation_id,
        thread_id=new_thread_id,
        scenario_id=normalized_scenario,
        parent_estimation_id=estimation_id,
        parent_checkpoint_id=checkpoint_id,
        state=state,
    )


def compare_scenario_states(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> dict[str, object]:
    """Return deterministic product-relevant differences between scenarios."""

    def estimate_value(state: Mapping[str, Any], key: str) -> object:
        estimate = state.get("estimate", {})
        return estimate.get(key) if isinstance(estimate, Mapping) else None

    def count(state: Mapping[str, Any], key: str) -> int:
        value = state.get(key, [])
        return len(value) if isinstance(value, list) else 0

    def metadata(state: Mapping[str, Any], key: str) -> object:
        value = state.get("execution_metadata", {})
        return value.get(key) if isinstance(value, Mapping) else None

    fields = {
        "total_hours": (estimate_value(left, "total_hours"), estimate_value(right, "total_hours")),
        "evidence_count": (count(left, "budget_matches"), count(right, "budget_matches")),
        "critic_finding_count": (
            count(left.get("critic_report", {}), "issues") if isinstance(left.get("critic_report"), Mapping) else 0,
            count(right.get("critic_report", {}), "issues") if isinstance(right.get("critic_report"), Mapping) else 0,
        ),
        "estimated_cost_usd": (
            metadata(left, "estimated_cost_usd"),
            metadata(right, "estimated_cost_usd"),
        ),
        "elapsed_ms": (metadata(left, "elapsed_ms"), metadata(right, "elapsed_ms")),
    }
    return {
        key: {"left": values[0], "right": values[1], "changed": values[0] != values[1]}
        for key, values in fields.items()
    }
