"""
Pure helper contracts for the optional Session 11 Quality Lab.

This module intentionally has no Streamlit dependency so deterministic CI can
validate the metrics/report transformation without launching a browser UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

METRIC_COLUMNS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]

OFFICIAL_RAGAS_PROFILE = "ragas==0.1.21 with datasets and LangChain OpenAI packages"


PROVIDER_STATUS_ROWS = [
    {
        "provider": "openai",
        "role": "official_baseline",
        "dry_run_supported": True,
        "live_status": "completed",
        "notes": "Official Session 11 baseline with OpenAI chat judge and text-embedding-3-small.",
    },
    {
        "provider": "deepseek",
        "role": "comparison_judge",
        "dry_run_supported": True,
        "live_status": "blocked_by_ragas_multi_completion_request",
        "notes": "Dry-run is wired; live comparison needs a judge path that avoids multi-completion requests.",
    },
    {
        "provider": "kimi",
        "role": "comparison_judge",
        "dry_run_supported": True,
        "live_status": "blocked_by_ragas_multi_completion_request",
        "notes": "Dry-run is wired; live comparison needs a judge path that avoids multi-completion requests.",
    },
]


def load_json_payload(path: Path) -> dict[str, Any]:
    """Load a committed JSON evaluation artifact."""

    return json.loads(path.read_text())


def _score(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def compute_metric_averages(records: list[dict[str, Any]]) -> dict[str, float]:
    """Compute mean RAGAS metrics for a list of per-query records."""

    if not records:
        return {metric: 0.0 for metric in METRIC_COLUMNS}

    return {
        metric: sum(_score(record.get(metric)) for record in records) / len(records)
        for metric in METRIC_COLUMNS
    }


def build_metric_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build UI-ready rows for five query metrics plus an average row."""

    records = payload.get("records") or []
    rows: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        rows.append(
            {
                "query": f"Q{index}",
                "faithfulness": round(_score(record.get("faithfulness")), 3),
                "answer_relevancy": round(_score(record.get("answer_relevancy")), 3),
                "context_precision": round(_score(record.get("context_precision")), 3),
                "context_recall": round(_score(record.get("context_recall")), 3),
            }
        )

    averages = compute_metric_averages(records)
    rows.append(
        {
            "query": "average",
            "faithfulness": round(averages["faithfulness"], 3),
            "answer_relevancy": round(averages["answer_relevancy"], 3),
            "context_precision": round(averages["context_precision"], 3),
            "context_recall": round(averages["context_recall"], 3),
        }
    )

    return rows


def build_provider_status_rows() -> list[dict[str, Any]]:
    """Return provider status rows for the optional Quality Lab UI."""

    return [dict(row) for row in PROVIDER_STATUS_ROWS]
