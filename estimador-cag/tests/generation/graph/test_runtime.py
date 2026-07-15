from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest
from fastapi import FastAPI

import app.generation.graph.runtime as runtime_module
import app.main as main_module
from app.generation.graph.runtime import (
    open_graph_estimation_service,
    open_postgres_checkpointer,
    postgres_saver_conninfo,
)
from app.services.graph_estimation import GraphEstimationService


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        (
            (
                "postgresql+asyncpg://user:password@"
                "localhost:5432/estimator"
            ),
            (
                "postgresql://user:password@"
                "localhost:5432/estimator"
            ),
        ),
        (
            (
                "postgresql+psycopg://user:password@"
                "postgres:5432/estimator"
            ),
            (
                "postgresql://user:password@"
                "postgres:5432/estimator"
            ),
        ),
        (
            (
                "postgresql+psycopg_async://user:password@"
                "postgres:5432/estimator?sslmode=require"
            ),
            (
                "postgresql://user:password@"
                "postgres:5432/estimator?sslmode=require"
            ),
        ),
        (
            "postgres://user:password@postgres/estimator",
            "postgresql://user:password@postgres/estimator",
        ),
        (
            "postgresql://user:password@postgres/estimator",
            "postgresql://user:password@postgres/estimator",
        ),
    ],
)
def test_postgres_saver_conninfo_normalizes_supported_urls(
    database_url: str,
    expected: str,
) -> None:
    assert postgres_saver_conninfo(database_url) == expected


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "sqlite+aiosqlite:///tmp/test.db",
        "mysql://user:password@localhost/test",
    ],
)
def test_postgres_saver_conninfo_rejects_invalid_urls(
    database_url: str,
) -> None:
    with pytest.raises(ValueError):
        postgres_saver_conninfo(database_url)


@dataclass
class FakeSaver:
    setup_calls: int = 0

    async def setup(self) -> None:
        self.setup_calls += 1


class FakeSaverFactory:
    conninfos: list[str] = []
    savers: list[FakeSaver] = []
    events: list[str] = []

    @classmethod
    def from_conn_string(cls, conninfo: str):
        cls.conninfos.append(conninfo)

        @asynccontextmanager
        async def context():
            saver = FakeSaver()
            cls.savers.append(saver)
            cls.events.append("enter")
            try:
                yield saver
            finally:
                cls.events.append("exit")

        return context()


@pytest.mark.asyncio
async def test_postgres_checkpointer_sets_up_once_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeSaverFactory.conninfos.clear()
    FakeSaverFactory.savers.clear()
    FakeSaverFactory.events.clear()

    monkeypatch.setattr(
        runtime_module,
        "AsyncPostgresSaver",
        FakeSaverFactory,
    )

    database_url = (
        "postgresql+asyncpg://user:password@"
        "localhost:5432/estimator"
    )

    async with open_postgres_checkpointer(
        database_url
    ) as saver:
        assert saver.setup_calls == 1
        assert FakeSaverFactory.events == ["enter"]

    assert FakeSaverFactory.conninfos == [
        (
            "postgresql://user:password@"
            "localhost:5432/estimator"
        )
    ]
    assert FakeSaverFactory.savers[0].setup_calls == 1
    assert FakeSaverFactory.events == ["enter", "exit"]


@pytest.mark.asyncio
async def test_graph_runtime_wires_checkpointer_and_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkpointer = object()
    dependencies = object()
    graph = object()
    events: list[object] = []

    @asynccontextmanager
    async def fake_open_checkpointer(
        database_url: str | None = None,
    ):
        events.append(("checkpointer_enter", database_url))
        try:
            yield checkpointer
        finally:
            events.append(("checkpointer_exit", database_url))

    def fake_build_dependencies():
        events.append("dependencies")
        return dependencies

    def fake_build_graph(
        received_dependencies: object,
        *,
        checkpointer: object,
    ):
        events.append(
            (
                "graph",
                received_dependencies,
                checkpointer,
            )
        )
        return graph

    monkeypatch.setattr(
        runtime_module,
        "open_postgres_checkpointer",
        fake_open_checkpointer,
    )
    monkeypatch.setattr(
        runtime_module,
        "build_graph_node_dependencies",
        fake_build_dependencies,
    )
    monkeypatch.setattr(
        runtime_module,
        "build_estimation_graph",
        fake_build_graph,
    )

    database_url = (
        "postgresql+asyncpg://user:password@"
        "localhost:5432/estimator"
    )

    async with open_graph_estimation_service(
        database_url
    ) as service:
        assert isinstance(service, GraphEstimationService)
        assert service.graph is graph
        assert events == [
            ("checkpointer_enter", database_url),
            "dependencies",
            ("graph", dependencies, checkpointer),
        ]

    assert events[-1] == (
        "checkpointer_exit",
        database_url,
    )


@pytest.mark.asyncio
async def test_lifespan_publishes_and_removes_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    events: list[str] = []

    @asynccontextmanager
    async def fake_runtime():
        events.append("enter")
        try:
            yield service
        finally:
            events.append("exit")

    monkeypatch.setattr(
        main_module,
        "open_graph_estimation_service",
        fake_runtime,
    )

    app = FastAPI()

    async with main_module.lifespan(app):
        assert app.state.graph_estimation_service is service
        assert events == ["enter"]

    assert app.state.graph_estimation_service is None
    assert events == ["enter", "exit"]


@pytest.mark.asyncio
async def test_lifespan_keeps_app_available_when_graph_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    @asynccontextmanager
    async def failing_runtime():
        events.append("enter")
        raise RuntimeError("postgres unavailable")
        yield object()

    monkeypatch.setattr(
        main_module,
        "open_graph_estimation_service",
        failing_runtime,
    )

    app = FastAPI()

    async with main_module.lifespan(app):
        assert app.state.graph_estimation_service is None

    assert app.state.graph_estimation_service is None
    assert events == ["enter"]
