from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from energy_core.controlled_execution import (
    CommandProposal,
    FakeToolAdapter,
    FakeToolResult,
    review_execution,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a bounded EACODE execution plan without real shell execution."
    )
    parser.add_argument("--proposal", required=True, help="Path to a CommandProposal JSON file.")
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", choices=["dry_run", "fake"], default=None)
    parser.add_argument(
        "--fake-result",
        help="Optional FakeToolResult JSON file. Valid only with --mode fake.",
    )
    parser.add_argument("--format", choices=["json", "text"], default="json")
    parser.add_argument("--fail-on-deny", action="store_true")
    args = parser.parse_args(argv)

    proposal_payload = _read_json_object(Path(args.proposal))
    if args.mode is not None:
        proposal_payload["requested_mode"] = args.mode
    proposal = CommandProposal.model_validate(proposal_payload)

    if args.fake_result and proposal.requested_mode != "fake":
        parser.error("--fake-result requires --mode fake or requested_mode=fake")
    adapter = None
    if proposal.requested_mode == "fake":
        result = (
            FakeToolResult.model_validate(_read_json_object(Path(args.fake_result)))
            if args.fake_result
            else FakeToolResult()
        )
        adapter = FakeToolAdapter(result)

    plan, evidence = review_execution(
        proposal,
        repository_root=args.repository_root,
        run_id=args.run_id,
        adapter=adapter,
    )
    payload: dict[str, Any] = {
        "plan": plan.model_dump(mode="json"),
        "evidence": evidence.model_dump(mode="json"),
        "real_execution_supported": False,
    }
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_format_text(payload))

    return 2 if args.fail_on_deny and plan.disposition == "deny" else 0


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected one JSON object in {path}")
    return payload


def _format_text(payload: dict[str, Any]) -> str:
    plan = payload["plan"]
    evidence = payload["evidence"]
    return "\n".join(
        [
            "EACODE Controlled Execution Preview",
            f"Plan: {plan['plan_id']}",
            f"Risk: {plan['risk']}",
            f"Disposition: {plan['disposition']}",
            f"Human authorization required: {plan['requires_human_authorization']}",
            f"Mode: {plan['execution_mode']}",
            f"Adapter invoked: {evidence['adapter_invoked']}",
            f"Execution performed: {evidence['execution_performed']}",
            f"Evidence status: {evidence['status']}",
            "Real execution supported: False",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
