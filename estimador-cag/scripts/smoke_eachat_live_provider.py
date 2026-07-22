"""One-call credentialed EACHAT smoke with sanitized evidence only."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.energy_chat.api_v2_contracts import EnergyChatV2Request
from app.energy_chat.runtime_container import EnergyChatApplicationRuntime

_KEY_ENV = {
    "deepseek": ("DEEPSEEK_API_KEY",),
    "kimi": ("MOONSHOT_API_KEY", "KIMI_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--provider", choices=("deepseek", "kimi", "openai"), required=True)
    parser.add_argument("--effort", choices=("fast", "balanced", "max"), default="balanced")
    parser.add_argument("--output", default="/tmp/eachat-live-provider-smoke.json")
    args = parser.parse_args()

    if not args.live:
        raise RuntimeError("Credentialed smoke requires the explicit --live flag")
    if not any(_usable_secret(os.environ.get(name, "")) for name in _KEY_ENV[args.provider]):
        raise RuntimeError(
            f"No usable credential is configured for selected provider {args.provider}"
        )

    runtime = EnergyChatApplicationRuntime()
    response = runtime.execute(
        EnergyChatV2Request(
            user_message=(
                "Explain one safe validation step for an AI service release. "
                "Do not claim that you ran tests or deployed anything."
            ),
            mode="chat_lite",
            provider_preference=args.provider,
            effort_profile=args.effort,
            context_profile="balanced",
            orchestration_mode="critic",
            execution_profile="live_bounded",
            allow_provider_fallback=False,
        ),
        "live_bounded",
    )
    metrics = response.provider_metrics_summary
    if not response.final_answer:
        raise RuntimeError("Live provider graph returned no visible final answer")
    if metrics.provider_call_count != 1:
        raise RuntimeError(
            f"Expected exactly one provider call, observed {metrics.provider_call_count}"
        )
    if response.fallback_used:
        raise RuntimeError("Live smoke unexpectedly used provider fallback")

    evidence = {
        "status": "success",
        "provider": response.served_provider,
        "model": response.served_model,
        "requested_provider": response.requested_provider,
        "effort": args.effort,
        "provider_call_count": metrics.provider_call_count,
        "input_tokens": metrics.total_input_tokens,
        "output_tokens": metrics.total_output_tokens,
        "estimated_cost_usd": metrics.total_cost_usd,
        "provider_latency_ms": metrics.total_latency_ms,
        "fallback_used": response.fallback_used,
        "final_disposition": response.final_disposition,
        "energy_decision": (
            response.energy_card_v2.decision if response.energy_card_v2 else None
        ),
        "answer_present": True,
        "answer_body_recorded": False,
        "prompt_body_recorded": False,
        "credential_recorded": False,
        "checkpoint_id": response.checkpoint_id,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(
        "EACHAT_LIVE_PROVIDER_SMOKE_OK "
        f"provider={response.served_provider} model={response.served_model} "
        f"calls={metrics.provider_call_count}"
    )


def _usable_secret(value: str) -> bool:
    normalized = value.strip().casefold()
    return bool(normalized) and normalized not in {
        "test",
        "dummy",
        "placeholder",
        "changeme",
    }


if __name__ == "__main__":
    main()
