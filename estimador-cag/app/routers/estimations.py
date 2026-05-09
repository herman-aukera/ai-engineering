"""
LAYER: routers (HTTP transport)
RESPONSIBILITY: Define estimation endpoints and wire HTTP requests to LLM services.
WHY IT EXISTS: Isolates FastAPI transport concerns from prompt building, caching,
               provider routing, and streaming business logic.
DEPENDS ON: fastapi, sse_starlette, app.schemas.estimation,
            app.services.llm_service, app.middleware.logging
"""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.middleware.logging import record_call_metrics
from app.schemas.estimation import EstimateRequest, EstimateResponse
from app.services.llm_service import estimate, estimate_stream

router = APIRouter(prefix="/api/v1", tags=["estimations"])


@router.post("/estimate", response_model=EstimateResponse)
def create_estimation(request: EstimateRequest):
    """
    POST /api/v1/estimate

    Receives a meeting transcription and returns a CAG software estimation.
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
        raise HTTPException(status_code=503, detail=f"Error LLM: {str(exc)}") from exc


@router.post("/estimate/stream")
def stream_estimation(request: EstimateRequest):
    """
    POST /api/v1/estimate/stream

    Streams an estimation using Server Sent Events.

    Event types:
    - token: partial text chunk
    - done: final metadata
    - error: failure details
    """

    def event_generator():
        started_at = datetime.now(UTC)
        output_chars = 0

        try:
            for token in estimate_stream(request.transcription, tier=request.tier):
                output_chars += len(token)
                yield ServerSentEvent(event="token", data=token)

            metadata = {
                "tier": request.tier or "flash",
                "output_chars": output_chars,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
            }
            yield ServerSentEvent(event="done", data=json.dumps(metadata))

        except Exception as exc:
            yield ServerSentEvent(
                event="error",
                data=json.dumps({"detail": str(exc)}),
            )

    return EventSourceResponse(event_generator())
