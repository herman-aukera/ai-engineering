"""Isolated production composition root for the Energy-Aware estimator.

The historical coursework application remains available through ``app.main`` for
compatibility and teaching evidence. Production deploys this module instead: only
the consolidated estimator API and operational probes are published. Persisted
estimation IDs are bound to signed tenant actors in durable PostgreSQL ownership.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from app.energy_aware_observability import observe_http_request
from app.estimator.ownership_store import (
    EstimationOwnershipStore,
    InMemoryEstimationOwnershipStore,
    PostgresEstimationOwnershipStore,
)
from app.estimator.production_identity import require_actor
from app.generation.graph.observability import flush_logfire_graph_traces
from app.generation.graph.unified_runtime import open_unified_graph_estimation_service
from app.routers.unified_graph_estimations import router as unified_graph_estimations_router

logger = logging.getLogger(__name__)
_PLACEHOLDER_KEYS = frozenset({"", "test", "dummy", "fake", "placeholder", "example"})


class EstimatorReadinessReport(BaseModel):
    """Sanitized production-readiness projection without model calls."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    ready: bool
    startup_complete: bool
    unified_runtime: bool
    configured_providers: list[str]
    ownership_restart_persistent: bool
    authority_store_available: bool
    identity_required: bool
    runtime_error: str | None = None


def _truthy(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"1", "true", "yes", "on"}


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


def _identity_key() -> bytes:
    value = os.getenv("ESTIMATOR_SESSION_SIGNING_KEY", "").encode("utf-8")
    if len(value) < 32:
        raise RuntimeError(
            "ESTIMATOR_SESSION_SIGNING_KEY must contain at least 32 bytes in production."
        )
    return value


def _build_ownership_store() -> EstimationOwnershipStore:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        store = PostgresEstimationOwnershipStore(database_url)
        store.setup()
        return store
    if _truthy(os.getenv("ESTIMATOR_ALLOW_IN_MEMORY_OWNERSHIP")):
        store = InMemoryEstimationOwnershipStore()
        store.setup()
        return store
    raise RuntimeError(
        "DATABASE_URL is required for estimator production ownership. "
        "Set ESTIMATOR_ALLOW_IN_MEMORY_OWNERSHIP=true only for explicit tests."
    )


def _authority_available(ownership: object) -> bool:
    if ownership is None:
        return False
    ping = getattr(ownership, "ping", None)
    if not callable(ping):
        return False
    try:
        return bool(ping())
    except Exception:
        logger.warning("estimator_authority_readiness_failed", exc_info=True)
        return False


@asynccontextmanager
async def lifespan(service: FastAPI) -> AsyncIterator[None]:
    """Own canonical graph runtime, signed identity, and durable ownership."""

    stack = AsyncExitStack()
    ownership_store = _build_ownership_store()
    identity_key = _identity_key()
    service.state.estimator_ownership_store = ownership_store
    service.state.estimator_identity_signing_key = identity_key
    service.state.unified_graph_estimation_service = None
    service.state.unified_graph_runtime_error = None
    service.state.startup_complete = False
    try:
        try:
            runtime = await stack.enter_async_context(open_unified_graph_estimation_service())
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
        ownership_store.close()
        await stack.aclose()
        try:
            flush_logfire_graph_traces()
        except Exception:
            logger.exception("unified_estimator_trace_flush_failed")


def create_production_app() -> FastAPI:
    service = FastAPI(
        title="Energy-Aware Estimator",
        description="Consolidated Energy-Aware estimation control plane",
        version="1.1.0",
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
    async def energy_aware_observability(request: Request, call_next) -> Response:
        return await observe_http_request(
            request,
            call_next,
            product="estimator",
            logger=logger,
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

    service.include_router(
        unified_graph_estimations_router,
        dependencies=[Depends(require_actor)],
    )

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
        """Require initialized runtime, reachable authority DB, identity, and provider config."""
        started = bool(getattr(service.state, "startup_complete", False))
        runtime_ready = getattr(service.state, "unified_graph_estimation_service", None) is not None
        providers = _configured_providers()
        ownership = getattr(service.state, "estimator_ownership_store", None)
        identity_key = getattr(service.state, "estimator_identity_signing_key", None)
        ownership_ready = ownership is not None
        authority_available = _authority_available(ownership)
        identity_ready = isinstance(identity_key, bytes) and len(identity_key) >= 32
        is_ready = (
            started
            and runtime_ready
            and bool(providers)
            and ownership_ready
            and authority_available
            and identity_ready
        )
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return EstimatorReadinessReport(
            status="ready" if is_ready else "not_ready",
            ready=is_ready,
            startup_complete=started,
            unified_runtime=runtime_ready,
            configured_providers=providers,
            ownership_restart_persistent=bool(getattr(ownership, "restart_persistent", False)),
            authority_store_available=authority_available,
            identity_required=True,
            runtime_error=_safe_error_type(getattr(service.state, "unified_graph_runtime_error", None)),
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
