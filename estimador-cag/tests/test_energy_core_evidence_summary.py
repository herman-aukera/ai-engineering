import json

from energy_core.evidence import read_evidence_records, summarize_evidence
from energy_core.reporter import format_evidence_markdown_report, format_evidence_summary


def test_evidence_summary_groups_records_by_status_and_type(tmp_path):
    evidence_path = tmp_path / "evidence.jsonl"
    records = [
        {
            "evidence_id": "ev-pytest-pass",
            "type": "pytest_output",
            "status": "pass",
            "summary": "tests passed",
            "trusted": True,
        },
        {
            "evidence_id": "ev-ruff-fail",
            "type": "lint_output",
            "status": "fail",
            "summary": "ruff failed",
            "trusted": True,
        },
        {
            "evidence_id": "ev-human-missing",
            "type": "human_approval",
            "status": "missing",
            "summary": "approval not provided",
            "trusted": False,
        },
        {
            "evidence_id": "ev-ci-conflict",
            "type": "ci_output",
            "status": "conflict",
            "summary": "local and CI disagree",
            "trusted": True,
        },
    ]
    evidence_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    summary = summarize_evidence(read_evidence_records(evidence_path))

    assert summary["total"] == 4
    assert summary["trusted"] == 3
    assert summary["not_trusted"] == 1
    assert summary["by_status"] == {"conflict": 1, "fail": 1, "missing": 1, "pass": 1}
    assert summary["by_type"] == {
        "ci_output": 1,
        "human_approval": 1,
        "lint_output": 1,
        "pytest_output": 1,
    }
    assert summary["failed_evidence"] == ["ev-ruff-fail"]
    assert summary["missing_evidence"] == ["ev-human-missing"]
    assert summary["conflicting_evidence"] == ["ev-ci-conflict"]


def test_evidence_summary_report_formats_are_human_readable():
    summary = {
        "total": 2,
        "by_status": {"fail": 1, "pass": 1},
        "by_type": {"pytest_output": 1, "secret_scan_output": 1},
        "trusted": 2,
        "not_trusted": 0,
        "failed_evidence": ["ev-secret-fail"],
        "missing_evidence": [],
        "conflicting_evidence": [],
    }

    text_report = format_evidence_summary(summary)
    markdown_report = format_evidence_markdown_report(summary)

    assert "Energy Aware Code Evidence Summary" in text_report
    assert "Total records: 2" in text_report
    assert "Failed evidence: ev-secret-fail" in text_report
    assert "# Energy Aware Code Evidence Summary" in markdown_report
    assert "- fail: 1" in markdown_report
    assert "- ev-secret-fail" in markdown_report
