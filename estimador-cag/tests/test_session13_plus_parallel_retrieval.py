from __future__ import annotations

import asyncio
from copy import deepcopy

import pytest

from app.generation.graph.fakes import FakeComponentClassifier, FakeRequirementExtractor
from app.generation.graph.nodes.parallel_retrieval import build_parallel_retrieval_nodes
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.review_state import merge_parallel_retrieval_results

COMPONENTS = [
    {"component_id": "CMP-1", "name": "One", "category": "backend", "requirement_ids": ["R-1"]},
    {"component_id": "CMP-2", "name": "Two", "category": "frontend", "requirement_ids": ["R-2"]},
    {"component_id": "CMP-3", "name": "Three", "category": "data", "requirement_ids": ["R-3"]},
]


def match(component_id: str, suffix: str) -> dict[str, object]:
    return {
        "component_id": component_id,
        "budget_id": f"BUD-{suffix}",
        "reference_component_id": f"REF-{suffix}",
        "source_document_id": f"DOC-{suffix}",
        "source_chunk_id": f"CH-{suffix}",
        "recorded_hours": 10.0,
        "distance": 0.1,
        "score": 0.9,
        "retrieval_method": "fake",
    }


class CoordinatedSearcher:
    def __init__(self) -> None:
        self.active = 0
        self.maximum = 0

    async def search_budgets(self, *, component, k: int):
        assert k == 5
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        await asyncio.sleep(
            {"CMP-1": 0.03, "CMP-2": 0.02, "CMP-3": 0.01}[component["component_id"]]
        )
        self.active -= 1
        return [match(component["component_id"], component["component_id"][-1])]


def dependencies(searcher) -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor([]),
        component_classifier=FakeComponentClassifier([]),
        budget_searcher=searcher,
    )


@pytest.mark.asyncio
async def test_send_fan_out_is_one_per_component_and_merge_is_canonical() -> None:
    searcher = CoordinatedSearcher()
    fan_out, worker, fan_in = build_parallel_retrieval_nodes(
        dependencies(searcher), max_concurrency=2
    )
    state = {"components": deepcopy(COMPONENTS), "estimation_id": "E-1", "graph_version": "plus"}
    sends = fan_out(state)
    assert [send.arg["component"]["component_id"] for send in sends] == ["CMP-1", "CMP-2", "CMP-3"]

    updates = await asyncio.gather(*(worker(send.arg) for send in reversed(sends)))
    results = [update["parallel_retrieval_results"][0] for update in updates]
    merged = await fan_in({**state, "parallel_retrieval_results": results})

    assert searcher.maximum == 2
    assert [item["component_id"] for item in merged["budget_matches"]] == [
        "CMP-1",
        "CMP-2",
        "CMP-3",
    ]
    assert merged["trace_events"][0]["event_type"] == "parallel_retrieval_merged"


def test_parallel_result_reducer_is_replay_idempotent() -> None:
    envelope = {"component_id": "CMP-1", "component_index": 0, "status": "success", "matches": []}
    assert merge_parallel_retrieval_results([envelope], [deepcopy(envelope)]) == [envelope]


@pytest.mark.asyncio
async def test_worker_failure_preserves_successful_sibling() -> None:
    class PartialFailureSearcher:
        async def search_budgets(self, *, component, k: int):
            del k
            if component["component_id"] == "CMP-2":
                raise RuntimeError("unavailable")
            return [match(component["component_id"], component["component_id"][-1])]

    fan_out, worker, fan_in = build_parallel_retrieval_nodes(
        dependencies(PartialFailureSearcher()), max_concurrency=2
    )
    state = {
        "components": deepcopy(COMPONENTS[:2]),
        "estimation_id": "E-2",
        "graph_version": "plus",
    }
    updates = await asyncio.gather(*(worker(send.arg) for send in fan_out(state)))
    merged = await fan_in(
        {
            **state,
            "parallel_retrieval_results": [u["parallel_retrieval_results"][0] for u in updates],
        }
    )

    assert [item["component_id"] for item in merged["budget_matches"]] == ["CMP-1"]
    assert merged["review_required"] is True
    assert merged["errors"][0]["code"] == "missing_budget_matches"
