import json
from pathlib import Path

from evals.session11_generation.quality_lab_helpers_s11 import (
    build_metric_rows,
    build_provider_status_rows,
    compute_metric_averages,
)


RESULTS_PATH = Path("evals/session11_generation/ragas_results_openai_s11.json")


def test_quality_lab_metric_rows_include_five_queries_and_average():
    payload = json.loads(RESULTS_PATH.read_text())

    rows = build_metric_rows(payload)

    assert len(rows) == 6
    assert rows[0]["query"] == "Q1"
    assert rows[-1] == {
        "query": "average",
        "faithfulness": 1.0,
        "answer_relevancy": 0.322,
        "context_precision": 1.0,
        "context_recall": 1.0,
    }


def test_quality_lab_metric_averages_are_stable_for_committed_baseline():
    payload = json.loads(RESULTS_PATH.read_text())

    averages = compute_metric_averages(payload["records"])

    assert averages["faithfulness"] == 1.0
    assert round(averages["answer_relevancy"], 3) == 0.322
    assert round(averages["context_precision"], 3) == 1.0
    assert averages["context_recall"] == 1.0


def test_quality_lab_provider_status_distinguishes_official_and_comparison_paths():
    rows = build_provider_status_rows()

    assert [row["provider"] for row in rows] == ["openai", "deepseek", "kimi"]
    assert rows[0]["role"] == "official_baseline"
    assert rows[0]["live_status"] == "completed"
    assert rows[1]["role"] == "comparison_judge"
    assert rows[1]["live_status"] == "blocked_by_ragas_multi_completion_request"
    assert rows[2]["role"] == "comparison_judge"
    assert rows[2]["dry_run_supported"] is True
