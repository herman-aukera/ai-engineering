"""Isolated production composition root for Energy Aware Chat.

The coursework application remains available through ``app.main``. This module
contains only the canonical EACHAT V2 service surface and requires durable
PostgreSQL, encrypted conversation memory, strict checkpoint deserialization, signed
actor identity, and restart-persistent ownership by default. Process-local storage is
available only through the explicit ``EACHAT_ALLOW_IN_MEMORY=true`` development/test
override.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from app.energy_aware_observability import observe_http_request
from app.energy_chat.byok_provider_override import install_byok_provider_override
from app.energy_chat.checkpoint_strict import StrictPostgresCheckpointer
from app.energy_chat.conversation_router import router as conversation_router
from app.energy_chat.conversation_store import (
    ConversationStore,
    InMemoryConversationStore,
    PostgresConversationStore,
)
from app.energy_chat.human_router import router as human_router
from app.energy_chat.ownership_store import (
    InMemoryResourceOwnershipStore,
    PostgresResourceOwnershipStore,
    ResourceOwnershipStore,
)
from app.energy_chat.production_identity import require_actor
from app.energy_chat.production_router import router as production_router
from app.energy_chat.request_byok import (
    BYOK_HEADER_NAMES,
    BYOKRequestError,
    parse_byok_headers,
    reset_request_byok,
    set_request_byok,
)
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime

logger = logging.getLogger(__name__)
DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
V2_DEMO_PATH = DOCS_DIR / "energy_chat_v2_demo.html"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"1", "true", "yes", "on"}


def _cors_origins() -> list[str]:
    raw = os.getenv("EACHAT_CORS_ORIGINS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _byok_enabled() -> bool:
    return _truthy(os.getenv("EA_ALLOW_BYOK"))


def _has_byok_headers(request: Request) -> bool:
    return any(request.headers.get(name) for name in BYOK_HEADER_NAMES)


def _identity_key() -> bytes:
    value = os.getenv("EACHAT_SESSION_SIGNING_KEY", "").encode("utf-8")
    if len(value) < 32:
        raise RuntimeError(
            "EACHAT_SESSION_SIGNING_KEY must contain at least 32 bytes in production."
        )
    return value


def _build_runtime() -> tuple[
    EnergyChatApplicationRuntime,
    StrictPostgresCheckpointer | None,
    ConversationStore,
    ResourceOwnershipStore,
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
        checkpointer = StrictPostgresCheckpointer(postgres_url)
        ownership_store: PostgresResourceOwnershipStore | None = None
        conversation_store: PostgresConversationStore | None = None
        try:
            checkpointer.setup()
            conversation_store = PostgresConversationStore(
                postgres_url,
                encryption_key=encryption_key,
            )
            conversation_store.setup()
            ownership_store = PostgresResourceOwnershipStore(postgres_url)
            ownership_store.setup()
        except Exception:
            if ownership_store is not None:
                ownership_store.close()
            if conversation_store is not None:
                conversation_store.close()
            checkpointer.close()
            raise
        return (
            EnergyChatApplicationRuntime(checkpointer=checkpointer),
            checkpointer,
            conversation_store,
            ownership_store,
        )
    if _truthy(os.getenv("EACHAT_ALLOW_IN_MEMORY")):
        conversation_store = InMemoryConversationStore()
        conversation_store.setup()
        ownership_store = InMemoryResourceOwnershipStore()
        ownership_store.setup()
        return EnergyChatApplicationRuntime(), None, conversation_store, ownership_store
    raise RuntimeError(
        "EACHAT_POSTGRES_URL is required for the production service. "
        "Set EACHAT_ALLOW_IN_MEMORY=true only for explicit local/test execution."
    )


def _authority_available(ownership_store: object) -> bool:
    if ownership_store is None:
        return False
    ping = getattr(ownership_store, "ping", None)
    if not callable(ping):
        return False
    try:
        return bool(ping())
    except Exception:
        logger.warning("eachat_authority_readiness_failed", exc_info=True)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    identity_key = _identity_key()
    runtime, checkpoint_backend, conversation_store, ownership_store = _build_runtime()
    app.state.energy_chat_runtime = runtime
    app.state.energy_chat_conversation_store = conversation_store
    app.state.energy_chat_ownership_store = ownership_store
    app.state.eachat_identity_signing_key = identity_key
    app.state.restart_persistent = checkpoint_backend is not None
    app.state.conversation_restart_persistent = conversation_store.restart_persistent
    app.state.ownership_restart_persistent = ownership_store.restart_persistent
    app.state.strict_msgpack = True
    app.state.startup_complete = True
    try:
        yield
    finally:
        app.state.startup_complete = False
        ownership_store.close()
        conversation_store.close()
        if checkpoint_backend is not None:
            checkpoint_backend.close()


def create_production_app() -> FastAPI:
    install_byok_provider_override()
    service = FastAPI(
        title="EACHAT",
        description="Energy-Aware Chat graph service",
        version="0.4.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    service.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            *BYOK_HEADER_NAMES,
        ],
    )

    @service.middleware("http")
    async def request_scoped_byok(request: Request, call_next) -> Response:
        if _has_byok_headers(request) and not _byok_enabled():
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Request-scoped BYOK is disabled."},
            )
        try:
            request_byok = parse_byok_headers(request.headers) if _byok_enabled() else None
        except BYOKRequestError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid request-scoped BYOK configuration."},
            )
        token = set_request_byok(request_byok)
        try:
            return await call_next(request)
        finally:
            reset_request_byok(token)

    @service.middleware("http")
    async def energy_aware_observability(request: Request, call_next) -> Response:
        return await observe_http_request(
            request,
            call_next,
            product="eachat",
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

    authenticated = [Depends(require_actor)]
    service.include_router(
        production_router,
        prefix="/energy-chat",
        tags=["energy-chat-v2"],
        dependencies=authenticated,
    )
    service.include_router(
        conversation_router,
        prefix="/energy-chat",
        tags=["energy-chat-memory"],
        dependencies=authenticated,
    )
    service.include_router(
        human_router,
        prefix="/energy-chat",
        tags=["energy-chat-human"],
        dependencies=authenticated,
    )

    @service.get("/startup", include_in_schema=False)
    def startup(response: Response) -> dict[str, object]:
        started = bool(getattr(service.state, "startup_complete", False))
        if not started:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "started" if started else "starting", "started": started}

    @service.get("/health", include_in_schema=False)
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "eachat",
            "restart_persistent": bool(service.state.restart_persistent),
            "conversation_restart_persistent": bool(
                service.state.conversation_restart_persistent
            ),
            "ownership_restart_persistent": bool(
                service.state.ownership_restart_persistent
            ),
            "strict_msgpack": bool(service.state.strict_msgpack),
        }

    @service.get("/ready", include_in_schema=False)
    def ready(response: Response) -> dict[str, object]:
        started = bool(getattr(service.state, "startup_complete", False))
        runtime = getattr(service.state, "energy_chat_runtime", None)
        conversation_store = getattr(
            service.state,
            "energy_chat_conversation_store",
            None,
        )
        ownership_store = getattr(service.state, "energy_chat_ownership_store", None)
        identity_key = getattr(service.state, "eachat_identity_signing_key", None)
        authority_available = _authority_available(ownership_store)
        is_ready = (
            started
            and isinstance(runtime, EnergyChatApplicationRuntime)
            and conversation_store is not None
            and ownership_store is not None
            and authority_available
            and isinstance(identity_key, bytes)
            and len(identity_key) >= 32
        )
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "ready" if is_ready else "not_ready",
            "ready": is_ready,
            "restart_persistent": bool(
                getattr(service.state, "restart_persistent", False)
            ),
            "conversation_restart_persistent": bool(
                getattr(service.state, "conversation_restart_persistent", False)
            ),
            "ownership_restart_persistent": bool(
                getattr(service.state, "ownership_restart_persistent", False)
            ),
            "authority_store_available": authority_available,
            "strict_msgpack": bool(getattr(service.state, "strict_msgpack", False)),
            "identity_required": True,
            "byok_enabled": _byok_enabled(),
        }

    @service.get("/version", include_in_schema=False)
    def version() -> dict[str, str]:
        return {
            "service": "eachat",
            "version": service.version,
            "git_sha": os.getenv("GIT_SHA", "unknown"),
        }

    @service.get("/energy-chat/v2/demo", include_in_schema=False)
    def browser_client() -> FileResponse:
        if not V2_DEMO_PATH.is_file():
            raise HTTPException(
                status_code=503,
                detail="EACHAT browser client is unavailable",
            )
        return FileResponse(V2_DEMO_PATH)

    @service.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/energy-chat/v2/demo", status_code=307)

    return service


app = create_production_app()
