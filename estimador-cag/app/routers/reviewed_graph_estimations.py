"""Additive API for durable Session 13 Plus human-review executions."""

from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.generation.graph.nodes.structure_review import StaleStructureReviewError
from app.schemas.reviewed_graph_estimation import (
    ReviewedGraphExecutionResponse,
    ReviewedGraphResumeRequest,
    ReviewedGraphStartRequest,
)
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
