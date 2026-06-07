from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "estimador-cag" / "README.md"


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def test_session08_readme_documents_current_branch_and_stack() -> None:
    text = _readme()

    assert "## Session 08: pgvector semantic search" in text
    assert "gg-session-08-pgvector-search" in text
    assert "PostgreSQL plus pgvector" in text
    assert "POST /embeddings/ingest" in text
    assert "POST /search" in text


def test_session08_readme_documents_reproducible_compose_workflow() -> None:
    text = _readme()

    assert "docker compose up -d postgres redis ai_service" in text
    assert "docker compose exec -T ai_service uv run alembic upgrade head" in text
    assert "query_examples.py --dry-run" in text
    assert "query_examples.py --ingest-example-corpus" in text
    assert "output_examples.txt" in text


def test_session08_readme_explains_schema_and_retrieval_choices() -> None:
    text = _readme()

    for required in [
        "Why two tables",
        "Why JSONB metadata",
        "Why cosine distance",
        "Why no vector index yet",
        "Out-of-domain queries still return nearest neighbors",
    ]:
        assert required in text


def test_session08_readme_documents_validation_and_security() -> None:
    text = _readme()

    assert "OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q" in text
    assert "SESSION08_DB_INTEGRATION=1" in text
    assert "Never commit `.env`, real API keys" in text
