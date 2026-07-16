from __future__ import annotations

from typing import Any

import pytest

from app.schemas.estimation import EstimationRequest
from app.services.graph_estimation import GraphEstimationRun
from app.services.session_estimation_bridge import (
    GraphBackendExecutionError,
    GraphBackendUnavailableError,
    build_graph_transcript,
    execute_session_estimation,
)


def _request() -> EstimationRequest:
    return EstimationRequest(
        description="Build a FastAPI service with PostgreSQL and authentication.",
        project_type="web_saas",
        detail_level="medium",
        output_format="phases_table",
        tier="flash",
    )


def _graph_run() -> GraphEstimationRun:
    component_estimate = {
        "component_id": "component-1",
        "name": "Backend API",
        "hours": 40.0,
        "grounding_status": "grounded",
        "reference_budget_ids": ["budget-1"],
        "reference_component_ids": ["reference-1"],
        "source_hours": [40.0],
        "source_range_low": 40.0,
        "source_range_high": 40.0,
        "dispersion": 0.0,
        "confidence": 0.9,
        "derivation_method": "single_reference",
        "review_reasons": [],
    }
    return GraphEstimationRun(
        estimation_id="12345678-1234-5678-1234-567812345678",
        thread_id="estimate:12345678-1234-5678-1234-567812345678",
        state={
            "graph_version": "session13.v1",
            "status": "validated",
            "review_required": False,
            "requirements": [],
            "components": [],
            "budget_matches": [],
            "component_estimates": [component_estimate],
            "estimate": {
                "components": [component_estimate],
                "subtotal_hours": 40.0,
                "contingency_hours": 4.0,
                "total_hours": 44.0,
                "total_cost_eur": 4400.0,
                "currency": "EUR",
            },
            "errors": [],
            "trace_events": [],
            "provider_metadata": {},
            "execution_metadata": {"graph_version": "session13.v1"},
        },
    )


class RecordingGraphService:
    def __init__(self, run: GraphEstimationRun | None = None) -> None:
        self.run = run or _graph_run()
        self.transcripts: list[str] = []

    async def estimate(self, *, transcript: str, estimation_id=None) -> GraphEstimationRun:
        self.transcripts.append(transcript)
        return self.run


class FailingGraphService:
    async def estimate(self, *, transcript: str, estimation_id=None) -> GraphEstimationRun:
        raise ValueError("broken graph")


@pytest.mark.asyncio
async def test_legacy_mode_preserves_existing_call_shape() -> None:
    calls: list[dict[str, Any]] = []
    expected = {"text": "legacy result"}

    def legacy_estimator(request: EstimationRequest, **kwargs: Any) -> dict[str, Any]:
        calls.append({"request": request, **kwargs})
        return expected

    result = await execute_session_estimation(
        backend="legacy",
        legacy_estimator=legacy_estimator,
        graph_service=None,
        request=_request(),
        transcript="Current transcript for the project.",
        tier="flash",
        prompt_version="v2",
        project_metadata={"project_name": "Atlas"},
        attachments_text="attachment context",
        conversation_history=[{"role": "assistant", "content": "previous"}],
    )

    assert result is expected
    assert len(calls) == 1
    assert calls[0]["tier"] == "flash"
    assert calls[0]["prompt_version"] == "v2"
    assert calls[0]["project_metadata"] == {"project_name": "Atlas"}
    assert calls[0]["attachments_text"] == "attachment context"
    assert calls[0]["conversation_history"] == [
        {"role": "assistant", "content": "previous"}
    ]


@pytest.mark.asyncio
async def test_graph_mode_uses_enriched_transcript_and_skips_legacy() -> None:
    graph_service = RecordingGraphService()
    legacy_calls = 0

    def legacy_estimator(request: EstimationRequest, **kwargs: Any) -> dict[str, Any]:
        nonlocal legacy_calls
        legacy_calls += 1
        return {"text": "unexpected"}

    result = await execute_session_estimation(
        backend="graph",
        legacy_estimator=legacy_estimator,
        graph_service=graph_service,
        request=_request(),
        transcript="Current transcript for the project.",
        tier="flash",
        prompt_version="v2",
        project_metadata={"project_name": "Atlas"},
        attachments_text="PDF requirements",
        conversation_history=[{"role": "assistant", "content": "previous"}],
    )

    assert legacy_calls == 0
    assert graph_service.transcripts == [
        "Current transcript for the project.\n\n"
        "Attachment context:\nPDF requirements"
    ]
    assert result["estimation_backend"] == "graph"
    assert result["graph_estimation"]["estimate"]["total_hours"] == 44.0
    assert result["result"] is None


@pytest.mark.asyncio
async def test_graph_mode_fails_explicitly_when_service_is_unavailable() -> None:
    with pytest.raises(
        GraphBackendUnavailableError,
        match="Estimation graph service is not available",
    ):
        await execute_session_estimation(
            backend="graph",
            legacy_estimator=lambda request, **kwargs: {},
            graph_service=None,
            request=_request(),
            transcript="Current transcript for the project.",
            tier=None,
            prompt_version="v1",
            project_metadata={},
            attachments_text="",
            conversation_history=[],
        )


@pytest.mark.asyncio
async def test_graph_mode_normalizes_runtime_failure() -> None:
    with pytest.raises(
        GraphBackendExecutionError,
        match="Graph estimation execution failed",
    ) as exc_info:
        await execute_session_estimation(
            backend="graph",
            legacy_estimator=lambda request, **kwargs: {},
            graph_service=FailingGraphService(),
            request=_request(),
            transcript="Current transcript for the project.",
            tier=None,
            prompt_version="v1",
            project_metadata={},
            attachments_text="",
            conversation_history=[],
        )

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_graph_transcript_does_not_add_empty_attachment_section() -> None:
    assert build_graph_transcript(
        transcript="Current transcript for the project.",
        attachments_text="   ",
    ) == "Current transcript for the project."
