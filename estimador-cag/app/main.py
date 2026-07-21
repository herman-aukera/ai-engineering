"""FastAPI application composition root."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

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
    """Serve the V2 demo only while the V2 feature is enabled."""

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
    return FileResponse(ENERGY_CHAT_DEMO_HTML_PATH)


@app.get("/demo", include_in_schema=False)
def browser_demo() -> RedirectResponse:
    return RedirectResponse(url="/energy-chat/demo", status_code=307)


@app.get("/", include_in_schema=False)
def root_demo() -> RedirectResponse:
    return RedirectResponse(url="/energy-chat/demo", status_code=307)
