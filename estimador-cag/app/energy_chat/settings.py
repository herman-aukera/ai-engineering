"""Runtime configuration helpers for Energy Aware Chat.

Configuration is read at request time so tests and rollback operations can change
feature flags without rebuilding the FastAPI application.
"""

from __future__ import annotations

import os

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def energy_chat_v2_enabled() -> bool:
    """Return whether graph-backed V2 surfaces are enabled.

    Invalid values fail closed. The default remains enabled for backward
    compatibility with the existing EACHAT branch.
    """

    raw = os.getenv("EACHAT_V2_ENABLED", "true").strip().lower()
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    return False
