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
from fastapi.responses import FileResponse, RedirectResponse

from app.embedding_pipeline.router import router as embedding_router
from app.energy_chat.router import router as energy_chat_router
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
    allow_headers=["*"],
)

# Wire observability middleware
setup_logging(app)

# Transport layer
app.include_router(estimations_router)
app.include_router(sessions_router)
app.include_router(embedding_router, prefix="/embeddings", tags=["embeddings"])
app.include_router(energy_chat_router, prefix="/energy-chat", tags=["energy-chat"])


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


DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
DEMO_HTML_PATH = DOCS_DIR / "sse_demo.html"
ENERGY_CHAT_DEMO_HTML_PATH = DOCS_DIR / "energy_chat_demo.html"
ENERGY_CHAT_V2_DEMO_HTML_PATH = DOCS_DIR / "energy_chat_v2_demo.html"


@app.get("/energy-chat/v2/demo", include_in_schema=False)
def energy_chat_v2_browser_demo() -> FileResponse:
    """Serve the V2 graph-backed Energy Aware Chat browser demo."""
    return FileResponse(ENERGY_CHAT_V2_DEMO_HTML_PATH)


@app.get("/energy-chat/demo", include_in_schema=False)
def energy_chat_browser_demo() -> FileResponse:
    """
    LAYER: presentation helper
    RESPONSIBILITY: Serve the Energy Aware Chat browser demo from the FastAPI app.
    WHY IT EXISTS: Gives reviewers and humans a same-origin UI for the MVP path:
                   project RAG, local agent orchestration, Energy Card, and
                   measurement-only benchmark output.
    DEPENDS_ON: docs/energy_chat_demo.html
    """
    return FileResponse(ENERGY_CHAT_DEMO_HTML_PATH)


@app.get("/demo", include_in_schema=False)
def browser_demo() -> RedirectResponse:
    """
    Redirect the generic demo URL to the Energy Aware Chat browser demo.

    The old SSE demo remains available only as a static file in docs. For the
    final-project branch, the default human path should be Energy Aware Chat.
    """
    return RedirectResponse(url="/energy-chat/demo", status_code=307)


@app.get("/", include_in_schema=False)
def root_demo() -> RedirectResponse:
    """
    Redirect the FastAPI root to the Energy Aware Chat browser demo.

    This makes opening the Codespaces port 8000 URL land on the correct product
    demo without manually typing `/energy-chat/demo`.
    """
    return RedirectResponse(url="/energy-chat/demo", status_code=307)
