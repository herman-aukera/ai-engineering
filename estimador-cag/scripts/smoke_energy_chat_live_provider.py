"""Manual live-provider smoke for Energy Aware Chat.

This script is intentionally excluded from normal deterministic CI. It requires
real GitHub or Codespaces secrets and proves that DeepSeek can draft while Kimi
is available as the configured backup tier.
"""

from __future__ import annotations

import json
import sys

from app.energy_chat.baseline import generate_deepseek_baseline_draft
from app.energy_chat.contracts import DeepSeekBaselineRequest
from app.services.litellm_provider import LiteLLMProvider


def main() -> int:
    provider = LiteLLMProvider()
    baseline = generate_deepseek_baseline_draft(
        DeepSeekBaselineRequest(
            user_message=(
                "Draft one concise release-readiness sentence for Energy Aware Chat. "
                "Do not claim deployment or quality improvement."
            ),
            tier="flash",
            max_tokens=128,
        ),
        provider=provider,
    )
    kimi_backup = provider.verify_visible_output(
        tier="backup",
        transcription="Reply with one visible sentence confirming backup-provider visibility.",
        system_prompt="You are a provider smoke-test assistant. Return one concise sentence.",
        max_tokens=64,
    )

    payload = {
        "baseline_provider": baseline.provider,
        "baseline_model": baseline.model,
        "baseline_tier": baseline.tier,
        "baseline_fallback_used": baseline.fallback_used,
        "baseline_visible_output": bool(baseline.draft_answer.strip()),
        "baseline_input_tokens": baseline.input_tokens,
        "baseline_output_tokens": baseline.output_tokens,
        "baseline_cost_usd": baseline.cost_usd,
        "backup_provider": kimi_backup["provider"],
        "backup_model": kimi_backup["model"],
        "backup_visible_output": kimi_backup["visible_output"],
        "backup_reliable": kimi_backup["reliable"],
        "claim_boundary": "live_provider_smoke_no_quality_claim",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))

    if not payload["baseline_visible_output"]:
        print("Energy Chat live smoke failed: DeepSeek baseline returned no visible output.")
        return 1
    if not payload["backup_reliable"]:
        print("Energy Chat live smoke failed: Kimi backup tier returned no visible output.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
