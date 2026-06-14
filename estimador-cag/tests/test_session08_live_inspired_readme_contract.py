from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"


def test_session08_readme_identifies_live_inspired_learning_branch() -> None:
    text = README.read_text(encoding="utf-8")

    assert "gg-session-08-live-inspired-hardening" in text
    assert "post-live learning branch" in text
    assert "strict homework baseline" in text
    assert "not a teacher-code copy" in text


def test_session08_readme_separates_baseline_from_extra_mile_features() -> None:
    text = README.read_text(encoding="utf-8")

    assert "Baseline Session 08 deliverables" in text
    assert "Post-live extra-mile features" in text
    assert "HNSW cosine vector index" in text
    assert "metadata filters" in text
    assert "search metrics" in text
    assert "Streamlit search UI" in text
