"""Additive HTTP transport for the Session 13 estimation graph."""

from __future__ import annotations

import logging
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

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

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["estimations"],
)


def get_graph_estimation_service(
    request: Request,
) -> GraphEstimationApplication:
    """Resolve the lifespan-owned graph service."""

    service = getattr(
        request.app.state,
        "graph_estimation_service",
        None,
    )

    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Estimation graph service is not available.",
        )

    return cast(GraphEstimationApplication, service)


@router.post(
    "/estimate/graph",
    response_model=GraphEstimationResponse,
)
async def create_graph_estimation(
    payload: GraphEstimationRequest,
    service: GraphEstimationApplication = Depends(
        get_graph_estimation_service
    ),
) -> GraphEstimationResponse:
    """Execute the graph without changing the established estimate routes."""

    try:
        run = await service.estimate(
            transcript=payload.transcript,
            estimation_id=payload.estimation_id,
        )
        return graph_response_from_run(run)
    except ValidationError as exc:
        logger.exception(
            "graph_estimation_response_invalid"
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to produce a graph estimate.",
        ) from exc
    except Exception as exc:
        logger.exception(
            "graph_estimation_execution_failed"
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to produce a graph estimate.",
        ) from exc


@router.post(
    "/estimate/graph/{estimation_id}/resume",
    response_model=GraphEstimationResponse,
)
async def resume_graph_human_review(
    estimation_id: UUID,
    payload: GraphHumanReviewResumeRequest,
    service: GraphEstimationApplication = Depends(
        get_graph_estimation_service
    ),
) -> GraphEstimationResponse:
    """Resume one persisted Task 14 review on its original thread."""

    try:
        run = await service.resume_human_review(
            estimation_id=estimation_id,
            decision=payload,
        )
        return graph_response_from_run(run)
    except GraphEstimationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        GraphHumanReviewConflictError,
        StaleSession14HumanReviewError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IncompleteSession14AdjustmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValidationError as exc:
        logger.exception("graph_human_review_response_invalid")
        raise HTTPException(
            status_code=502,
            detail="Human review produced an invalid graph response.",
        ) from exc
    except Exception as exc:
        logger.exception("graph_human_review_resume_failed")
        raise HTTPException(
            status_code=502,
            detail="Failed to resume graph human review.",
        ) from exc
