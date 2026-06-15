from __future__ import annotations

import argparse
import json
from pathlib import Path

from energy_core.acceptance_trace import (
    build_acceptance_trace,
    format_acceptance_trace_markdown,
    format_acceptance_trace_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Trace acceptance criteria to evidence, tests, and review surfaces."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--spec-dir", default=None)
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args(argv)

    trace = build_acceptance_trace(
        Path(args.project_root),
        spec_dir=Path(args.spec_dir) if args.spec_dir else None,
    )

    if args.format == "json":
        print(json.dumps(trace, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(format_acceptance_trace_markdown(trace))
    else:
        print(format_acceptance_trace_text(trace))

    if args.fail_on_incomplete and not trace["complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
