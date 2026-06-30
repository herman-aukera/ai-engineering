"""
Manual Session 11 RAGAS runner.

This module is intentionally safe for CI:
- dry-run mode validates the deterministic RAGAS input contract;
- live mode requires OPENAI_API_KEY and imports optional RAGAS dependencies only then.

Manual live example:
    uv run python evals/session11_generation/run_ragas_s11.py --live
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

OFFICIAL_PROVIDER = "openai"
PROVIDERS = {
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "model_env": "OPENAI_RAGAS_JUDGE_MODEL",
        "default_model": "gpt-4o-mini",
        "base_url_env": "OPENAI_BASE_URL",
        "default_base_url": None,
        "official": True,
    },
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "model_env": "DEEPSEEK_RAGAS_JUDGE_MODEL",
        "default_model": "deepseek-chat",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "default_base_url": "https://api.deepseek.com",
        "official": False,
    },
    "kimi": {
        "env_key": "KIMI_API_KEY",
        "model_env": "KIMI_RAGAS_JUDGE_MODEL",
        "default_model": "moonshot-v1-8k",
        "base_url_env": "KIMI_BASE_URL",
        "default_base_url": "https://api.moonshot.ai/v1",
        "official": False,
    },
}
CHAT_JUDGE_MODEL = PROVIDERS[OFFICIAL_PROVIDER]["default_model"]
EMBEDDING_MODEL = "text-embedding-3-small"
METRICS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]

DEFAULT_SAMPLE_PATH = Path("evals/session11_generation/ragas_sample_s11.json")
DEFAULT_OUTPUT_PATH = Path("evals/session11_generation/ragas_results_s11.json")


def load_sample_contract(path: Path) -> dict[str, Any]:
    """Load the deterministic Session 11 RAGAS sample contract."""

    return json.loads(path.read_text())


def build_ragas_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Convert the deterministic sample contract into RAGAS input rows.

    RAGAS expects question, answer, contexts, and ground_truth.
    Metadata is intentionally excluded from live scoring rows.
    """

    rows = []

    for sample in payload["samples"]:
        rows.append(
            {
                "question": sample["question"],
                "answer": sample["answer"],
                "contexts": sample["contexts"],
                "ground_truth": sample["ground_truth"],
            }
        )

    return rows


def build_dry_run_summary(
    rows: list[dict[str, Any]],
    output_path: Path,
    judge_provider: str = OFFICIAL_PROVIDER,
) -> dict[str, Any]:
    """Return a deterministic summary without importing or calling RAGAS."""

    provider_config = PROVIDERS[judge_provider]
    chat_judge_model = os.environ.get(
        provider_config["model_env"],
        provider_config["default_model"],
    )

    return {
        "mode": "dry_run",
        "sample_count": len(rows),
        "metrics": METRICS,
        "judge_provider": judge_provider,
        "official_baseline": provider_config["official"],
        "chat_judge_model": chat_judge_model,
        "embedding_model": EMBEDDING_MODEL,
        "output_path": str(output_path),
        "requires_env": [provider_config["env_key"]],
    }


def _result_to_records(result: Any) -> list[dict[str, Any]]:
    """Convert common RAGAS result shapes to JSON-serializable records."""

    if hasattr(result, "to_pandas"):
        return result.to_pandas().to_dict(orient="records")

    if hasattr(result, "scores"):
        scores = result.scores
        if isinstance(scores, list):
            return scores

    if isinstance(result, dict):
        return [result]

    raise TypeError(f"Unsupported RAGAS result shape: {type(result)!r}")


def run_live_ragas(
    rows: list[dict[str, Any]],
    output_path: Path,
    judge_provider: str = OFFICIAL_PROVIDER,
) -> dict[str, Any]:
    """Run live RAGAS scoring with OpenAI-backed judge and embeddings."""

    provider_config = PROVIDERS[judge_provider]
    provider_api_key = os.environ.get(provider_config["env_key"])
    if not provider_api_key:
        raise RuntimeError(
            f'{provider_config["env_key"]} is required for --live RAGAS scoring.'
        )

    chat_judge_model = os.environ.get(
        provider_config["model_env"],
        provider_config["default_model"],
    )
    base_url = os.environ.get(
        provider_config["base_url_env"],
        provider_config["default_base_url"],
    )

    try:
        from datasets import Dataset
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas import evaluate
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Missing or incompatible optional RAGAS dependencies. Install or repair manually, for example: "
            "uv add ragas datasets langchain-openai. Original import error: "
            f"{exc!r}"
        ) from exc

    dataset = Dataset.from_list(rows)
    chat_kwargs = {
        "model": chat_judge_model,
        "api_key": provider_api_key,
    }
    if base_url:
        chat_kwargs["base_url"] = base_url

    evaluator_llm = LangchainLLMWrapper(ChatOpenAI(**chat_kwargs))
    evaluator_embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )

    records = _result_to_records(result)

    payload = {
        "mode": "live",
        "sample_count": len(rows),
        "metrics": METRICS,
        "judge_provider": judge_provider,
        "official_baseline": provider_config["official"],
        "chat_judge_model": chat_judge_model,
        "embedding_model": EMBEDDING_MODEL,
        "records": records,
    }

    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample-path",
        type=Path,
        default=DEFAULT_SAMPLE_PATH,
        help="Path to deterministic RAGAS sample contract JSON.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path where live RAGAS result JSON should be written.",
    )
    parser.add_argument(
        "--judge-provider",
        choices=sorted(PROVIDERS),
        default=OFFICIAL_PROVIDER,
        help="Judge provider for live RAGAS scoring or dry-run summary.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize the RAGAS contract without live scoring.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live RAGAS scoring. Requires OPENAI_API_KEY and optional dependencies.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.dry_run and args.live:
        print("Use either --dry-run or --live, not both.", file=sys.stderr)
        return 2

    payload = load_sample_contract(args.sample_path)
    rows = build_ragas_rows(payload)

    if args.live:
        try:
            live_payload = run_live_ragas(
                rows,
                args.output_path,
                judge_provider=args.judge_provider,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        print(json.dumps(live_payload, indent=2, sort_keys=True))
        return 0

    summary = build_dry_run_summary(
        rows,
        args.output_path,
        judge_provider=args.judge_provider,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
