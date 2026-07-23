from __future__ import annotations

from uuid import UUID

import pytest

from app.schemas.estimation import EstimationRequest
from app.services.graph_estimation import GraphEstimationRun
from app.services.graph_rollout import (
    InMemoryGraphShadowStore,
    prepare_session_estimation_rollout,
)
from app.services.session_estimation_bridge import GraphBackendUnavailableError


class RecordingGraphService:
    def __init__(self) -> None:
        self.calls = 0
        self.transcripts: list[str] = []

    async def estimate(self, *, transcript: str, estimation_id: UUID | None = None):
        self.calls += 1
        self.transcripts.append(transcript)
        return GraphEstimationRun(
            estimation_id="11111111-1111-4111-8111-111111111111",
            thread_id="estimate:11111111-1111-4111-8111-111111111111",
            state={
                "graph_version": "session13.v1",
                "status": "validated",
                "review_required": False,
                "estimate": {
                    "components": [],
                    "subtotal_hours": 40.0,
                    "contingency_hours": 4.0,
                    "total_hours": 44.0,
                    "total_cost_eur": 5500.0,
                    "currency": "EUR",
                },
                "requirements": [],
                "components": [],
                "budget_matches": [],
                "component_estimates": [],
                "errors": [],
                "trace_events": [],
                "provider_metadata": {
                    "provider": "deepseek",
                    "model": "deepseek-v4-flash",
                    "prompt_version": "session13.v1",
                },
                "execution_metadata": {},
            },
        )


def _request() -> EstimationRequest:
    return EstimationRequest(
        description="Build a secure FastAPI onboarding platform with PostgreSQL.",
        project_type="web_saas",
        detail_level="medium",
        output_format="phases_table",
        tier="flash",
    )


def _legacy_estimator(request, **kwargs):
    return {
        "prompt_version": kwargs.get("prompt_version", "v1"),
        "result": {
            "summary": "Legacy structured estimate.",
            "total_cost_eur": 5000,
        },
        "text": "Legacy estimate text",
        "requested_tier": kwargs.get("tier"),
        "served_tier": kwargs.get("tier"),
    }


def _prepare(**overrides):
    values = {
        "rollout_mode": "off",
        "configured_backend": "legacy",
        "legacy_estimator": _legacy_estimator,
        "graph_service": RecordingGraphService(),
        "request": _request(),
        "transcript": "Build a secure FastAPI onboarding platform with PostgreSQL.",
        "tier": "flash",
        "prompt_version": "v2",
        "project_metadata": {"project_name": "Atlas"},
        "attachments_text": "",
        "conversation_history": [],
        "session_id": "session-123",
    }
    values.update(overrides)
    return prepare_session_estimation_rollout(**values)


@pytest.mark.asyncio
async def test_off_mode_preserves_configured_legacy_backend() -> None:
    prepared = await _prepare()

    assert prepared.result["estimation_backend"] == "legacy"
    assert prepared.result["graph_rollout_mode"] == "off"
    assert prepared.shadow_operation is None


@pytest.mark.asyncio
async def test_serve_mode_forces_graph_backend() -> None:
    graph_service = RecordingGraphService()

    prepared = await _prepare(
        rollout_mode="serve",
        configured_backend="legacy",
        graph_service=graph_service,
    )

    assert prepared.result["estimation_backend"] == "graph"
    assert prepared.result["graph_rollout_mode"] == "serve"
    assert graph_service.calls == 1
    assert prepared.shadow_operation is None


@pytest.mark.asyncio
async def test_shadow_mode_serves_legacy_before_graph_operation_runs() -> None:
    graph_service = RecordingGraphService()
    store = InMemoryGraphShadowStore()

    prepared = await _prepare(
        rollout_mode="shadow",
        configured_backend="graph",
        graph_service=graph_service,
        shadow_store=store,
    )

    assert prepared.result["estimation_backend"] == "legacy"
    assert prepared.result["graph_rollout_mode"] == "shadow"
    assert prepared.result["text"] == "Legacy estimate text"
    assert prepared.result["shadow_comparison_id"]
    assert graph_service.calls == 0
    assert store.list() == []

    assert prepared.shadow_operation is not None
    await prepared.shadow_operation()

    assert graph_service.calls == 1
    records = store.list()
    assert len(records) == 1
    record = records[0]
    assert record.status == "completed"
    assert record.served_backend == "legacy"
    assert record.shadow_backend == "graph"
    assert record.primary_total_cost_eur == 5000.0
    assert record.shadow_total_cost_eur == 5500.0
    assert record.cost_delta_eur == 500.0
    assert record.shadow_graph_status == "validated"
    assert record.shadow_review_required is False
    transcript = "Build a secure FastAPI onboarding platform with PostgreSQL."
    assert record.request_fingerprint != transcript
    assert transcript not in record.model_dump_json()


@pytest.mark.asyncio
async def test_shadow_failure_is_recorded_without_affecting_served_result() -> None:
    store = InMemoryGraphShadowStore()

    prepared = await _prepare(
        rollout_mode="shadow",
        graph_service=None,
        shadow_store=store,
    )

    assert prepared.result["text"] == "Legacy estimate text"
    assert prepared.shadow_operation is not None
    await prepared.shadow_operation()

    records = store.list()
    assert len(records) == 1
    assert records[0].status == "failed"
    assert records[0].error_type == "GraphBackendUnavailableError"


@pytest.mark.asyncio
async def test_serve_mode_fails_closed_when_graph_runtime_is_unavailable() -> None:
    with pytest.raises(GraphBackendUnavailableError):
        await _prepare(
            rollout_mode="serve",
            graph_service=None,
        )


def test_shadow_store_validates_bounds() -> None:
    with pytest.raises(ValueError, match="max_records must be positive"):
        InMemoryGraphShadowStore(max_records=0)

    store = InMemoryGraphShadowStore(max_records=1)
    assert store.list() == []
    with pytest.raises(ValueError, match="limit must be positive"):
        store.list(limit=0)
