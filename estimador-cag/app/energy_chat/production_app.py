"""Isolated production composition root for Energy Aware Chat.

The coursework application remains available through ``app.main``. This module
contains only the EACHAT service surface and requires durable PostgreSQL, encrypted
conversation memory, and strict checkpoint deserialization by default. Process-local
storage is available only through the explicit ``EACHAT_ALLOW_IN_MEMORY=true``
development/test override.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response

from app.energy_chat.checkpoint_postgres import PostgresCheckpointer
from app.energy_chat.conversation_router import router as conversation_router
from app.energy_chat.conversation_store import (
    ConversationStore,
    InMemoryConversationStore,
    PostgresConversationStore,
)
from app.energy_chat.human_router import router as human_router
from app.energy_chat.router import router as energy_chat_router
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
V2_DEMO_PATH = DOCS_DIR / "energy_chat_v2_demo.html"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"1", "true", "yes", "on"}


def _build_runtime() -> tuple[
    EnergyChatApplicationRuntime,
    PostgresCheckpointer | None,
    ConversationStore,
]:
    if not _truthy(os.getenv("LANGGRAPH_STRICT_MSGPACK")):
        raise RuntimeError(
            "LANGGRAPH_STRICT_MSGPACK=true is required for the production service."
        )

    postgres_url = os.getenv("EACHAT_POSTGRES_URL", "").strip()
    if postgres_url:
        encryption_key = os.getenv("EACHAT_MEMORY_ENCRYPTION_KEY", "").strip()
        if not encryption_key:
            raise RuntimeError(
                "EACHAT_MEMORY_ENCRYPTION_KEY is required for durable conversation memory."
            )
        checkpointer = PostgresCheckpointer(postgres_url)
        try:
            checkpointer.setup()
            conversation_store = PostgresConversationStore(
                postgres_url,
                encryption_key=encryption_key,
            )
            conversation_store.setup()
        except Exception:
            checkpointer.close()
            raise
        return (
            EnergyChatApplicationRuntime(checkpointer=checkpointer),
            checkpointer,
            conversation_store,
        )

    if _truthy(os.getenv("EACHAT_ALLOW_IN_MEMORY")):
        conversation_store = InMemoryConversationStore()
        conversation_store.setup()
        return EnergyChatApplicationRuntime(), None, conversation_store

    raise RuntimeError(
        "EACHAT_POSTGRES_URL is required for the production service. "
        "Set EACHAT_ALLOW_IN_MEMORY=true only for explicit local/test execution."
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    runtime, checkpoint_backend, conversation_store = _build_runtime()
    app.state.energy_chat_runtime = runtime
    app.state.energy_chat_conversation_store = conversation_store
    app.state.restart_persistent = checkpoint_backend is not None
    app.state.conversation_restart_persistent = conversation_store.restart_persistent
    app.state.strict_msgpack = True
    try:
        yield
    finally:
        conversation_store.close()
        if checkpoint_backend is not None:
            checkpoint_backend.close()


def create_production_app() -> FastAPI:
    service = FastAPI(
        title="EACHAT",
        description="Energy-Aware Chat graph service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    service.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
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
        if request.url.path.startswith("/energy-chat"):
            response.headers["Cache-Control"] = "no-store"
        if request.url.path == "/energy-chat/v2/demo":
            response.headers["Content-Security-Policy"] = "; ".join(
                (
                    "default-src 'self'",
                    "script-src 'self' 'unsafe-inline'",
                    "style-src 'self' 'unsafe-inline'",
                    "img-src 'self' data:",
                    "connect-src 'self'",
                    "font-src 'self'",
                    "object-src 'none'",
                    "base-uri 'none'",
                    "form-action 'self'",
                    "frame-ancestors 'none'",
                )
            )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    service.include_router(energy_chat_router, prefix="/energy-chat", tags=["energy-chat"])
    service.include_router(
        conversation_router,
        prefix="/energy-chat",
        tags=["energy-chat-memory"],
    )
    service.include_router(human_router, prefix="/energy-chat", tags=["energy-chat-human"])

    @service.get("/health", include_in_schema=False)
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "eachat",
            "restart_persistent": bool(service.state.restart_persistent),
            "conversation_restart_persistent": bool(
                service.state.conversation_restart_persistent
            ),
            "strict_msgpack": bool(service.state.strict_msgpack),
        }

    @service.get("/energy-chat/v2/demo", include_in_schema=False)
    def browser_client() -> FileResponse:
        if not V2_DEMO_PATH.is_file():
            raise HTTPException(status_code=503, detail="EACHAT browser client is unavailable")
        return FileResponse(V2_DEMO_PATH)

    @service.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/energy-chat/v2/demo", status_code=307)

    return service


app = create_production_app()
