"""Session 14 Logfire lifecycle regression tests."""

from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI

import app.main as main_module


@pytest.mark.asyncio
async def test_lifespan_flushes_logfire_after_graph_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    @asynccontextmanager
    async def open_graph_service():
        events.append("session14_open")
        try:
            yield object()
        finally:
            events.append("session14_close")

    @asynccontextmanager
    async def open_reviewed_service():
        events.append("reviewed_open")
        try:
            yield object()
        finally:
            events.append("reviewed_close")

    def flush_graph_traces() -> bool:
        events.append("logfire_flush")
        return True

    monkeypatch.setattr(
        main_module,
        "open_graph_estimation_service",
        open_graph_service,
    )
    monkeypatch.setattr(
        main_module,
        "open_reviewed_graph_estimation_service",
        open_reviewed_service,
    )
    monkeypatch.setattr(
        main_module,
        "flush_logfire_graph_traces",
        flush_graph_traces,
    )

    test_app = FastAPI()
    async with main_module.lifespan(test_app):
        assert test_app.state.graph_estimation_service is not None
        assert test_app.state.reviewed_graph_estimation_service is not None

    assert events == [
        "session14_open",
        "reviewed_open",
        "reviewed_close",
        "session14_close",
        "logfire_flush",
    ]


@pytest.mark.asyncio
async def test_lifespan_does_not_mask_shutdown_when_logfire_flush_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @asynccontextmanager
    async def open_service():
        yield object()

    def failed_flush() -> bool:
        raise RuntimeError("export unavailable")

    monkeypatch.setattr(
        main_module,
        "open_graph_estimation_service",
        open_service,
    )
    monkeypatch.setattr(
        main_module,
        "open_reviewed_graph_estimation_service",
        open_service,
    )
    monkeypatch.setattr(
        main_module,
        "flush_logfire_graph_traces",
        failed_flush,
    )

    async with main_module.lifespan(FastAPI()):
        pass
