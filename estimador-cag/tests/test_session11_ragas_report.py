import json
from pathlib import Path

from evals.session11_generation.render_ragas_report_s11 import (
    METRIC_COLUMNS,
    compute_metric_averages,
    render_markdown_report,
)

RESULTS_PATH = Path("evals/session11_generation/ragas_results_openai_s11.json")
REPORT_PATH = Path("evals/session11_generation/RAGAS_BASELINE_S11.md")


def test_ragas_report_renderer_computes_average_row():
    payload = json.loads(RESULTS_PATH.read_text())
    averages = compute_metric_averages(payload["records"])

    assert set(averages) == set(METRIC_COLUMNS)
    assert averages["faithfulness"] == 1.0
    assert round(averages["answer_relevancy"], 3) == 0.322
    assert round(averages["context_precision"], 3) == 1.0
    assert averages["context_recall"] == 1.0


def test_ragas_report_renderer_outputs_required_sections():
    payload = json.loads(RESULTS_PATH.read_text())
    markdown = render_markdown_report(payload)

    assert "# Session 11 RAGAS Baseline" in markdown
    assert "## Metrics table" in markdown
    assert "## Citation verification summary" in markdown
    assert "## Suspicious-number note" in markdown
    assert "## Reproduction commands" in markdown
    assert "ragas==0.1.21" in markdown
    assert "text-embedding-3-small" in markdown
    assert "gpt-4o-mini" in markdown


def test_ragas_report_file_exists_with_five_queries_and_average():
    report = REPORT_PATH.read_text()

    assert "| query | faithfulness | answer_relevancy | context_precision | context_recall |" in report
    assert "| average |" in report

    query_rows = [
        line
        for line in report.splitlines()
        if line.startswith("| Q")
    ]

    assert len(query_rows) == 5
    assert "answer_relevancy is much lower" in report
