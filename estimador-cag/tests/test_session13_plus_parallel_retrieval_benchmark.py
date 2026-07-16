from __future__ import annotations

import pytest

from evals.session13_plus_parallel_retrieval_benchmark import run_benchmark


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
    assert result["call_count"] == 16
    assert result["speedup_ratio"] > 1
