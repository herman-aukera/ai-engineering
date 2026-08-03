"""Additive API for the consolidated Session 13 + 14 Plus graph."""

from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError

from app.generation.graph.nodes.session14_human_review import (
    IncompleteSession14AdjustmentError,
    StaleSession14HumanReviewError,
)
from app.schemas.graph_estimation import (
    GraphEstimationRequest,
    GraphEstimationResponse,
    GraphHumanReviewResumeRequest,
)
from app.services.graph_estimation import (
    GraphEstimationApplication,
    GraphEstimationNotFoundError,
    GraphHumanReviewConflictError,
)
from app.services.graph_product_adapter import graph_response_from_run
from app.services.unified_control_projection import (
    UnifiedControlProjection,
    unified_control_projection_from_run,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/estimate/graph/unified",
    tags=["unified-estimations"],
)


class UnifiedRuntimeReadiness(BaseModel):
    """Sanitized readiness projection for the additive unified runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ready: bool
    graph_name: str
    graph_version: str
    runtime_error: str | None = None
    rollback_paths: list[str]


def _safe_error_type(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 120:
        return None
    return value if value.isidentifier() else None


def get_unified_graph_estimation_service(
    request: Request,
) -> GraphEstimationApplication:
    """Resolve only the lifespan-owned unified service."""

    service = getattr(
        request.app.state,
        "unified_graph_estimation_service",
        None,
    )
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Unified estimation graph service is not available.",
        )
    return cast(GraphEstimationApplication, service)


def _raise_resume_error(exc: Exception) -> None:
    if isinstance(exc, GraphEstimationNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(
        exc,
        (GraphHumanReviewConflictError, StaleSession14HumanReviewError),
    ):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, IncompleteSession14AdjustmentError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(
            status_code=502,
            detail="Unified human review produced an invalid response.",
        ) from exc
    raise HTTPException(
        status_code=502,
        detail="Failed to resume unified graph human review.",
    ) from exc


@router.get(
    "/readiness",
    response_model=UnifiedRuntimeReadiness,
)
def unified_graph_readiness(request: Request) -> UnifiedRuntimeReadiness:
    """Report unified runtime availability without changing legacy readiness."""

    ready = (
        getattr(
            request.app.state,
            "unified_graph_estimation_service",
            None,
        )
        is not None
    )
    return UnifiedRuntimeReadiness(
        ready=ready,
        graph_name="session13_14_plus_unified_graph",
        graph_version="session13_14_plus.unified.v1",
        runtime_error=_safe_error_type(
            getattr(
                request.app.state,
                "unified_graph_runtime_error",
                None,
            )
        ),
        rollback_paths=[
            "/api/v1/estimate/graph",
            "/api/v1/estimate/graph/reviewed/start",
        ],
    )


@router.post(
    "",
    response_model=GraphEstimationResponse,
)
async def create_unified_graph_estimation(
    payload: GraphEstimationRequest,
    service: GraphEstimationApplication = Depends(
        get_unified_graph_estimation_service
    ),
) -> GraphEstimationResponse:
    """Execute the canonical graph without replacing older graph endpoints."""

    try:
        run = await service.estimate(
            transcript=payload.transcript,
            estimation_id=payload.estimation_id,
        )
        return graph_response_from_run(run)
    except ValidationError as exc:
        logger.exception("unified_graph_estimation_response_invalid")
        raise HTTPException(
            status_code=502,
            detail="Failed to produce a unified graph estimate.",
        ) from exc
    except Exception as exc:
        logger.exception("unified_graph_estimation_execution_failed")
        raise HTTPException(
            status_code=502,
            detail="Failed to produce a unified graph estimate.",
        ) from exc


@router.post(
    "/control",
    response_model=UnifiedControlProjection,
)
async def create_unified_control_projection(
    payload: GraphEstimationRequest,
    service: GraphEstimationApplication = Depends(
        get_unified_graph_estimation_service
    ),
) -> UnifiedControlProjection:
    """Run the graph and return only allowlisted control-plane evidence."""

    try:
        run = await service.estimate(
            transcript=payload.transcript,
            estimation_id=payload.estimation_id,
        )
        return unified_control_projection_from_run(run)
    except ValidationError as exc:
        logger.exception("unified_control_projection_invalid")
        raise HTTPException(
            status_code=502,
            detail="Failed to produce a unified control projection.",
        ) from exc
    except Exception as exc:
        logger.exception("unified_control_execution_failed")
        raise HTTPException(
            status_code=502,
            detail="Failed to produce a unified control projection.",
        ) from exc


@router.post(
    "/{estimation_id}/resume",
    response_model=GraphEstimationResponse,
)
async def resume_unified_graph_human_review(
    estimation_id: UUID,
    payload: GraphHumanReviewResumeRequest,
    service: GraphEstimationApplication = Depends(
        get_unified_graph_estimation_service
    ),
) -> GraphEstimationResponse:
    """Resume the persisted unified graph on its original thread."""

    try:
        run = await service.resume_human_review(
            estimation_id=estimation_id,
            decision=payload,
        )
        return graph_response_from_run(run)
    except Exception as exc:
        logger.exception("unified_graph_human_review_resume_failed")
        _raise_resume_error(exc)
        raise AssertionError("unreachable")


@router.post(
    "/control/{estimation_id}/resume",
    response_model=UnifiedControlProjection,
)
async def resume_unified_control_projection(
    estimation_id: UUID,
    payload: GraphHumanReviewResumeRequest,
    service: GraphEstimationApplication = Depends(
        get_unified_graph_estimation_service
    ),
) -> UnifiedControlProjection:
    """Resume and return the refreshed allowlisted Control Room projection."""

    try:
        run = await service.resume_human_review(
            estimation_id=estimation_id,
            decision=payload,
        )
        return unified_control_projection_from_run(run)
    except Exception as exc:
        logger.exception("unified_control_human_review_resume_failed")
        _raise_resume_error(exc)
        raise AssertionError("unreachable")
