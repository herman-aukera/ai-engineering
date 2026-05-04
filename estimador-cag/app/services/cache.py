"""
LAYER: services (caching)
RESPONSIBILITY: Intelligent response caching for LLM estimations.
WHY IT EXISTS: Avoids redundant API calls (cost saving) and improves
               latency for repeated transcriptions. TTL prevents stale data.
DEPENDS ON: Nothing (pure utility)
"""

import hashlib
import time
from functools import wraps

# In-memory cache: {hash: (timestamp, result)}
_cache_store: dict[str, tuple[float, dict]] = {}


def _make_key(transcription: str, tier: str) -> str:
    """Deterministic hash key from inputs."""
    raw = f"{transcription}:{tier}"
    return hashlib.sha256(raw.encode()).hexdigest()


def cached_estimate(ttl_seconds: int = 300):
    """
    Decorator: caches the result of estimate() for ttl_seconds.
    WHY decorator: Non-invasive caching that wraps the existing function
                   without modifying its internals.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(transcription: str, tier: str | None = None):
            effective_tier = tier or "flash"
            key = _make_key(transcription, effective_tier)
            now = time.time()

            if key in _cache_store:
                cached_at, result = _cache_store[key]
                if now - cached_at < ttl_seconds:
                    result["cached"] = True
                    return result

            # Cache miss: call real function
            result = func(transcription, tier)
            result["cached"] = False
            _cache_store[key] = (now, result)
            return result
        return wrapper
    return decorator
