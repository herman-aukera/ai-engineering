"""
LAYER: routers (HTTP transport)
RESPONSIBILITY: Define estimation endpoints and wire to services.
WHY IT EXISTS: Isolates HTTP concerns from prompt/LLM logic.
DEPENDS ON: app.schemas.estimation, app.services.llm_service,
            app.middleware.logging
"""

from fastapi import APIRouter, HTTPException

from app.middleware.logging import record_call_metrics
from app.schemas.estimation import EstimateRequest, EstimateResponse
from app.services.llm_service import estimate

router = APIRouter(prefix="/api/v1", tags=["estimations"])


@router.post("/estimate", response_model=EstimateResponse)
def create_estimation(request: EstimateRequest):
    """
    POST /api/v1/estimate
    Recibe transcripcion y devuelve estimacion CAG.
    """
    try:
        result = estimate(request.transcription, tier=request.tier)
        record_call_metrics(result)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Error LLM: {str(exc)}"
        ) from exc
