"""
LAYER: main (application entry point)
RESPONSIBILITY: Bootstrap FastAPI, register routers, middleware, and health/metrics.
WHY IT EXISTS: Composition root pattern: all wiring happens in one place
               so the app is predictable and testable.
DEPENDS ON: application routers and middleware.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.embedding_pipeline.router import router as embedding_router
from app.middleware.logging import get_last_metrics, setup_logging
from app.routers.eacode import router as eacode_router
from app.routers.estimations import router as estimations_router
from app.routers.sessions import router as sessions_router

app = FastAPI(
    title="LIDR Estimador CAG + EACODE",
    description="CAG estimator with an Energy-Aware governed coding control plane",
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

setup_logging(app)

app.include_router(estimations_router)
app.include_router(sessions_router)
app.include_router(embedding_router, prefix="/embeddings", tags=["embeddings"])
app.include_router(eacode_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Health endpoint for Codespaces port forwarding."""

    return {"status": "ok", "version": "0.5.0"}


@app.get("/metrics", tags=["observability"])
def metrics():
    """Return runtime metrics from the last LLM call."""

    return get_last_metrics()


DEMO_HTML_PATH = Path(__file__).resolve().parents[1] / "docs" / "sse_demo.html"


@app.get("/demo", include_in_schema=False)
def browser_demo() -> FileResponse:
    """Serve the existing browser SSE demo from the FastAPI app."""

    return FileResponse(DEMO_HTML_PATH)


@app.get("/", include_in_schema=False)
def root_demo() -> FileResponse:
    """Serve the existing browser demo from the root URL."""

    return FileResponse(DEMO_HTML_PATH)


def _configured_cors_origins() -> list[str]:
    """Return an explicit origin allowlist; wildcard CORS is never the default."""

    raw = os.getenv(
        "EACODE_ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    )
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins or "*" in origins:
        raise RuntimeError("EACODE_ALLOWED_ORIGINS must be an explicit non-empty allowlist")
    return origins
