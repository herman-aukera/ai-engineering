from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.checkpoint_scenarios import (
    branch_checkpoint,
    compare_scenario_states,
    list_checkpoint_records,
    read_checkpoint,
)


@dataclass
class Snapshot:
    values: dict[str, object]
    next: tuple[str, ...]
    config: dict[str, object]
    created_at: str | None = "2026-07-16T12:00:00Z"


class FakeScenarioGraph:
    def __init__(self) -> None:
        self.snapshots = [
            Snapshot(
                values={"estimation_id": "source", "estimate": {"total_hours": 40.0}},
                next=("final_estimate_review",),
                config={"configurable": {"thread_id": "estimate:source", "checkpoint_id": "cp-2"}},
            ),
            Snapshot(
                values={"estimation_id": "source", "estimate": {"total_hours": 32.0}},
                next=(),
                config={"configurable": {"thread_id": "estimate:source", "checkpoint_id": "cp-1"}},
            ),
        ]
        self.updates: list[tuple[dict[str, object], dict[str, object]]] = []

    async def aget_state(self, config):
        checkpoint_id = config["configurable"].get("checkpoint_id")
        return next(
            item
            for item in self.snapshots
            if item.config["configurable"]["checkpoint_id"] == checkpoint_id
        )

    async def aupdate_state(self, config, values, as_node=None):
        del as_node
        self.updates.append((config, values))
        return config

    async def _history(self, limit):
        for item in self.snapshots[:limit]:
            yield item

    def aget_state_history(self, config, *, limit=None):
        assert config == {"configurable": {"thread_id": "estimate:source"}}
        return self._history(limit or len(self.snapshots))


@pytest.mark.asyncio
async def test_checkpoint_history_is_newest_first_and_read_only() -> None:
    graph = FakeScenarioGraph()
    records = await list_checkpoint_records(graph, estimation_id="source")
    assert [item.checkpoint_id for item in records] == ["cp-2", "cp-1"]
    assert records[0].next_nodes == ("final_estimate_review",)
    assert graph.updates == []


@pytest.mark.asyncio
async def test_read_selected_checkpoint_uses_exact_checkpoint_identity() -> None:
    graph = FakeScenarioGraph()
    record = await read_checkpoint(
        graph, estimation_id="source", checkpoint_id="cp-1"
    )
    assert record.checkpoint_id == "cp-1"
    assert record.state["estimate"]["total_hours"] == 32.0


@pytest.mark.asyncio
async def test_branch_creates_new_thread_and_preserves_source() -> None:
    graph = FakeScenarioGraph()
    source_before = dict(graph.snapshots[0].values)
    branch = await branch_checkpoint(
        graph,
        estimation_id="source",
        checkpoint_id="cp-2",
        scenario_id="enterprise",
    )
    assert branch.estimation_id != "source"
    assert branch.thread_id == f"estimate:{branch.estimation_id}"
    assert branch.parent_estimation_id == "source"
    assert branch.parent_checkpoint_id == "cp-2"
    assert branch.state["scenario_id"] == "enterprise"
    assert graph.snapshots[0].values == source_before
    assert graph.updates[0][0] == {"configurable": {"thread_id": branch.thread_id}}


def test_scenario_comparison_reports_hours_evidence_findings_cost_and_latency() -> None:
    left = {
        "estimate": {"total_hours": 40.0},
        "budget_matches": [{}, {}],
        "critic_report": {"issues": [{}]},
        "execution_metadata": {"estimated_cost_usd": 0.2, "elapsed_ms": 100},
    }
    right = {
        "estimate": {"total_hours": 52.0},
        "budget_matches": [{}, {}, {}],
        "critic_report": {"issues": []},
        "execution_metadata": {"estimated_cost_usd": 0.3, "elapsed_ms": 80},
    }
    comparison = compare_scenario_states(left, right)
    assert comparison["total_hours"] == {"left": 40.0, "right": 52.0, "changed": True}
    assert comparison["evidence_count"]["right"] == 3
    assert comparison["critic_finding_count"]["left"] == 1
    assert comparison["estimated_cost_usd"]["changed"] is True
    assert comparison["elapsed_ms"]["right"] == 80
