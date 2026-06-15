"""Manual live-provider smoke for Energy Aware Chat.

This script is intentionally excluded from normal deterministic tests. It requires
real DeepSeek and Kimi credentials and is meant to be run only from the manual
GitHub Actions workflow or a trusted developer shell.

It proves two things:
1. DeepSeek primary tier can return a visible message.
2. The Energy Chat baseline fallback seam can continue to real Kimi when
   DeepSeek tiers are unavailable.
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.energy_chat.baseline import generate_deepseek_baseline_draft
from app.energy_chat.contracts import DeepSeekBaselineRequest, ProviderTier
from app.services.litellm_provider import LiteLLMProvider


def _require_live_secret(name: str) -> None:
    value = os.getenv(name, "").strip()
    if not value or value == "test" or value.startswith("replace-with"):
        raise RuntimeError(f"Missing live secret: {name}")


def _short_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "Return one concise sentence. Do not include secrets or markdown.",
        },
        {
            "role": "user",
            "content": "Say that the Energy Aware Chat live provider smoke is reachable.",
        },
    ]


def _assert_visible_response(result: dict[str, Any], *, expected_provider: str) -> None:
    content = result.get("estimation") or result.get("draft_answer")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"{expected_provider} smoke returned no visible response")
    if result.get("provider") != expected_provider:
        raise RuntimeError(
            f"Expected provider={expected_provider}, got provider={result.get('provider')!r}"
        )


class ForcedKimiFallbackProvider(LiteLLMProvider):
    """Force DeepSeek tiers to fail so the fallback ladder must reach Kimi."""

    def complete_messages(
        self,
        *,
        messages: list[dict[str, str]],
        tier: ProviderTier,
        max_tokens: int = 2000,
    ) -> dict:
        if tier in {"flash", "pro"}:
            raise RuntimeError(f"forced live-smoke failure for tier={tier}")
        return super().complete_messages(messages=messages, tier=tier, max_tokens=max_tokens)


def main() -> None:
    _require_live_secret("DEEPSEEK_API_KEY")
    _require_live_secret("KIMI_API_KEY")

    provider = LiteLLMProvider()

    deepseek_result = provider.complete_messages(
        messages=_short_messages(),
        tier="flash",
        max_tokens=96,
    )
    _assert_visible_response(deepseek_result, expected_provider="deepseek")

    fallback_request = DeepSeekBaselineRequest(
        user_message="Return one concise sentence confirming the Kimi fallback path is reachable.",
        mode="chat_lite",
        tier="flash",
        max_tokens=96,
    )
    fallback_result = generate_deepseek_baseline_draft(
        fallback_request,
        provider=ForcedKimiFallbackProvider(),
    )

    if fallback_result.provider != "kimi":
        raise RuntimeError(f"Expected fallback provider kimi, got {fallback_result.provider!r}")
    if not fallback_result.fallback_used:
        raise RuntimeError("Expected fallback_used=true after forced DeepSeek tier failures")
    if fallback_result.tier not in {"backup", "backup_pro"}:
        raise RuntimeError(f"Expected Kimi backup tier, got {fallback_result.tier!r}")
    if not fallback_result.draft_answer.strip():
        raise RuntimeError("Kimi fallback returned an empty draft answer")

    print(
        json.dumps(
            {
                "decision": "accept",
                "deepseek_primary": {
                    "provider": deepseek_result.get("provider"),
                    "tier": deepseek_result.get("tier"),
                    "model": deepseek_result.get("model"),
                    "input_tokens": deepseek_result.get("input_tokens"),
                    "output_tokens": deepseek_result.get("output_tokens"),
                },
                "kimi_fallback": {
                    "provider": fallback_result.provider,
                    "tier": fallback_result.tier,
                    "model": fallback_result.model,
                    "fallback_used": fallback_result.fallback_used,
                    "input_tokens": fallback_result.input_tokens,
                    "output_tokens": fallback_result.output_tokens,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
