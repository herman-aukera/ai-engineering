"""
LAYER: main (application entry point)
RESPONSIBILITY: Bootstrap FastAPI, register routers, middleware, and graph runtimes.
WHY IT EXISTS: Composition root pattern: all wiring happens in one place so the app is
               predictable, observable, rollback-safe, and testable.
DEPENDS_ON: app routers, graph runtimes, middleware logging
"""

import logging
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.embedding_pipeline.router import router as embedding_router
from app.generation.graph.observability import flush_logfire_graph_traces
from app.generation.graph.reviewed_runtime import (
    open_reviewed_graph_estimation_service,
)
from app.generation.graph.session14_runtime import (
    open_session14_graph_estimation_service as open_graph_estimation_service,
)
from app.generation.graph.unified_runtime import (
    open_unified_graph_estimation_service,
)
from app.middleware.logging import get_last_metrics, setup_logging
from app.routers.estimations import router as estimations_router
from app.routers.graph_estimations import router as graph_estimations_router
from app.routers.graph_rollout import router as graph_rollout_router
from app.routers.readiness import router as readiness_router
from app.routers.reviewed_graph_estimations import (
    router as reviewed_graph_estimations_router,
)
from app.routers.search import router as search_router
from app.routers.sessions import router as sessions_router
from app.routers.unified_graph_estimations import (
    router as unified_graph_estimations_router,
)
from app.routers.v2_estimations import router as v2_estimations_router
from app.services.litellm_timeout import install_litellm_request_timeout

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Own all versioned graph runtimes without cross-path failure coupling."""

    stack = AsyncExitStack()
    app.state.graph_estimation_service = None
    app.state.reviewed_graph_estimation_service = None
    app.state.unified_graph_estimation_service = None
    app.state.graph_runtime_error = None
    app.state.reviewed_graph_runtime_error = None
    app.state.unified_graph_runtime_error = None

    try:
        try:
            service = await stack.enter_async_context(
                open_graph_estimation_service()
            )
        except Exception as exc:
            app.state.graph_runtime_error = type(exc).__name__
            logger.exception("graph_estimation_runtime_initialization_failed")
        else:
            app.state.graph_estimation_service = service

        try:
            reviewed_service = await stack.enter_async_context(
                open_reviewed_graph_estimation_service()
            )
        except Exception as exc:
            app.state.reviewed_graph_runtime_error = type(exc).__name__
            logger.exception(
                "reviewed_graph_estimation_runtime_initialization_failed"
            )
        else:
            app.state.reviewed_graph_estimation_service = reviewed_service

        try:
            unified_service = await stack.enter_async_context(
                open_unified_graph_estimation_service()
            )
        except Exception as exc:
            app.state.unified_graph_runtime_error = type(exc).__name__
            logger.exception(
                "unified_graph_estimation_runtime_initialization_failed"
            )
        else:
            app.state.unified_graph_estimation_service = unified_service

        yield
    finally:
        app.state.unified_graph_estimation_service = None
        app.state.reviewed_graph_estimation_service = None
        app.state.graph_estimation_service = None
        await stack.aclose()
        try:
            flushed = flush_logfire_graph_traces()
        except Exception:
            logger.exception("graph_trace_flush_failed")
        else:
            if not flushed:
                logger.warning("graph_trace_flush_timed_out")


install_litellm_request_timeout()

app = FastAPI(
    title="LIDR Estimador CAG",
    description="Context-Augmented Generation (CAG) estimator",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_logging(app)

app.include_router(estimations_router)
app.include_router(graph_estimations_router)
app.include_router(graph_rollout_router)
app.include_router(reviewed_graph_estimations_router)
app.include_router(unified_graph_estimations_router)
app.include_router(v2_estimations_router)
app.include_router(sessions_router)
app.include_router(embedding_router, prefix="/embeddings", tags=["embeddings"])
app.include_router(search_router, tags=["search"])
app.include_router(readiness_router)


@app.get("/health", tags=["health"])
def health_check():
    """Liveness endpoint for Codespaces, containers, and deployment probes."""

    return {"status": "ok", "version": "0.4.0"}


@app.get("/metrics", tags=["observability"])
def metrics():
    """Return sanitized metrics from the last LLM call."""

    return get_last_metrics()


SESSION08_DEMO_HTML_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "session08_search_demo.html"
)
SSE_DEMO_HTML_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "sse_demo.html"
)


@app.get("/demo", include_in_schema=False)
def browser_demo() -> FileResponse:
    """Serve the Session 08 pgvector search demonstration."""

    return FileResponse(SESSION08_DEMO_HTML_PATH)


@app.get("/sse-demo", include_in_schema=False)
def sse_demo() -> FileResponse:
    """Serve the historical synchronous-versus-SSE demonstration."""

    return FileResponse(SSE_DEMO_HTML_PATH)


@app.get("/", include_in_schema=False)
def root_demo() -> FileResponse:
    """Serve the current browser demonstration from the root URL."""

    return FileResponse(SESSION08_DEMO_HTML_PATH)
