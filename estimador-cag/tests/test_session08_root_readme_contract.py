from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_README = REPO_ROOT / "README.md"


def _readme() -> str:
    return ROOT_README.read_text(encoding="utf-8")


def _normalized_readme() -> str:
    return " ".join(_readme().split())


def test_root_readme_documents_current_session13_submission() -> None:
    text = _readme()
    front_door = text.split(
        "## Historical Session 10 retrieval work",
        1,
    )[0]

    assert "gg-session-13/pre-work" in front_door
    assert "Session 13 — agent orchestration with LangGraph" in front_door
    assert "estimador-cag/" in front_door
    assert "gg-session-10/pre-work" not in front_door


def test_root_readme_preserves_session10_measurement_runner() -> None:
    text = _readme()
    history = text.split(
        "## Historical Session 10 retrieval work",
        1,
    )[1]

    assert "gg-session-10/pre-work" in history
    assert "uv run python -m evals.session10_retrieval.run" in history
    assert "evals/session10_retrieval/results.json" in history
    assert "evals/session10_retrieval/REPORT.md" in history
    assert "A/B/C/D retrieval variants" in history


def test_root_readme_documents_bounded_historical_interpretation() -> None:
    text = _normalized_readme()

    assert "wiring and smoke evidence" in text
    assert (
        "not proof that hybrid search or reranking improves quality in production"
        in text
    )
    assert "result budget precision@5" in text
    assert "unique budget precision@5" in text


def test_root_readme_documents_provider_policy_and_security() -> None:
    text = _normalized_readme()

    assert "prefer DeepSeek first" in text
    assert "Kimi only as fallback or comparison" in text
    assert "Do not commit `.env`, real API keys" in text
