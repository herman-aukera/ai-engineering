"""Select one configured estimation backend without owning its execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.config import EstimationBackend

ResultT = TypeVar("ResultT")
AsyncEstimationOperation = Callable[[], Awaitable[ResultT]]


async def dispatch_estimation(
    *,
    backend: EstimationBackend,
    legacy_operation: AsyncEstimationOperation[ResultT],
    graph_operation: AsyncEstimationOperation[ResultT],
) -> ResultT:
    """Execute only the operation selected by validated configuration."""

    selected_operation = (
        legacy_operation
        if backend == "legacy"
        else graph_operation
    )
    return await selected_operation()
