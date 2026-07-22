"""Compatibility imports for the hardened EACODE live-provider runtime.

All live-provider behavior is implemented in :mod:`energy_core.live_adapter_v2`.
The public import surface remains stable for existing scripts and tests.
"""

from energy_core.live_adapter_v2 import (
    BaseLiveAdapter,
    DeepSeekAdapter,
    KimiCodeAdapter,
    LiveAdapterConfig,
    OpenAIAdapter,
    _chat_completions_url,
    _openai_compatible_call,
    _request_body,
)

__all__ = [
    "BaseLiveAdapter",
    "DeepSeekAdapter",
    "KimiCodeAdapter",
    "LiveAdapterConfig",
    "OpenAIAdapter",
    "_chat_completions_url",
    "_openai_compatible_call",
    "_request_body",
]
