"""
LAYER: main (application entry point)
RESPONSIBILITY: Bootstrap the FastAPI application, register routers, and expose health checks
WHY IT EXISTS: Centralizes app composition so routers and middleware are wired in one place,
               following the "composition root" pattern. Avoids circular imports.
DEPENDS ON: app.routers.estimations (HTTP routes)
"""

from fastapi import FastAPI
from app.routers.estimations import router as estimations_router

app = FastAPI(
    title="LIDR Estimador CAG",
    description="Context-Augmented Generation (CAG) estimator for software engineering tasks",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(estimations_router)


@app.get("/health", tags=["health"])
def health_check():
    """Health endpoint for Codespaces port forwarding verification."""
    return {"status": "ok", "version": "0.2.0"}
