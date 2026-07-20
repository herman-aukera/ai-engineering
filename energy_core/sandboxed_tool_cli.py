"""CLI for the sandboxed real-process tool adapter.

Disabled by default. Requires explicit --live-tool to enable real execution.
Without --live-tool, the CLI prints configuration and exits without creating
any process.

Usage:
    python -m energy_core.sandboxed_tool_cli \\
        --plan <path-to-ExecutionPlan.json> \\
        --repository-root <path> \\
        --run-id <id> \\
        [--authorization-receipt <path>] \\
        [--live-tool] \\
        [--format json|text]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from energy_core.controlled_execution import ExecutionPlan
from energy_core.execution_authorization import AuthorizationReceipt
from energy_core.sandboxed_tool import (
    RealToolResult,
    SandboxedToolAdapter,
    SandboxedToolConfig,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute a validated EACODE ExecutionPlan under strict policy."
    )
    parser.add_argument(
        "--plan", required=True, help="Path to an ExecutionPlan JSON file."
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--authorization-receipt",
        default=None,
        help="Path to an AuthorizationReceipt JSON file (required for human-gated plans).",
    )
    parser.add_argument(
        "--live-tool",
        action="store_true",
        default=False,
        help="Enable real process execution. Without this flag, execution is refused.",
    )
    parser.add_argument(
        "--format", choices=["json", "text"], default="json"
    )
    parser.add_argument(
        "--current-revision", type=int, default=0, help="Current repository revision."
    )
    parser.add_argument(
        "--trusted-actor",
        action="append",
        default=[],
        dest="trusted_actors",
        help="Trusted actor names (may be repeated).",
    )
    args = parser.parse_args(argv)

    plan = ExecutionPlan.model_validate(
        json.loads(Path(args.plan).read_text(encoding="utf-8"))
    )

    authorization_receipt = None
    if args.authorization_receipt:
        authorization_receipt = AuthorizationReceipt.model_validate(
            json.loads(Path(args.authorization_receipt).read_text(encoding="utf-8"))
        )

    if not args.live_tool:
        print(
            json.dumps(
                {
                    "status": "refused",
                    "reason": (
                        "Real execution requires --live-tool. "
                        "Use energy_core.controlled_execution_cli for dry-run/fake review."
                    ),
                    "plan_id": plan.plan_id,
                    "plan_hash": plan.plan_hash,
                    "disposition": plan.disposition,
                    "real_execution_supported": True,
                    "real_execution_enabled": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    config = SandboxedToolConfig(
        enabled=True,
        repository_root=args.repository_root,
        current_revision=args.current_revision,
        trusted_actors=args.trusted_actors,
    )

    adapter = SandboxedToolAdapter(config)
    result = adapter.invoke(plan, authorization_receipt=authorization_receipt)

    evidence = adapter.build_evidence(
        plan,
        result,
        run_id=args.run_id,
        authorization_receipt=authorization_receipt,
    )

    payload: dict[str, Any] = {
        "plan": plan.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "evidence": evidence.model_dump(mode="json"),
        "real_execution_supported": True,
        "real_execution_performed": True,
    }

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_format_text(payload, plan, result, evidence))

    return 0 if result.exit_code == 0 else result.exit_code or 1


def _format_text(
    payload: dict[str, Any],
    plan: ExecutionPlan,
    result: RealToolResult,
    evidence: Any,
) -> str:
    lines = [
        "EACODE Sandboxed Tool Execution",
        f"Plan: {plan.plan_id}",
        f"Plan hash: {plan.plan_hash}",
        f"Executable: {plan.executable}",
        f"Arguments: {' '.join(plan.arguments)}",
        f"Exit code: {result.exit_code}",
        f"Duration: {result.duration_ms}ms",
        f"Timed out: {result.timed_out}",
        f"Cancelled: {result.cancelled}",
        f"Process tree cleaned: {result.process_tree_cleaned}",
        f"Failure class: {result.failure_class}",
        f"Redacted: {result.redacted}",
        f"Output truncated: {result.stdout_truncated or result.stderr_truncated}",
        f"Evidence status: {evidence.status}",
        f"Execution performed: {evidence.execution_performed}",
        "--- stdout ---",
        result.stdout,
        "--- stderr ---",
        result.stderr,
        "Real execution performed: True",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
