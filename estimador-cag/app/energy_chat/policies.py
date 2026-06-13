"""Default Energy Aware Chat policies."""

from __future__ import annotations

from app.energy_chat.contracts import EnergyPolicy


def default_chat_lite_policy() -> EnergyPolicy:
    """Return the deterministic MVP policy for chat_lite evaluations."""

    return EnergyPolicy()
