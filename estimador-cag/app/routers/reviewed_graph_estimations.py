"""Additive API for durable Session 13 Plus human-review executions."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.generation.graph.nodes.final_estimate_review import (
    StaleFinalEstimateReviewError,
)
from app.generation.graph.nodes.structure_review import StaleStructureReviewError
from app.schemas.reviewed_graph_estimation import (
    ReviewedAuditPacketResponse,
    ReviewedCheckpointHistoryResponse,
    ReviewedCheckpointResponse,
    ReviewedGraphExecutionResponse,
    ReviewedGraphFinalResumeRequest,
    ReviewedGraphResumeRequest,
    ReviewedGraphStartRequest,
    ReviewedScenarioBranchRequest,
    ReviewedScenarioComparisonRequest,
    ReviewedScenarioComparisonResponse,
)
from app.services.audit_export import build_estimation_audit_packet
from app.services.reviewed_graph_estimation import (
    ReviewedGraphEstimationApplication,
    ReviewedGraphNotFoundError,
    ReviewedGraphRun,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["reviewed-estimations"])


def get_reviewed_graph_estimation_service(
    request: Request,
) -> ReviewedGraphEstimationApplication:
    service = getattr(
        request.app.state,
        "reviewed_graph_estimation_service",
        None,
    )
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Reviewed estimation graph service is not available.",
        )
    return cast(ReviewedGraphEstimationApplication, service)


def reviewed_graph_response_from_run(
    run: ReviewedGraphRun,
) -> ReviewedGraphExecutionResponse:
    state = run.state
    return ReviewedGraphExecutionResponse.model_validate(
        {
            "execution_status": run.execution_status,
            "estimation_id": run.estimation_id,
            "thread_id": run.thread_id,
            "graph_version": state.get("graph_version"),
            "graph_status": state.get("status", "pending"),
            "review_required": bool(state.get("review_required", False)),
            "human_review_mode": state.get("human_review_mode", "risk_based"),
            "structure_review_revision": state.get("structure_review_revision", 0),
            "structure_review_status": state.get("structure_review_status"),
            "final_review_revision": state.get("final_review_revision", 0),
            "final_review_status": state.get("final_review_status"),
            "next_nodes": list(run.next_nodes),
            "interrupts": list(run.interrupts),
            "state": dict(state),
        }
    )


@router.post(
    "/estimate/graph/reviewed/start",
    response_model=ReviewedGraphExecutionResponse,
)
async def start_reviewed_graph_estimation(
    payload: ReviewedGraphStartRequest,
    service: ReviewedGraphEstimationApplication = Depends(
        get_reviewed_graph_estimation_service
    ),
) -> ReviewedGraphExecutionResponse:
    try:
        run = await service.start(
            transcript=payload.transcript,
            human_review_mode=payload.human_review_mode,
            estimation_id=payload.estimation_id,
            provider=payload.provider,
            reasoning=payload.reasoning,
            context_detail=payload.context_detail,
        )
        return reviewed_graph_response_from_run(run)
    except ValidationError as exc:
        logger.exception("reviewed_graph_response_invalid")
        raise HTTPException(
            status_code=502,
            detail="Reviewed graph produced an invalid response.",
        ) from exc
    except Exception as exc:
        logger.exception("reviewed_graph_start_failed")
        raise HTTPException(
            status_code=502,
            detail="Failed to start reviewed graph estimation.",
        ) from exc


@router.post(
    "/estimate/graph/reviewed/{estimation_id}/resume",
    response_model=ReviewedGraphExecutionResponse,
)
async def resume_reviewed_graph_estimation(
    estimation_id: UUID,
    payload: ReviewedGraphResumeRequest,
    service: ReviewedGraphEstimationApplication = Depends(
        get_reviewed_graph_estimation_service
    ),
) -> ReviewedGraphExecutionResponse:
    try:
        run = await service.resume_structure_review(
            estimation_id=estimation_id,
            decision=payload,
        )
        return reviewed_graph_response_from_run(run)
    except ReviewedGraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StaleStructureReviewError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        logger.exception("reviewed_graph_resume_response_invalid")
        raise HTTPException(
            status_code=502,
            detail="Reviewed graph produced an invalid response.",
        ) from exc
    except Exception as exc:
        logger.exception("reviewed_graph_resume_failed")
        raise HTTPException(
            status_code=502,
            detail="Failed to resume reviewed graph estimation.",
        ) from exc


@router.post(
    "/estimate/graph/reviewed/{estimation_id}/resume/final",
    response_model=ReviewedGraphExecutionResponse,
)
async def resume_final_reviewed_graph_estimation(
    estimation_id: UUID,
    payload: ReviewedGraphFinalResumeRequest,
    service: ReviewedGraphEstimationApplication = Depends(
        get_reviewed_graph_estimation_service
    ),
) -> ReviewedGraphExecutionResponse:
    try:
        run = await service.resume_final_review(
            estimation_id=estimation_id,
            decision=payload,
        )
        return reviewed_graph_response_from_run(run)
    except ReviewedGraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StaleFinalEstimateReviewError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        logger.exception("reviewed_graph_final_resume_response_invalid")
        raise HTTPException(
            status_code=502,
            detail="Reviewed graph produced an invalid response.",
        ) from exc
    except Exception as exc:
        logger.exception("reviewed_graph_final_resume_failed")
        raise HTTPException(
            status_code=502,
            detail="Failed to resume final estimate review.",
        ) from exc


@router.get(
    "/estimate/graph/reviewed/{estimation_id}/checkpoints",
    response_model=ReviewedCheckpointHistoryResponse,
)
async def list_reviewed_checkpoints(
    estimation_id: UUID,
    limit: int = 50,
    service: ReviewedGraphEstimationApplication = Depends(
        get_reviewed_graph_estimation_service
    ),
) -> ReviewedCheckpointHistoryResponse:
    try:
        records = await service.checkpoint_history(
            estimation_id=estimation_id, limit=limit
        )
        return ReviewedCheckpointHistoryResponse(
            estimation_id=estimation_id,
            checkpoints=[
                ReviewedCheckpointResponse(
                    checkpoint_id=item.checkpoint_id,
                    created_at=item.created_at,
                    next_nodes=list(item.next_nodes),
                    state=dict(item.state),
                )
                for item in records
            ],
        )
    except (LookupError, ReviewedGraphNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/estimate/graph/reviewed/{estimation_id}/checkpoints/{checkpoint_id}",
    response_model=ReviewedCheckpointResponse,
)
async def inspect_reviewed_checkpoint(
    estimation_id: UUID,
    checkpoint_id: str,
    service: ReviewedGraphEstimationApplication = Depends(
        get_reviewed_graph_estimation_service
    ),
) -> ReviewedCheckpointResponse:
    try:
        item = await service.inspect_checkpoint(
            estimation_id=estimation_id, checkpoint_id=checkpoint_id
        )
        return ReviewedCheckpointResponse(
            checkpoint_id=item.checkpoint_id,
            created_at=item.created_at,
            next_nodes=list(item.next_nodes),
            state=dict(item.state),
        )
    except (LookupError, ReviewedGraphNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/estimate/graph/reviewed/{estimation_id}/scenarios",
    response_model=ReviewedGraphExecutionResponse,
)
async def branch_reviewed_scenario(
    estimation_id: UUID,
    payload: ReviewedScenarioBranchRequest,
    service: ReviewedGraphEstimationApplication = Depends(
        get_reviewed_graph_estimation_service
    ),
) -> ReviewedGraphExecutionResponse:
    try:
        run = await service.branch_scenario(
            estimation_id=estimation_id,
            checkpoint_id=payload.checkpoint_id,
            scenario_id=payload.scenario_id,
        )
        return reviewed_graph_response_from_run(run)
    except (LookupError, ReviewedGraphNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/estimate/graph/reviewed/scenarios/compare",
    response_model=ReviewedScenarioComparisonResponse,
)
async def compare_reviewed_scenarios(
    payload: ReviewedScenarioComparisonRequest,
    service: ReviewedGraphEstimationApplication = Depends(
        get_reviewed_graph_estimation_service
    ),
) -> ReviewedScenarioComparisonResponse:
    comparison = await service.compare_scenarios(
        left_estimation_id=payload.left_estimation_id,
        right_estimation_id=payload.right_estimation_id,
    )
    return ReviewedScenarioComparisonResponse(
        left_estimation_id=payload.left_estimation_id,
        right_estimation_id=payload.right_estimation_id,
        comparison=comparison,
    )


@router.get(
    "/estimate/graph/reviewed/{estimation_id}/audit",
    response_model=ReviewedAuditPacketResponse,
)
async def export_reviewed_audit_packet(
    estimation_id: UUID,
    service: ReviewedGraphEstimationApplication = Depends(
        get_reviewed_graph_estimation_service
    ),
) -> ReviewedAuditPacketResponse:
    try:
        run = await service.inspect(estimation_id=estimation_id)
        history = await service.checkpoint_history(estimation_id=estimation_id, limit=1)
        packet = build_estimation_audit_packet(
            run.state,
            thread_id=run.thread_id,
            checkpoint_id=history[0].checkpoint_id,
            limitations=[
                "Live provider, browser, telemetry, and PostgreSQL restart evidence are separate promotion artifacts."
            ],
        )
        return ReviewedAuditPacketResponse(packet=packet)
    except (LookupError, ReviewedGraphNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/estimate/graph/reviewed/{estimation_id}",
    response_model=ReviewedGraphExecutionResponse,
)
async def inspect_reviewed_graph_estimation(
    estimation_id: UUID,
    service: ReviewedGraphEstimationApplication = Depends(
        get_reviewed_graph_estimation_service
    ),
) -> ReviewedGraphExecutionResponse:
    try:
        run = await service.inspect(estimation_id=estimation_id)
        return reviewed_graph_response_from_run(run)
    except ReviewedGraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        logger.exception("reviewed_graph_inspection_response_invalid")
        raise HTTPException(
            status_code=502,
            detail="Reviewed graph checkpoint is invalid.",
        ) from exc
    except Exception as exc:
        logger.exception("reviewed_graph_inspection_failed")
        raise HTTPException(
            status_code=502,
            detail="Failed to inspect reviewed graph estimation.",
        ) from exc


@router.post("/estimate/graph/reviewed/stream")
async def stream_reviewed_graph_estimation(
    payload: ReviewedGraphStartRequest,
    request: Request,
) -> EventSourceResponse:
    """Stream a reviewed graph execution as SSE events.

    Each event carries the node name and state delta as JSON.
    The final event is ``done`` with the complete state.
    """
    service: ReviewedGraphEstimationApplication = getattr(
        request.app.state, "reviewed_graph_estimation_service", None
    )
    if service is None:
        raise HTTPException(status_code=503, detail="Reviewed graph service unavailable.")

    from uuid import uuid4

    thread_id = f"estimate:{payload.estimation_id or uuid4()}"
    config: dict[str, object] = {"configurable": {"thread_id": thread_id}}

    from app.generation.graph.review_state import ReviewedEstimationGraphState
    from app.generation.graph.state import new_estimation_graph_state
    from app.schemas.review_policy import ExecutionBudgetSnapshot

    initial_state = ReviewedEstimationGraphState(
        **new_estimation_graph_state(
            transcript=payload.transcript,
            estimation_id=str(payload.estimation_id or uuid4()),
            graph_version="session13.plus.v1",
        )
    )
    initial_state.update(
        {
            "human_review_mode": payload.human_review_mode,
            "structure_review_revision": 0,
            "final_review_revision": 0,
            "execution_budgets": ExecutionBudgetSnapshot().model_dump(mode="json"),
        }
    )
    if payload.provider:
        initial_state["provider_selection"] = {
            "provider": payload.provider,
            "reasoning": payload.reasoning or "medium",
            "context_detail": payload.context_detail or "medium",
        }

    async def event_generator() -> AsyncIterator[ServerSentEvent]:
        try:
            async for event in service.graph.astream(
                initial_state, config, stream_mode="updates"
            ):
                if isinstance(event, dict):
                    for node_name, state_delta in event.items():
                        safe_delta = _safe_json_delta(state_delta)
                        yield ServerSentEvent(
                            event=node_name,
                            data=json.dumps(safe_delta, default=str),
                        )
            yield ServerSentEvent(event="done", data=json.dumps({"status": "completed"}))
        except Exception as exc:
            yield ServerSentEvent(
                event="error",
                data=json.dumps({"detail": str(exc)}),
            )

    return EventSourceResponse(event_generator())


def _safe_json_delta(delta: Any) -> dict[str, Any]:
    """Convert a state delta to a JSON-safe dict for SSE."""
    if isinstance(delta, dict):
        return {k: _safe_value(v) for k, v in delta.items()}
    return {"value": str(delta)}


def _safe_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, dict):
        return {k: _safe_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe_value(v) for v in value]
    return str(value)
