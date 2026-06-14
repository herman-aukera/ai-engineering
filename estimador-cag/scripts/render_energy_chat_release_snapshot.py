#!/usr/bin/env python3
"""Render an Energy Aware Chat release snapshot Markdown file."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.energy_chat.release_snapshot import (  # noqa: E402
    build_release_snapshot,
    build_release_snapshot_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a Markdown release snapshot for Energy Aware Chat."
    )
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--focused-tests", required=True, type=int)
    parser.add_argument("--full-tests", required=True, type=int)
    parser.add_argument("--local-ref", required=True)
    parser.add_argument("--ci-ref", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = build_release_snapshot(
        commit_sha=args.commit_sha,
        focused_tests=args.focused_tests,
        full_tests=args.full_tests,
        local_status="green",
        ci_status="green",
        local_ref=args.local_ref,
        ci_ref=args.ci_ref,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_release_snapshot_markdown(snapshot), encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
