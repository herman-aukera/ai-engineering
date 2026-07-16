"""Credentialed Session 13 Plus provider and telemetry smoke.

The runner records only bounded, sanitized metadata. It never writes prompts,
model content, API keys, or the Logfire token to its artifact.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import logfire

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.generation.graph.observability import get_logfire_graph_tracer  # noqa: E402
from app.services.litellm_agent_model import LiteLLMAgentModel  # noqa: E402

TIERS = ("flash", "backup")


def build_artifact(*, rows: list[dict[str, object]]) -> dict[str, object]:
    """Build the secret-free promotion artifact."""

    return {
        "schema_version": "session13.plus.live_runtime.v1",
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "scope": "credentialed_provider_and_logfire_smoke",
        "providers": rows,
        "all_providers_completed": all(row["status"] == "completed" for row in rows),
        "telemetry": {
            "backend": "logfire",
            "remote_send_requested": True,
            "span_name": "session13.plus.live_provider",
        },
        "privacy": {
            "prompt_recorded": False,
            "model_content_recorded": False,
            "credentials_recorded": False,
        },
    }


async def run_provider(tier: str) -> dict[str, object]:
    """Call one logical provider tier through the Plus adapter."""

    model = LiteLLMAgentModel(tier=tier, max_tokens=96)
    tracer = get_logfire_graph_tracer()
    started = perf_counter()
    with tracer.span(
        "session13.plus.live_provider",
        logical_tier=tier,
        smoke_scope="session13_plus",
    ) as span:
        try:
            turn = await model.complete_turn(
                messages=(
                    {
                        "role": "system",
                        "content": "Reply with one short sentence confirming availability.",
                    },
                    {"role": "user", "content": "Provider availability smoke."},
                ),
                tools=(),
            )
        except Exception as exc:
            span.set_attribute("status", "provider_error")
            span.set_attribute("error_type", type(exc).__name__)
            return {
                "tier": tier,
                "status": "provider_error",
                "error_type": type(exc).__name__,
                "elapsed_ms": int((perf_counter() - started) * 1000),
            }

        span.set_attribute("status", "completed")
        span.set_attribute("provider", turn.provider)
        span.set_attribute("model", turn.model)
        return {
            "tier": tier,
            "provider": turn.provider,
            "model": turn.model,
            "status": "completed",
            "visible_output": bool((turn.content or "").strip()),
            "input_tokens": turn.input_tokens,
            "output_tokens": turn.output_tokens,
            "cost_usd": turn.cost_usd,
            "finish_reason": turn.finish_reason,
            "elapsed_ms": int((perf_counter() - started) * 1000),
        }


async def run(output: Path) -> int:
    rows = [await run_provider(tier) for tier in TIERS]
    artifact = build_artifact(rows=rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    force_flush = getattr(logfire, "force_flush", None)
    if callable(force_flush):
        force_flush()
    print(json.dumps({"output": str(output), "statuses": [row["status"] for row in rows]}))
    return 0 if artifact["all_providers_completed"] else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/session13/live/session13_plus_live_runtime.json",
    )
    args = parser.parse_args()
    return asyncio.run(run(Path(args.output)))


if __name__ == "__main__":
    raise SystemExit(main())
