from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_README = REPO_ROOT / "README.md"


def _readme() -> str:
    return ROOT_README.read_text(encoding="utf-8")


def test_root_readme_documents_session08_current_submission() -> None:
    text = _readme()

    assert "gg-session-08-pgvector-search" in text
    assert "Session 08 — pgvector semantic search baseline" in text
    assert "estimador-cag/" in text


def test_root_readme_documents_session08_runtime_and_outputs() -> None:
    text = _readme()

    assert "docker compose up -d postgres redis ai_service" in text
    assert "query_examples.py --dry-run" in text
    assert "query_examples.py --ingest-example-corpus" in text
    assert "output_examples.txt" in text


def test_root_readme_documents_schema_and_limitations() -> None:
    text = _readme()

    assert "documents" in text
    assert "chunks" in text
    assert "JSONB" in text
    assert "cosine distance" in text
    assert "without HNSW or IVFFlat" in text
    assert "Out-of-domain queries still return nearest neighbors" in text


def test_root_readme_documents_extra_mile_plan() -> None:
    text = _readme()

    assert "Fix /api/v1/estimate 503" in text
    assert "metadata filters" in text
    assert "search metrics dashboard" in text
    assert "HNSW vector_cosine_ops index" in text
    assert "Streamlit search UI" in text
