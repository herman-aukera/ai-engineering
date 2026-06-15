#!/usr/bin/env python3
"""Render the Energy Aware Chat closeout pack."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.energy_chat.closeout_pack import (  # noqa: E402
    build_energy_chat_closeout_pack,
    render_energy_chat_closeout_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a Markdown closeout pack for Energy Aware Chat."
    )
    parser.add_argument(
        "--project-root",
        default=str(ROOT),
        help="Path to the estimador-cag project root.",
    )
    parser.add_argument(
        "--output",
        default="/tmp/energy_aware_chat_closeout_pack.md",
        help="Output Markdown path. Relative paths are resolved from project root.",
    )
    parser.add_argument(
        "--fail-on-incomplete",
        action="store_true",
        help="Exit non-zero if the closeout pack is incomplete.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path

    pack = build_energy_chat_closeout_pack(project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_energy_chat_closeout_markdown(pack), encoding="utf-8")
    print(f"Wrote {output_path}")

    if args.fail_on_incomplete and not pack.complete:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
