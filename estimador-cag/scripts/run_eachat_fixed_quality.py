"""Write deterministic fixed-corpus quality evidence for CI and reviewers."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.energy_chat.fixed_benchmark import (
    render_fixed_benchmark_markdown,
    run_fixed_benchmark,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default="/tmp/eachat-fixed-quality.json")
    parser.add_argument("--markdown", default="/tmp/eachat-fixed-quality.md")
    parser.add_argument("--run-id", default="eachat-fixed-quality-ci")
    args = parser.parse_args()

    result = run_fixed_benchmark(run_id=args.run_id)
    if not result.quality_claim_allowed:
        raise RuntimeError(
            "Fixed corpus did not prove bounded deterministic energy reduction"
        )
    Path(args.json).write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )
    Path(args.markdown).write_text(
        render_fixed_benchmark_markdown(result),
        encoding="utf-8",
    )
    print(
        "EACHAT_FIXED_QUALITY_OK "
        f"mean_delta={result.average_energy_delta_after_repair} "
        f"hard_reject_exposures={result.accepted_hard_reject_exposures}"
    )


if __name__ == "__main__":
    main()
