"""Operational readiness endpoint for deployment and orchestration probes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from app.services.production_readiness import (
    ProductionReadinessReport,
    build_production_readiness_report,
    runtime_availability_from_app_state,
)

router = APIRouter(tags=["health"])


@router.get(
    "/ready",
    response_model=ProductionReadinessReport,
    responses={503: {"model": ProductionReadinessReport}},
)
def readiness(request: Request, response: Response) -> ProductionReadinessReport:
    """Return 503 until graph runtimes and one real provider are configured."""

    report = build_production_readiness_report(
        runtime=runtime_availability_from_app_state(request.app.state)
    )
    if not report.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report
