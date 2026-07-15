from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "estimador-cag" / "README.md"


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _normalized_readme() -> str:
    return " ".join(_readme().split())


def test_project_readme_documents_current_session13_and_history() -> None:
    text = _readme()
    front_door, remaining = text.split(
        "## Historical Session 12 agentic work",
        1,
    )
    session12_history, session10_history = remaining.split(
        "## Historical Session 10 retrieval background",
        1,
    )

    assert "gg-session-13/pre-work" in front_door
    assert "POST /api/v1/estimate/graph" in front_door
    assert "docs/session13_task13_compliance.md" in front_door

    assert "gg-session-12/pre-work" in session12_history
    assert "docs/session12_agentic_handoff.md" in session12_history

    assert "app/embedding_pipeline/fusion.py" in session10_history
    assert "app/embedding_pipeline/reranker.py" in session10_history
    assert "POST /search" in session10_history


def test_project_readme_documents_abcd_retrieval_evaluation() -> None:
    text = _readme()

    assert "| A | Vector | No |" in text
    assert "| B | Hybrid | No |" in text
    assert "| C | Vector | Yes |" in text
    assert "| D | Hybrid | Yes |" in text
    assert "uv run python -m evals.session10_retrieval.run" in text


def test_project_readme_explains_metric_interpretation_and_limitations() -> None:
    text = _normalized_readme()

    assert "result budget precision@5" in text
    assert "unique budget precision@5" in text
    assert "corpus has only four budgets, eight component" in text
    assert "does not prove hybrid retrieval or reranking superiority" in text


def test_project_readme_documents_validation_provider_policy_and_history() -> None:
    text = _normalized_readme()

    assert (
        "OPENAI_API_KEY=test DEEPSEEK_API_KEY=test "
        "KIMI_API_KEY=test uv run pytest -q"
        in text
    )
    assert "prefer DeepSeek first" in text
    assert "Kimi only as fallback or comparison" in text
    assert "docs/HISTORICAL_SESSIONS.md" in text
