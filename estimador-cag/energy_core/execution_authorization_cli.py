from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from energy_core.controlled_execution import ExecutionPlan
from energy_core.execution_authorization import (
    AuthorizationContext,
    ExecutionAuthorization,
    consume_execution_authorization,
    verify_execution_authorization,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify or consume one exact EACODE execution authorization."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("verify", "consume"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--plan", required=True)
        subparser.add_argument("--authorization", required=True)
        subparser.add_argument("--context", required=True)
        subparser.add_argument("--format", choices=["json", "text"], default="json")
        if command == "consume":
            subparser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    plan = ExecutionPlan.model_validate(_read_json_object(Path(args.plan)))
    authorization = ExecutionAuthorization.model_validate(
        _read_json_object(Path(args.authorization))
    )
    context = AuthorizationContext.model_validate(_read_json_object(Path(args.context)))
    decision = verify_execution_authorization(plan, authorization, context)

    payload: dict[str, Any] = {
        "decision": decision.model_dump(mode="json"),
        "authorization_consumed": False,
        "execution_performed": False,
    }
    if args.command == "consume" and decision.authorized:
        consumed, updated_context, receipt = consume_execution_authorization(
            plan,
            authorization,
            context,
        )
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(output_dir / "authorization.json", consumed.model_dump(mode="json"))
        _write_json(output_dir / "context.json", updated_context.model_dump(mode="json"))
        _write_json(output_dir / "receipt.json", receipt.model_dump(mode="json"))
        payload.update(
            {
                "authorization_consumed": True,
                "receipt": receipt.model_dump(mode="json"),
                "output_dir": str(output_dir.resolve()),
            }
        )

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_format_text(payload))
    return 0 if decision.authorized else 2


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected one JSON object in {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _format_text(payload: dict[str, Any]) -> str:
    decision = payload["decision"]
    return "\n".join(
        [
            "EACODE Execution Authorization",
            f"Authorized: {decision['authorized']}",
            f"Reasons: {', '.join(decision['reasons']) or 'none'}",
            f"Revision: {decision['current_revision']}",
            f"Authorization consumed: {payload['authorization_consumed']}",
            "Execution performed: False",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
