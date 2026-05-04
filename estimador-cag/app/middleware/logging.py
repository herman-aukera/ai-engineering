"""
LAYER: middleware (observability)
RESPONSIBILITY: Log request metadata and expose runtime metrics endpoint.
WHY IT EXISTS: Session 3 requires observability. Middleware captures latency
               and token usage transparently for every /estimate call.
DEPENDS ON: app.config (settings), time, logging
"""

import logging
import time
from collections import deque

from fastapi import Request

logger = logging.getLogger(__name__)

# Rolling window of last 100 call metrics
_metrics_history: deque[dict] = deque(maxlen=100)
_last_call: dict = {}


async def logging_middleware(request: Request, call_next):
    """
    ASGI middleware: logs method, path, and duration.
    WHY async: FastAPI middleware must be async to avoid blocking.
    """
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    logger.info(
        f"{request.method} {request.url.path} "
        f"-> {response.status_code} in {duration:.3f}s"
    )
    return response


def setup_logging(app):
    """
    Wire middleware into the FastAPI app composition root.
    WHY centralized: Keeps main.py clean; middleware is attached here, not in main.
    """
    app.middleware("http")(logging_middleware)


def record_call_metrics(result: dict):
    """
    Record metrics from a successful LLM call.
    WHY separate function: llm_service.py calls this to push data without
       knowing about HTTP middleware internals.
    """
    global _last_call
    _last_call = {
        "model": result.get("model"),
        "tier": result.get("tier"),
        "provider": result.get("provider"),
        "input_tokens": result.get("input_tokens"),
        "output_tokens": result.get("output_tokens"),
        "timestamp": result.get("timestamp"),
        "cached": result.get("cached", False),
    }
    _metrics_history.append(_last_call)
    logger.info(f"Metrics recorded: {_last_call['tier']} tokens={_last_call['input_tokens']}/{_last_call['output_tokens']}")


def get_last_metrics() -> dict:
    """Return metrics from the most recent LLM call."""
    return _last_call.copy()


def get_metrics_history() -> list[dict]:
    """Return rolling window of recent call metrics."""
    return list(_metrics_history)
