"""Additive HTTP transport for the Session 13 estimation graph."""

from __future__ import annotations

import logging
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.schemas.graph_estimation import (
    GraphEstimationRequest,
    GraphEstimationResponse,
)
from app.services.graph_estimation import (
    GraphEstimationApplication,
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
