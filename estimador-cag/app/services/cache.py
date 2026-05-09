"""
LAYER: services (caching)
RESPONSIBILITY: Exact-match TTL cache for LLM estimations.
WHY IT EXISTS: Avoids repeated LLM calls for identical transcriptions and tiers,
               reducing cost and latency during development and demos.
DEPENDS_ON: hashlib, time, functools
"""

import hashlib
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

_cache_store: dict[str, tuple[float, dict[str, Any]]] = {}


def _make_key(transcription: str, tier: str) -> str:
    """Create deterministic SHA256 key from transcription and tier."""
    raw = f"{tier}::{transcription}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cached_estimate(ttl_seconds: int = 300):
    """
    Decorator for estimate(transcription, tier).

    LAYER: services
    RESPONSIBILITY: Wrap the estimation function with exact-match cache.
    WHY IT EXISTS: Keeps cache logic outside the LLM business function.
    DEPENDS_ON: _make_key, _cache_store
    """

    def decorator(func: Callable[..., dict[str, Any]]):
        @wraps(func)
        def wrapper(transcription: str, tier: str | None = None):
            effective_tier = tier or "flash"
            key = _make_key(transcription, effective_tier)
            now = time.time()

            if key in _cache_store:
                cached_at, cached_result = _cache_store[key]
                if now - cached_at < ttl_seconds:
                    result = cached_result.copy()
                    result["cached"] = True
                    return result

                del _cache_store[key]

            result = func(transcription, tier).copy()
            result["cached"] = False
            _cache_store[key] = (now, result.copy())
            return result

        return wrapper

    return decorator
