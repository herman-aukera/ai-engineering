from pathlib import Path

README = Path("README.md")


def test_readme_documents_session08_search_quality_workflow() -> None:
    text = README.read_text(encoding="utf-8")

    assert "### Session 08 search-quality evaluation workflow" in text
    assert "evals/session08_search_quality/cases.jsonl" in text
    assert "evals/session08_search_quality/evaluator.py" in text
    assert "evals/session08_search_quality/capture.py" in text
    assert "uv run python -m evals.session08_search_quality.capture" in text
    assert "uv run python -m evals.session08_search_quality.evaluator" in text


def test_readme_documents_search_quality_safety_boundaries() -> None:
    text = README.read_text(encoding="utf-8")

    assert "No LLM judge" in text
    assert "No live provider call in tests" in text
    assert "No benchmark superiority claim" in text
    assert "not a Task 09 implementation claim" in text
    assert "captured responses should be reviewed before committing" in text


def test_readme_documents_capture_dry_run_before_live_capture() -> None:
    text = README.read_text(encoding="utf-8")

    dry_run_index = text.index("--dry-run")
    live_capture_index = text.index("--base-url http://localhost:8000")
    assert dry_run_index < live_capture_index
