from pathlib import Path


def test_session12_task12_compliance_doc_exists():
    path = Path("docs/session12_task12_compliance.md")

    assert path.exists()

    content = path.read_text(encoding="utf-8")

    required = [
        "Session 12 Task 12 Compliance Audit",
        "Mandatory requirement mapping",
        "sample_transcript_complex.txt",
        "more than one search_budgets call",
        "calculate_estimate",
        "function_call_output",
        "call_id",
        "max_iterations",
        "Model variance explanation",
        "Not a model-quality benchmark",
        "Remaining gaps",
        "session-12/pre-work",
        "remote CI green is not proven",
    ]

    for fragment in required:
        assert fragment in content


def test_readme_names_session13_and_preserves_session12_history():
    readme = Path("README.md").read_text(encoding="utf-8")
    front_door, history = readme.split(
        "## Historical Session 12 agentic work",
        1,
    )

    assert "Current branch:" in front_door
    assert "gg-session-13/pre-work" in front_door
    assert "POST /api/v1/estimate/graph" in front_door

    assert "gg-session-12/pre-work" in history
    assert "Session 12 — hand-written agent loop" in history
    assert "docs/session12_task12_compliance.md" in history
