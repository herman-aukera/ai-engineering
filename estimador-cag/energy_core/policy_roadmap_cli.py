from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from energy_core.policy_roadmap import (
    build_policy_roadmap,
    format_policy_roadmap_markdown,
    format_policy_roadmap_text,
)

DEFAULT_POLICY = Path(".energy/specs/0001-energy-policy-ledger/energy-policy.yaml")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report policy-only constraints and future enforcement roadmap."
    )
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args(argv)

    roadmap = build_policy_roadmap(_resolve_path(Path(args.policy)))
    print(_format(roadmap, args.format))

    if args.fail_on_incomplete and not roadmap["complete"]:
        return 1
    return 0


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    project_relative = PROJECT_ROOT / path
    if project_relative.exists():
        return project_relative
    return path


def _format(roadmap: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(roadmap, indent=2, sort_keys=True)
    if output_format == "markdown":
        return format_policy_roadmap_markdown(roadmap)
    return format_policy_roadmap_text(roadmap)


if __name__ == "__main__":
    raise SystemExit(main())
