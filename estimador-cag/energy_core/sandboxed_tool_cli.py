"""Fail-closed CLI for the secure EACODE live-execution path.

The legacy real-process adapter is not reachable from this CLI. A process can
be attempted only when all of the following are supplied and validated:

- an explicit ``LiveExecutionPlan``;
- its matching ``LiveExecutionIntent``;
- an authoritative SQLite live-authorization database;
- a matching one-time receipt ID;
- an explicit ``--live-tool`` opt-in.

Without ``--live-tool`` the command refuses before reserving authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from energy_core.live_authorization import (
    LiveAuthorizationReceipt,
    SQLiteLiveAuthorizationStore,
)
from energy_core.live_execution_contract import LiveExecutionIntent, LiveExecutionPlan
from energy_core.secure_execution_service import (
    SecureExecutionOutcome,
    SecureExecutionService,
)
from energy_core.secure_process_adapter import SecureProcessAdapter, SecureProcessConfig

Executor = Callable[..., SecureExecutionOutcome]


def main(
    argv: list[str] | None = None,
    *,
    executor: Executor | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Execute one authorized EACODE live plan under strict policy."
    )
    parser.add_argument("--plan", required=True, help="LiveExecutionPlan JSON path.")
    parser.add_argument("--intent", required=True, help="LiveExecutionIntent JSON path.")
    parser.add_argument("--authorization-db", required=True)
    parser.add_argument("--receipt-id", required=True)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--current-revision", type=int, required=True)
    parser.add_argument(
        "--trusted-actor",
        action="append",
        default=[],
        dest="trusted_actors",
    )
    parser.add_argument(
        "--live-tool",
        action="store_true",
        default=False,
        help="Reserve authority and permit one bounded process attempt.",
    )
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args(argv)

    plan = LiveExecutionPlan.model_validate(_read_json(args.plan))
    intent = LiveExecutionIntent.model_validate(_read_json(args.intent))

    if not args.live_tool:
        _print_payload(
            {
                "status": "refused",
                "reason": "Real execution requires explicit --live-tool opt-in.",
                "live_plan_hash": plan.plan_hash,
                "base_plan_hash": plan.base_plan_hash,
                "authorization_receipt_id": plan.authorization_receipt_id,
                "real_execution_supported": True,
                "real_execution_enabled": False,
                "real_execution_performed": False,
            },
            output_format=args.format,
        )
        return 2

    store = SQLiteLiveAuthorizationStore(args.authorization_db)
    receipt = store.get(args.receipt_id)
    if receipt is None:
        _print_refusal(
            PermissionError("Authoritative live authorization receipt was not found."),
            output_format=args.format,
        )
        return 2

    execute = executor or _execute_secure
    try:
        outcome = execute(
            plan=plan,
            intent=intent,
            receipt=receipt,
            store=store,
            repository_root=args.repository_root,
            current_revision=args.current_revision,
            trusted_actors=args.trusted_actors,
            run_id=args.run_id,
        )
    except (OSError, PermissionError, ValueError) as exc:
        _print_refusal(exc, output_format=args.format)
        return 2

    payload = {
        "status": outcome.evidence.status,
        "real_execution_supported": True,
        "real_execution_enabled": True,
        "real_execution_performed": outcome.evidence.execution_performed,
        "result": outcome.result.model_dump(mode="json"),
        "evidence": outcome.evidence.model_dump(mode="json"),
        "authority": {
            "receipt_id": outcome.reserved_receipt.receipt_id,
            "reserved": outcome.reserved_receipt.execution_reserved,
            "completion_verified": (
                outcome.evidence.authority_completion_verified
            ),
            "final_record_hash": (
                outcome.final_receipt.record_hash
                if outcome.final_receipt is not None
                else None
            ),
        },
    }
    _print_payload(payload, output_format=args.format)
    return 0 if outcome.evidence.status == "pass" else 1


def _execute_secure(
    *,
    plan: LiveExecutionPlan,
    intent: LiveExecutionIntent,
    receipt: LiveAuthorizationReceipt,
    store: SQLiteLiveAuthorizationStore,
    repository_root: str,
    current_revision: int,
    trusted_actors: list[str],
    run_id: str,
) -> SecureExecutionOutcome:
    config = SecureProcessConfig(
        enabled=True,
        repository_root=repository_root,
        current_revision=current_revision,
        trusted_actors=trusted_actors,
    )
    adapter = SecureProcessAdapter(config, receipt_store=store)
    service = SecureExecutionService(adapter=adapter, receipt_store=store)
    return service.execute(plan, intent, receipt, run_id=run_id)


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print_refusal(exc: Exception, *, output_format: str) -> None:
    _print_payload(
        {
            "status": "refused",
            "error_type": type(exc).__name__,
            "reason": _bounded_reason(exc),
            "real_execution_performed": False,
        },
        output_format=output_format,
    )


def _bounded_reason(exc: Exception) -> str:
    value = " ".join(str(exc).split())
    return value[:500] or type(exc).__name__


def _print_payload(payload: dict[str, Any], *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    lines = ["EACODE Secure Live Execution"]
    for key, value in payload.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for nested_key, nested_value in value.items():
                lines.append(f"  {nested_key}: {nested_value}")
        else:
            lines.append(f"{key}: {value}")
    print("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
