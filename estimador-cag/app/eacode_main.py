"""Dedicated minimal FastAPI composition root for the EACODE product image."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.routers.eacode import router as eacode_router


def _configured_origins() -> list[str]:
    raw = os.getenv(
        "EACODE_ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    )
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins or "*" in origins:
        raise RuntimeError("EACODE_ALLOWED_ORIGINS must be an explicit non-empty allowlist")
    return origins


app = FastAPI(
    title="EACODE",
    description="Deterministic governed coding control plane",
    version="0.5.0-beta-hardening",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(eacode_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "product": "eacode",
        "version": "0.5.0-beta-hardening",
    }


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/eacode/ui", status_code=307)
