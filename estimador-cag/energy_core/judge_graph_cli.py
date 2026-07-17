from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from langgraph.types import Command

from energy_core.judge_graph import judge_input
from energy_core.judge_persistence import sqlite_judge_graph


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run, resume, or inspect the EACODE judge graph.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    _add_persistence_args(run)
    run.add_argument("--run-id", required=True)
    run.add_argument("--spec-id", required=True)
    run.add_argument("--policy", required=True)
    run.add_argument("--evidence", required=True)
    run.add_argument("--proposals", required=True)
    run.add_argument("--max-iterations", type=int, required=True)
    inspect = subparsers.add_parser("inspect")
    _add_persistence_args(inspect)
    resume = subparsers.add_parser("resume")
    _add_persistence_args(resume)
    resume.add_argument("--response", required=True, help="JSON human response object.")
    args = parser.parse_args(argv)
    config = {"configurable": {"thread_id": args.thread_id}}
    with sqlite_judge_graph(args.database) as graph:
        if args.command == "run":
            proposals = json.loads(Path(args.proposals).read_text(encoding="utf-8"))
            if not isinstance(proposals, list):
                raise ValueError("Proposals file must contain a JSON list.")
            result = graph.invoke(
                judge_input(
                    run_id=args.run_id,
                    thread_id=args.thread_id,
                    spec_id=args.spec_id,
                    policy_path=args.policy,
                    evidence_path=args.evidence,
                    proposals=proposals,
                    max_iterations=args.max_iterations,
                ),
                config,
            )
        elif args.command == "resume":
            response = json.loads(args.response)
            if not isinstance(response, dict):
                raise ValueError("Response must be a JSON object.")
            result = graph.invoke(Command(resume=response), config)
        else:
            snapshot = graph.get_state(config)
            result = {
                "values": snapshot.values,
                "next": list(snapshot.next),
            }
        print(json.dumps(result, indent=2, sort_keys=True, default=_json_default))
    return 0


def _add_persistence_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--database", required=True)
    parser.add_argument("--thread-id", required=True)


def _json_default(value: Any) -> Any:
    if hasattr(value, "value"):
        return {"value": value.value, "id": getattr(value, "id", None)}
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


if __name__ == "__main__":
    raise SystemExit(main())
