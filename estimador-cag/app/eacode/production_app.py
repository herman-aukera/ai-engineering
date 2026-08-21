"""Isolated production composition root for the EACODE control plane.

Production publishes only the explicitly versioned EACODE service surface and
operational probes. Authoritative proposals, receipts and execution reservations
must use the versioned PostgreSQL store before the process becomes ready.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.energy_aware_observability import observe_http_request
from app.routers.eacode import router as eacode_router
from energy_core.beta_store_runtime import build_beta_demo_store

logger = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    raw = os.getenv("EACODE_CORS_ORIGINS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _validate_signing_key() -> None:
    signing_key = os.getenv("EACODE_SESSION_SIGNING_KEY", "")
    if len(signing_key.encode("utf-8")) < 32:
        raise RuntimeError(
            "EACODE_SESSION_SIGNING_KEY must contain at least 32 bytes in production."
        )


@asynccontextmanager
async def lifespan(service: FastAPI) -> AsyncIterator[None]:
    _validate_signing_key()
    store = build_beta_demo_store(require_durable=True)
    store.verify_schema()
    service.state.startup_complete = True
    service.state.authority_store = "postgresql"
    try:
        yield
    finally:
        service.state.startup_complete = False


def create_production_app() -> FastAPI:
    service = FastAPI(
        title="EACODE",
        description="Deterministic Energy-Aware coding control plane",
        version="0.2.0",
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
        return await observe_http_request(request, call_next, product="eacode", logger=logger)

    @service.middleware("http")
    async def security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        if request.url.path.startswith("/api/v1/eacode"):
            response.headers["Cache-Control"] = "no-store"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    service.include_router(eacode_router, prefix="/api/v1")

    @service.get("/startup", include_in_schema=False)
    def startup(response: Response) -> dict[str, object]:
        started = bool(getattr(service.state, "startup_complete", False))
        if not started:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "started" if started else "starting", "started": started}

    @service.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "eacode"}

    @service.get("/ready", include_in_schema=False)
    def ready(response: Response) -> dict[str, object]:
        started = bool(getattr(service.state, "startup_complete", False))
        authority_store = getattr(service.state, "authority_store", None)
        is_ready = started and authority_store == "postgresql"
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "ready" if is_ready else "not_ready",
            "ready": is_ready,
            "control_plane": "deterministic",
            "authority_store": authority_store,
        }

    @service.get("/version", include_in_schema=False)
    def version() -> dict[str, str]:
        return {"service": "eacode", "version": service.version, "git_sha": os.getenv("GIT_SHA", "unknown")}

    return service


app = create_production_app()
