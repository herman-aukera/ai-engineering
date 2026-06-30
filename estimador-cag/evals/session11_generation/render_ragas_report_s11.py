"""
Render the Session 11 RAGAS baseline report.

The report is deterministic: it reads committed live RAGAS JSON results and
produces a Markdown baseline table with caveats and reproduction commands.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RESULTS_PATH = Path("evals/session11_generation/ragas_results_openai_s11.json")
REPORT_PATH = Path("evals/session11_generation/RAGAS_BASELINE_S11.md")

METRIC_COLUMNS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]


def _score(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _fmt(value: float) -> str:
    return f"{value:.3f}"


def compute_metric_averages(records: list[dict[str, Any]]) -> dict[str, float]:
    if not records:
        return {
            metric: 0.0
            for metric in METRIC_COLUMNS
        }

    return {
        metric: sum(_score(record.get(metric)) for record in records) / len(records)
        for metric in METRIC_COLUMNS
    }


def render_markdown_report(payload: dict[str, Any]) -> str:
    records = payload["records"]
    averages = compute_metric_averages(records)

    lines = [
        "# Session 11 RAGAS Baseline",
        "",
        "Status: committed live OpenAI baseline",
        "",
        "## Scope",
        "",
        "This report is the Session 11 generation-quality baseline. It uses the deterministic RAGAS sample contract derived from the Session 10 golden set and the committed live OpenAI RAGAS result JSON.",
        "",
        "Official baseline configuration:",
        "",
        f"- Judge provider: {payload['judge_provider']}",
        f"- Official baseline: {payload['official_baseline']}",
        f"- Chat judge model: {payload['chat_judge_model']}",
        f"- Embedding model: {payload['embedding_model']}",
        f"- Sample count: {payload['sample_count']}",
        "- Isolated scorer profile: ragas==0.1.21, datasets==5.0.0, langchain-community==0.2.19, langchain-openai",
        "",
        "## Metrics table",
        "",
        "| query | faithfulness | answer_relevancy | context_precision | context_recall |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for index, record in enumerate(records, start=1):
        lines.append(
            "| Q{index} | {faithfulness} | {answer_relevancy} | {context_precision} | {context_recall} |".format(
                index=index,
                faithfulness=_fmt(_score(record.get("faithfulness"))),
                answer_relevancy=_fmt(_score(record.get("answer_relevancy"))),
                context_precision=_fmt(_score(record.get("context_precision"))),
                context_recall=_fmt(_score(record.get("context_recall"))),
            )
        )

    lines.append(
        "| average | {faithfulness} | {answer_relevancy} | {context_precision} | {context_recall} |".format(
            faithfulness=_fmt(averages["faithfulness"]),
            answer_relevancy=_fmt(averages["answer_relevancy"]),
            context_precision=_fmt(averages["context_precision"]),
            context_recall=_fmt(averages["context_recall"]),
        )
    )

    lines.extend(
        [
            "",
            "## Citation verification summary",
            "",
            "- Line-level source references are part of the estimate schema.",
            "- Grounded lines require real source references.",
            "- Unsupported lines must be marked as insufficient/no-data instead of inventing hours.",
            "- The planted dangling citation demo verifies that a cited chunk id not present in the retrieved context is detected as a quality failure.",
            "",
            "Committed evidence:",
            "",
            "- `tests/test_session11_citation_verification.py`",
            "- `tests/test_session11_dangling_demo.py`",
            "- `scripts/demo_verify_citations_s11.py`",
            "- `evals/session11_generation/ragas_results_openai_s11.json`",
            "",
            "## Suspicious-number note",
            "",
            "The most suspicious result is that faithfulness, context precision, and context recall are all effectively perfect while answer_relevancy is much lower. This likely happens because the deterministic answer is tightly grounded in the retrieved source text, but its wording is short and component-centric rather than naturally answering the query as a user-facing estimate. The numbers should be treated as a baseline for the wired pipeline, not as proof of production-grade generation quality.",
            "",
            "## Known limitations",
            "",
            "- The corpus and golden set are small, so the metrics are course-scale baseline evidence.",
            "- DeepSeek and Kimi judge dry-runs are supported, but live comparison scoring hit provider API limits around multi-completion requests from the RAGAS/LangChain stack.",
            "- The official submitted baseline is OpenAI because the task requires OpenAI embeddings with `text-embedding-3-small`.",
            "",
            "## Reproduction commands",
            "",
            "Dry-run contract:",
            "",
            "    uv run python evals/session11_generation/run_ragas_s11.py --dry-run --judge-provider openai",
            "",
            "Live OpenAI baseline with isolated RAGAS profile:",
            "",
            "    uv run --no-project --with \"ragas==0.1.21\" --with \"datasets==5.0.0\" --with \"langchain-community==0.2.19\" --with \"langchain-openai\" python evals/session11_generation/run_ragas_s11.py --live --judge-provider openai --output-path evals/session11_generation/ragas_results_openai_s11.json",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    payload = json.loads(RESULTS_PATH.read_text())
    REPORT_PATH.write_text(render_markdown_report(payload).rstrip() + "\n")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
