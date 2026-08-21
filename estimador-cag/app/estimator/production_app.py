"""Isolated production composition root for the Energy-Aware estimator.

The historical coursework application remains available through ``app.main`` for
compatibility and teaching evidence. Production deploys this module instead: only
the consolidated Session 13/14 unified estimator API and operational probes are
published.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from app.generation.graph.observability import flush_logfire_graph_traces
from app.generation.graph.unified_runtime import open_unified_graph_estimation_service
from app.routers.unified_graph_estimations import router as unified_graph_estimations_router

logger = logging.getLogger(__name__)
_PLACEHOLDER_KEYS = frozenset({"", "test", "dummy", "fake", "placeholder", "example"})


class EstimatorReadinessReport(BaseModel):
    """Sanitized production-readiness projection without network/model calls."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    ready: bool
    startup_complete: bool
    unified_runtime: bool
    configured_providers: list[str]
    runtime_error: str | None = None


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _configured_providers() -> list[str]:
    providers: list[str] = []
    candidates = (
        ("deepseek", os.getenv("DEEPSEEK_API_KEY", "")),
        ("moonshot", os.getenv("KIMI_API_KEY", "")),
        ("openai", os.getenv("OPENAI_API_KEY", "")),
    )
    for provider, value in candidates:
        if value.strip().casefold() not in _PLACEHOLDER_KEYS:
            providers.append(provider)
    return providers


def _safe_error_type(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 120:
        return None
    return value if value.isidentifier() else None


@asynccontextmanager
async def lifespan(service: FastAPI) -> AsyncIterator[None]:
    """Own only the canonical unified runtime for the production process."""

    stack = AsyncExitStack()
    service.state.unified_graph_estimation_service = None
    service.state.unified_graph_runtime_error = None
    service.state.startup_complete = False
    try:
        try:
            runtime = await stack.enter_async_context(
                open_unified_graph_estimation_service()
            )
        except Exception as exc:
            service.state.unified_graph_runtime_error = type(exc).__name__
            logger.exception("unified_estimator_runtime_initialization_failed")
        else:
            service.state.unified_graph_estimation_service = runtime
        service.state.startup_complete = True
        yield
    finally:
        service.state.startup_complete = False
        service.state.unified_graph_estimation_service = None
        await stack.aclose()
        try:
            flush_logfire_graph_traces()
        except Exception:
            logger.exception("unified_estimator_trace_flush_failed")


def create_production_app() -> FastAPI:
    service = FastAPI(
        title="Energy-Aware Estimator",
        description="Consolidated Session 13/14 estimation control plane",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    service.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )

    @service.middleware("http")
    async def security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    service.include_router(unified_graph_estimations_router)

    @service.get("/startup", include_in_schema=False)
    def startup(response: Response) -> dict[str, object]:
        started = bool(getattr(service.state, "startup_complete", False))
        if not started:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "started" if started else "starting", "started": started}

    @service.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        """Cheap local liveness probe; performs no database or model call."""

        return {"status": "ok", "service": "estimator"}

    @service.get(
        "/ready",
        response_model=EstimatorReadinessReport,
        responses={503: {"model": EstimatorReadinessReport}},
        include_in_schema=False,
    )
    def ready(response: Response) -> EstimatorReadinessReport:
        """Require initialized durable graph runtime and one configured provider."""

        started = bool(getattr(service.state, "startup_complete", False))
        runtime_ready = (
            getattr(service.state, "unified_graph_estimation_service", None) is not None
        )
        providers = _configured_providers()
        is_ready = started and runtime_ready and bool(providers)
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return EstimatorReadinessReport(
            status="ready" if is_ready else "not_ready",
            ready=is_ready,
            startup_complete=started,
            unified_runtime=runtime_ready,
            configured_providers=providers,
            runtime_error=_safe_error_type(
                getattr(service.state, "unified_graph_runtime_error", None)
            ),
        )

    @service.get("/version", include_in_schema=False)
    def version() -> dict[str, str]:
        return {
            "service": "estimator",
            "version": service.version,
            "git_sha": os.getenv("GIT_SHA", "unknown"),
        }

    return service


app = create_production_app()
