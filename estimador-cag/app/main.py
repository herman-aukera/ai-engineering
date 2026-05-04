"""
LAYER: main (application entry point)
RESPONSIBILITY: Bootstrap FastAPI, register routers, middleware, and health/metrics.
WHY IT EXISTS: Composition root pattern: all wiring happens in one place
               so the app is predictable and testable.
DEPENDS ON: app.routers.estimations, app.middleware.logging
"""

from fastapi import FastAPI

from app.middleware.logging import get_last_metrics, setup_logging
from app.routers.estimations import router as estimations_router

app = FastAPI(
    title="LIDR Estimador CAG",
    description="Context-Augmented Generation (CAG) estimator",
    version="0.3.0",
)

# Wire observability middleware
setup_logging(app)

# Transport layer
app.include_router(estimations_router)


@app.get("/health", tags=["health"])
def health_check():
    """Health endpoint for Codespaces port forwarding."""
    return {"status": "ok", "version": "0.3.0"}


@app.get("/metrics", tags=["observability"])
def metrics():
    """
    Runtime metrics from the last LLM call.
    WHY: Session 3 observability requirement. Shows tokens, tier, latency.
    """
    return get_last_metrics()
