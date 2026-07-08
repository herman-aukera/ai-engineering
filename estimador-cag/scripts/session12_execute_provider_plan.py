"""
Execute a Session 12 provider plan artifact through deterministic local tools.

This script does not call live providers. It reads a previously generated plan
artifact and writes an executed result artifact.
"""

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.generation.agentic.agent_loop import execute_planned_steps_with_retrieval  # noqa: E402
from app.generation.agentic.agent_schemas import AgentRunRequest  # noqa: E402
from app.generation.agentic.provider_adapters import AgentPlannedStep  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute a Session 12 provider plan with deterministic tools.",
    )
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--output-file")
    parser.add_argument(
        "--transcript",
        default="Session 12 executed provider plan artifact.",
    )
    return parser


def _default_output_path(plan_file: Path) -> Path:
    return plan_file.with_name(plan_file.stem.replace("_plan", "_executed") + ".json")


async def execute_plan_file(
    *,
    plan_file: Path,
    output_file: Path,
    transcript: str,
) -> Path:
    plan_payload = json.loads(plan_file.read_text(encoding="utf-8"))
    raw_steps = plan_payload.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("Plan artifact must include a non-empty steps list.")

    provider = plan_payload.get("provider")
    if provider not in {"fake", "deepseek", "kimi", "openai"}:
        provider = "fake"

    model = plan_payload.get("model")
    planned_steps = [AgentPlannedStep(**step) for step in raw_steps]

    result = await execute_planned_steps_with_retrieval(
        AgentRunRequest(
            transcript=transcript,
            provider=provider,
            model=model,
        ),
        planned_steps,
    )

    output_payload = {
        "schema_version": "session12.executed_provider_plan.v1",
        "source_plan_schema_version": plan_payload.get("schema_version"),
        "provider": provider,
        "tier": plan_payload.get("tier"),
        "model": model,
        "temperature": plan_payload.get("temperature"),
        "result": result.model_dump(),
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(output_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_file


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan_file = Path(args.plan_file)
    output_file = Path(args.output_file) if args.output_file else _default_output_path(plan_file)

    try:
        written = asyncio.run(
            execute_plan_file(
                plan_file=plan_file,
                output_file=output_file,
                transcript=args.transcript,
            )
        )
    except Exception as exc:
        print(f"failed: {exc}")
        return 2

    print(f"wrote {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
