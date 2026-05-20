"""
LAYER: main (application entry point)
RESPONSIBILITY: Bootstrap FastAPI, register routers, middleware, and health/metrics.
WHY IT EXISTS: Composition root pattern: all wiring happens in one place
               so the app is predictable and testable.
DEPENDS ON: app.routers.estimations, app.middleware.logging
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.middleware.logging import get_last_metrics, setup_logging
from app.routers.estimations import router as estimations_router
from app.routers.sessions import router as sessions_router

app = FastAPI(
    title="LIDR Estimador CAG",
    description="Context-Augmented Generation (CAG) estimator",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Wire observability middleware
setup_logging(app)

# Transport layer
app.include_router(estimations_router)
app.include_router(sessions_router)


@app.get("/health", tags=["health"])
def health_check():
    """Health endpoint for Codespaces port forwarding."""
    return {"status": "ok", "version": "0.3.0"}


@app.get("/metrics", tags=["observability"])
def metrics():
    """
    Runtime metrics from the last LLM call.
    WHY: Session 3 observability requirement. Shows tokens, tier, latency.
    """
    return get_last_metrics()

DEMO_HTML_PATH = Path(__file__).resolve().parents[1] / "docs" / "sse_demo.html"


@app.get("/demo", include_in_schema=False)
def browser_demo() -> FileResponse:
    """
    LAYER: presentation helper
    RESPONSIBILITY: Serve the browser SSE demo from the FastAPI app.
    WHY IT EXISTS: Keeps the browser demo on the same origin as the API, which avoids
    Codespaces CORS and mixed-content issues while giving nontechnical users one clean URL.
    DEPENDS_ON: docs/sse_demo.html
    """
    return FileResponse(DEMO_HTML_PATH)

@app.get("/", include_in_schema=False)
def root_demo() -> FileResponse:
    """
    LAYER: presentation helper
    RESPONSIBILITY: Serve the browser demo from the root URL.
    WHY IT EXISTS: Gives nontechnical testers one obvious URL when they open
    the forwarded FastAPI port in Codespaces.
    DEPENDS_ON: docs/sse_demo.html
    """
    return FileResponse(DEMO_HTML_PATH)
