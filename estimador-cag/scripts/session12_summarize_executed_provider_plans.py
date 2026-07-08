"""
Summarize Session 12 executed provider-plan artifacts.

This script does not call live providers. It reads executed local artifacts and
writes a sanitized Markdown summary suitable for committing.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

PROVIDER_ORDER = {
    "deepseek": 0,
    "kimi": 1,
    "openai": 2,
}

TIER_ORDER = {
    "cheap": 0,
    "final": 1,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a sanitized summary for executed provider-plan artifacts.",
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--expected-count", type=int)
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a JSON object")
    return payload


def _artifact_row(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"{path} is missing result")

    estimate = result.get("estimate")
    if not isinstance(estimate, dict):
        raise ValueError(f"{path} is missing result.estimate")

    validation = result.get("validation")
    if not isinstance(validation, dict):
        validation = {}

    return {
        "provider": payload.get("provider"),
        "tier": payload.get("tier"),
        "model": payload.get("model"),
        "total_hours": estimate.get("total_hours"),
        "total_cost_eur": estimate.get("total_cost_eur"),
        "validation_valid": validation.get("valid"),
        "terminated": result.get("terminated"),
    }


def load_rows(input_dir: Path) -> list[dict[str, Any]]:
    paths = sorted(input_dir.glob("*_executed.json"))
    rows = [_artifact_row(path) for path in paths]
    return sorted(
        rows,
        key=lambda row: (
            PROVIDER_ORDER.get(str(row["provider"]), 99),
            TIER_ORDER.get(str(row["tier"]), 99),
            str(row["model"]),
        ),
    )


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Session 12 Executed Provider Plan Summary",
        "",
        "Scope: sanitized summary of live-provider plans executed through deterministic local tools.",
        "",
        "Evidence level: manual live-provider planning plus deterministic local tool execution.",
        "",
        "| Provider | Tier | Model | Total hours | Total cost EUR | Validation valid | Terminated |",
        "|---|---|---|---:|---:|---|---|",
    ]

    for row in rows:
        lines.append(
            "| {provider} | {tier} | {model} | {total_hours} | {total_cost_eur} | {validation_valid} | {terminated} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "Notes:",
            "- This file is a sanitized report, not a raw provider artifact.",
            "- Raw executed artifacts were kept outside the repository.",
            "- The executed artifacts were produced from live-provider plans.",
            "- The execution step itself used deterministic local tools.",
            "- This evidence does not claim remote CI green, browser UI proof, benchmark quality, or production readiness.",
        ]
    )

    return "\n".join(lines) + "\n"


def write_summary(
    *,
    input_dir: Path,
    output_file: Path,
    expected_count: int | None,
) -> Path:
    rows = load_rows(input_dir)

    if expected_count is not None and len(rows) != expected_count:
        raise ValueError(
            f"expected {expected_count} executed artifacts, found {len(rows)}"
        )

    if not rows:
        raise ValueError("no executed artifacts found")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(render_markdown(rows), encoding="utf-8")
    return output_file


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        written = write_summary(
            input_dir=Path(args.input_dir),
            output_file=Path(args.output_file),
            expected_count=args.expected_count,
        )
    except Exception as exc:
        print(f"failed: {exc}")
        return 2

    print(f"wrote {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
