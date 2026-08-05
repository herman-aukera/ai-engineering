"""Run the bounded DeepSeek quality benchmark for Energy Aware Chat.

This script is a manual evidence command, not a normal CI command. It writes a
benchmark result and reviewer report that can later be copied into the release
claim evidence packet after human review.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.energy_chat.benchmark import run_deepseek_energy_benchmark  # noqa: E402
from app.energy_chat.contracts import DeepSeekBenchmarkRequest  # noqa: E402
from app.energy_chat.deepseek_quality_claim import (  # noqa: E402
    build_deepseek_quality_evidence,
    render_deepseek_quality_markdown,
)

DEFAULT_CASES_PATH = PROJECT_ROOT / "evals" / "energy_chat" / "deepseek_quality_cases.json"
DEFAULT_RESULT_PATH = (
    PROJECT_ROOT / "evals" / "energy_chat" / "deepseek_quality_benchmark_result.json"
)
DEFAULT_REPORT_PATH = PROJECT_ROOT / "docs" / "energy_aware_chat_deepseek_quality_benchmark.md"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the DeepSeek quality benchmark and write evidence files."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    request = DeepSeekBenchmarkRequest.model_validate_json(
        args.cases.read_text(encoding="utf-8")
    )
    benchmark = run_deepseek_energy_benchmark(request)
    evidence = build_deepseek_quality_evidence(
        benchmark,
        report_path=str(args.report.relative_to(PROJECT_ROOT)),
        live_provider_run=True,
    )

    args.result.write_text(
        json.dumps(benchmark.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    args.report.write_text(
        render_deepseek_quality_markdown(benchmark, evidence),
        encoding="utf-8",
    )

    print(f"Wrote {args.result.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {args.report.relative_to(PROJECT_ROOT)}")
    print(json.dumps(evidence.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
