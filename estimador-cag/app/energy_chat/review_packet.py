"""Review packet helpers for Energy Aware Chat documentation navigation."""

from __future__ import annotations

from dataclasses import dataclass

from app.energy_chat.artifact_registry import artifact_paths


@dataclass(frozen=True)
class ReviewPacket:
    """Ordered paths a reviewer can open before running the demo."""

    open_first: tuple[str, ...]
    runnable_entries: tuple[str, ...]


def build_review_packet() -> ReviewPacket:
    """Build a compact reviewer navigation packet from the artifact registry."""

    paths = artifact_paths()
    open_first = tuple(
        path
        for path in paths
        if path.startswith("docs/energy_aware_chat_")
    )
    runnable_entries = tuple(
        path
        for path in paths
        if path.startswith("scripts/") or path == "energy_chat_streamlit_app.py"
    )
    return ReviewPacket(open_first=open_first, runnable_entries=runnable_entries)
