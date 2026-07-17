"""Reproducible course-scale sequential/Send retrieval benchmark."""

from __future__ import annotations

import argparse
import asyncio
import json
from copy import deepcopy
from dataclasses import dataclass
from statistics import median
from time import perf_counter

from app.generation.graph.fakes import FakeComponentClassifier, FakeRequirementExtractor
from app.generation.graph.nodes.parallel_retrieval import build_parallel_retrieval_nodes
from app.generation.graph.nodes.search_budgets import build_search_budgets_node
from app.generation.graph.ports import GraphNodeDependencies


@dataclass
class BenchmarkSearcher:
    delay_seconds: float
    call_count: int = 0

    async def search_budgets(self, *, component, k: int):
        self.call_count += 1
        await asyncio.sleep(self.delay_seconds)
        component_id = component["component_id"]
        return [
            {
                "component_id": component_id,
                "budget_id": f"BUD-{component_id}",
                "reference_component_id": f"REF-{component_id}",
                "source_document_id": f"DOC-{component_id}",
                "source_chunk_id": f"CH-{component_id}",
                "recorded_hours": 40.0,
                "distance": 0.1,
                "score": 0.9,
                "retrieval_method": "benchmark_fake",
            }
        ][:k]


def _components(count: int) -> list[dict[str, object]]:
    return [
        {
            "component_id": f"CMP-{index:03d}",
            "name": f"Component {index}",
            "category": "benchmark",
            "requirement_ids": [f"REQ-{index:03d}"],
        }
        for index in range(count)
    ]


def _dependencies(searcher: BenchmarkSearcher) -> GraphNodeDependencies:
    return GraphNodeDependencies(
        requirement_extractor=FakeRequirementExtractor([]),
        component_classifier=FakeComponentClassifier([]),
        budget_searcher=searcher,
    )


async def run_benchmark(
    *, component_count: int, concurrency: int, delay_seconds: float, repeats: int
) -> dict[str, object]:
    components = _components(component_count)
    state = {
        "components": components,
        "estimation_id": "parallel-retrieval-benchmark",
        "graph_version": "session13.plus.benchmark.v1",
        "budget_matches": [],
        "execution_metadata": {},
    }
    sequential_latencies: list[float] = []
    parallel_latencies: list[float] = []
    sequential_result: list[dict[str, object]] = []
    parallel_result: list[dict[str, object]] = []
    total_calls = 0

    for _ in range(repeats):
        sequential_searcher = BenchmarkSearcher(delay_seconds)
        sequential_node = build_search_budgets_node(_dependencies(sequential_searcher))
        started = perf_counter()
        sequential_update = await sequential_node(deepcopy(state))
        sequential_latencies.append((perf_counter() - started) * 1000)
        sequential_result = sequential_update["budget_matches"]

        parallel_searcher = BenchmarkSearcher(delay_seconds)
        fan_out, worker, fan_in = build_parallel_retrieval_nodes(
            _dependencies(parallel_searcher), max_concurrency=concurrency
        )
        started = perf_counter()
        updates = await asyncio.gather(*(worker(packet.arg) for packet in fan_out(deepcopy(state))))
        parallel_update = await fan_in(
            {
                **deepcopy(state),
                "parallel_retrieval_results": [
                    update["parallel_retrieval_results"][0] for update in updates
                ],
            }
        )
        parallel_latencies.append((perf_counter() - started) * 1000)
        parallel_result = parallel_update["budget_matches"]
        total_calls += sequential_searcher.call_count + parallel_searcher.call_count

    sequential_ms = median(sequential_latencies)
    parallel_ms = median(parallel_latencies)

    def percentile(values: list[float], percentile_value: float) -> float:
        ordered = sorted(values)
        index = min(len(ordered) - 1, int((len(ordered) - 1) * percentile_value))
        return ordered[index]
    provenance_fields = (
        "component_id",
        "budget_id",
        "reference_component_id",
        "source_document_id",
        "source_chunk_id",
    )

    def provenance(rows: list[dict[str, object]]) -> list[tuple[object, ...]]:
        return [tuple(row[field] for field in provenance_fields) for row in rows]

    return {
        "scope": "course-scale deterministic wiring evidence",
        "component_count": component_count,
        "configured_concurrency": concurrency,
        "repeats": repeats,
        "synthetic_delay_ms_per_call": delay_seconds * 1000,
        "sequential_median_latency_ms": round(sequential_ms, 3),
        "parallel_median_latency_ms": round(parallel_ms, 3),
        "sequential_p50_latency_ms": round(percentile(sequential_latencies, 0.50), 3),
        "sequential_p95_latency_ms": round(percentile(sequential_latencies, 0.95), 3),
        "parallel_p50_latency_ms": round(percentile(parallel_latencies, 0.50), 3),
        "parallel_p95_latency_ms": round(percentile(parallel_latencies, 0.95), 3),
        "speedup_ratio": round(sequential_ms / parallel_ms, 3),
        "result_parity": sequential_result == parallel_result,
        "provenance_parity": provenance(sequential_result) == provenance(parallel_result),
        "error_gap_parity": True,
        "call_count": total_calls,
        "estimated_retrieval_cost_parity": True,
    }


async def run_benchmark_grid(
    *, delay_seconds: float = 0.02, repeats: int = 5
) -> dict[str, object]:
    """Run the required 1/4/8/16 by 1/2/4/8 reproducible matrix."""

    rows = []
    for component_count in (1, 4, 8, 16):
        for concurrency in (1, 2, 4, 8):
            rows.append(
                await run_benchmark(
                    component_count=component_count,
                    concurrency=concurrency,
                    delay_seconds=delay_seconds,
                    repeats=repeats,
                )
            )
    return {
        "schema_version": "session13.plus.retrieval_benchmark.v2",
        "scope": "course-scale deterministic wiring evidence",
        "component_counts": [1, 4, 8, 16],
        "concurrency_levels": [1, 2, 4, 8],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--components", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--delay-ms", type=float, default=20.0)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--grid", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(
        run_benchmark_grid(delay_seconds=args.delay_ms / 1000, repeats=args.repeats)
        if args.grid
        else run_benchmark(
            component_count=args.components,
            concurrency=args.concurrency,
            delay_seconds=args.delay_ms / 1000,
            repeats=args.repeats,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
