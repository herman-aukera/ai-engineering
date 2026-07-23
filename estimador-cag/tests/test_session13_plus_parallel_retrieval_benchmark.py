from __future__ import annotations

import pytest

from evals.session13_plus_parallel_retrieval_benchmark import (
    run_benchmark,
    run_benchmark_grid,
)


@pytest.mark.asyncio
async def test_parallel_benchmark_reports_required_parity_and_metrics() -> None:
    result = await run_benchmark(
        component_count=4,
        concurrency=2,
        delay_seconds=0.005,
        repeats=2,
    )

    assert result["component_count"] == 4
    assert result["configured_concurrency"] == 2
    assert result["result_parity"] is True
    assert result["provenance_parity"] is True
    assert result["error_gap_parity"] is True
    assert result["estimated_retrieval_cost_parity"] is True
    assert result["parallel_p95_latency_ms"] >= result["parallel_p50_latency_ms"]
    assert result["call_count"] == 16
    assert result["speedup_ratio"] > 1


@pytest.mark.asyncio
async def test_required_benchmark_grid_has_all_sixteen_cells() -> None:
    result = await run_benchmark_grid(delay_seconds=0.0001, repeats=2)
    rows = result["rows"]
    assert len(rows) == 16
    assert {(row["component_count"], row["configured_concurrency"]) for row in rows} == {
        (components, concurrency)
        for components in (1, 4, 8, 16)
        for concurrency in (1, 2, 4, 8)
    }
    assert all(row["result_parity"] for row in rows)
