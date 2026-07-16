from __future__ import annotations

from typing import Generic, TypeVar

import pytest

from app.services.estimation_dispatcher import dispatch_estimation

ResultT = TypeVar("ResultT")


class RecordingOperation(Generic[ResultT]):
    """Async fake recording whether one backend operation was invoked."""

    def __init__(self, result: ResultT) -> None:
        self.result = result
        self.calls = 0

    async def __call__(self) -> ResultT:
        self.calls += 1
        return self.result


@pytest.mark.asyncio
async def test_dispatch_estimation_selects_only_legacy_operation() -> None:
    legacy_result = object()
    graph_result = object()
    legacy = RecordingOperation(legacy_result)
    graph = RecordingOperation(graph_result)

    result = await dispatch_estimation(
        backend="legacy",
        legacy_operation=legacy,
        graph_operation=graph,
    )

    assert result is legacy_result
    assert legacy.calls == 1
    assert graph.calls == 0


@pytest.mark.asyncio
async def test_dispatch_estimation_selects_only_graph_operation() -> None:
    legacy_result = object()
    graph_result = object()
    legacy = RecordingOperation(legacy_result)
    graph = RecordingOperation(graph_result)

    result = await dispatch_estimation(
        backend="graph",
        legacy_operation=legacy,
        graph_operation=graph,
    )

    assert result is graph_result
    assert legacy.calls == 0
    assert graph.calls == 1
