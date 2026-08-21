"""Minimal production composition root for the EACODE control plane.

The coursework application keeps the legacy ``/eacode`` compatibility surface in
``app.main``. This production root publishes the same deterministic product
semantics under the explicit major-version namespace ``/api/v1/eacode`` and does
not mount unrelated estimator/chat routes.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.routers.eacode import router as eacode_router


def _cors_origins() -> list[str]:
    raw = os.getenv("EACODE_CORS_ORIGINS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def create_production_app() -> FastAPI:
    service = FastAPI(
        title="EACODE",
        description="Deterministic Energy-Aware coding control plane",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
    )
    service.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
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
        if request.url.path.startswith("/api/v1/eacode"):
            response.headers["Cache-Control"] = "no-store"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    service.include_router(eacode_router, prefix="/api/v1")

    @service.get("/startup", include_in_schema=False)
    def startup() -> dict[str, object]:
        return {"status": "started", "started": True}

    @service.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        """Cheap local liveness probe; it performs no provider call."""

        return {"status": "ok", "service": "eacode"}

    @service.get("/ready", include_in_schema=False)
    def ready() -> dict[str, object]:
        """The deterministic selector has no external runtime dependency."""

        return {"status": "ready", "ready": True, "control_plane": "deterministic"}

    @service.get("/version", include_in_schema=False)
    def version() -> dict[str, str]:
        return {
            "service": "eacode",
            "version": service.version,
            "git_sha": os.getenv("GIT_SHA", "unknown"),
        }

    return service


app = create_production_app()
