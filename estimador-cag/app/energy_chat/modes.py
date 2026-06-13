"""Mode constants for Energy Aware Chat."""

from __future__ import annotations

from enum import StrEnum


class EnergyChatMode(StrEnum):
    """Supported mode identifiers.

    Slice 1 implements only chat_lite behavior. Other values are declared so future
    slices can add mode overlays without changing the public contract shape.
    """

    CHAT_LITE = "chat_lite"
    RESEARCH = "research"
    PROJECT = "project"
    TUTOR = "tutor"
