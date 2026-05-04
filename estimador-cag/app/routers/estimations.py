"""
LAYER: routers (HTTP transport)
RESPONSIBILITY: Define endpoints for estimation requests and wire them to the service layer
WHY IT EXISTS: Isolates HTTP-specific concerns from prompt engineering and LLM logic.
               Schemas movidos a app/schemas/ por decision arquitectonica (Heladia).
DEPENDS ON: app.schemas.estimation, app.services.llm_service
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.estimation import EstimateRequest, EstimateResponse
from app.services.llm_service import estimate

router = APIRouter(prefix="/api/v1", tags=["estimations"])


@router.post("/estimate", response_model=EstimateResponse, status_code=status.HTTP_200_OK)
def create_estimation(request: EstimateRequest):
    """
    POST /api/v1/estimate
    MEJORA: respeta request.tier (tu version original lo ignoraba).
    MEJORA V2: captura RuntimeError cuando todos los tiers fallan -> HTTP 503.
    """
    try:
        result = estimate(request.transcription, tier=request.tier)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Error en llamada a LLM: {str(e)}")
