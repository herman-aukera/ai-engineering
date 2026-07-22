"""FastAPI application composition root."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response

from app.embedding_pipeline.router import router as embedding_router
from app.energy_chat.human_router import router as energy_chat_human_router
from app.energy_chat.router import router as energy_chat_router
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime
from app.energy_chat.settings import energy_chat_v2_enabled
from app.middleware.logging import get_last_metrics, setup_logging
from app.routers.estimations import router as estimations_router
from app.routers.sessions import router as sessions_router

app = FastAPI(
    title="LIDR Estimador CAG",
    description="Context-Augmented Generation (CAG) estimator",
    version="0.3.0",
)
app.state.energy_chat_runtime = EnergyChatApplicationRuntime()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Apply safe browser defaults without exposing environment-dependent values."""

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    if request.url.path.startswith("/energy-chat"):
        response.headers["Cache-Control"] = "no-store"
    if request.url.path in {"/energy-chat/v2/demo", "/energy-chat/demo"}:
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
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


setup_logging(app)
app.include_router(estimations_router)
app.include_router(sessions_router)
app.include_router(embedding_router, prefix="/embeddings", tags=["embeddings"])
app.include_router(energy_chat_router, prefix="/energy-chat", tags=["energy-chat"])
app.include_router(
    energy_chat_human_router,
    prefix="/energy-chat",
    tags=["energy-chat-human"],
)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "version": "0.3.0"}


@app.get("/metrics", tags=["observability"])
def metrics():
    return get_last_metrics()


DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
DEMO_HTML_PATH = DOCS_DIR / "sse_demo.html"
ENERGY_CHAT_DEMO_HTML_PATH = DOCS_DIR / "energy_chat_demo.html"
ENERGY_CHAT_V2_DEMO_HTML_PATH = DOCS_DIR / "energy_chat_v2_demo.html"


@app.get("/energy-chat/v2/demo", include_in_schema=False)
def energy_chat_v2_browser_demo() -> FileResponse:
    """Serve the V2 product UI only while the feature is enabled."""

    if not energy_chat_v2_enabled():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "v2_disabled",
                "detail": "Energy Chat V2 is disabled by EACHAT_V2_ENABLED.",
            },
        )
    return FileResponse(ENERGY_CHAT_V2_DEMO_HTML_PATH)


@app.get("/energy-chat/demo", include_in_schema=False)
def energy_chat_browser_demo() -> FileResponse:
    """Preserve the legacy evaluator/demo as the rollback path."""

    return FileResponse(ENERGY_CHAT_DEMO_HTML_PATH)


def _energy_chat_product_url() -> str:
    return "/energy-chat/v2/demo" if energy_chat_v2_enabled() else "/energy-chat/demo"


@app.get("/demo", include_in_schema=False)
def browser_demo() -> RedirectResponse:
    return RedirectResponse(url=_energy_chat_product_url(), status_code=307)


@app.get("/", include_in_schema=False)
def root_demo() -> RedirectResponse:
    return RedirectResponse(url=_energy_chat_product_url(), status_code=307)
