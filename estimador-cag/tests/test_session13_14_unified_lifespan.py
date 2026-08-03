from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient


def test_unified_runtime_failure_does_not_disable_existing_runtimes(monkeypatch) -> None:
    import app.main as main_module

    supervised_service = object()
    reviewed_service = object()

    @asynccontextmanager
    async def supervised_runtime():
        yield supervised_service

    @asynccontextmanager
    async def reviewed_runtime():
        yield reviewed_service

    @asynccontextmanager
    async def broken_unified_runtime():
        raise RuntimeError("sensitive backend detail must not reach readiness")
        yield  # pragma: no cover

    monkeypatch.setattr(
        main_module,
        "open_graph_estimation_service",
        supervised_runtime,
    )
    monkeypatch.setattr(
        main_module,
        "open_reviewed_graph_estimation_service",
        reviewed_runtime,
    )
    monkeypatch.setattr(
        main_module,
        "open_unified_graph_estimation_service",
        broken_unified_runtime,
    )
    monkeypatch.setattr(
        main_module,
        "flush_logfire_graph_traces",
        lambda: True,
    )

    with TestClient(main_module.app) as client:
        assert main_module.app.state.graph_estimation_service is (
            supervised_service
        )
        assert main_module.app.state.reviewed_graph_estimation_service is (
            reviewed_service
        )
        assert main_module.app.state.unified_graph_estimation_service is None
        response = client.get(
            "/api/v1/estimate/graph/unified/readiness"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert payload["runtime_error"] == "RuntimeError"
    assert "sensitive backend detail" not in response.text
