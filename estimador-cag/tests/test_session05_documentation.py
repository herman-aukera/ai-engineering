from pathlib import Path

README = Path("README.md").read_text(encoding="utf-8")


def test_readme_documents_session05_memory_and_attachment_flow():
    assert "Session 05" in README
    assert "POST /sessions" in README
    assert "POST /sessions/{session_id}/estimate" in README
    assert "project_metadata" in README
    assert "ConversationHistory" in README
    assert "sliding window" in README.lower()
    assert "multipart/form-data" in README
    assert "pypdf" in README
    assert "python-docx" in README


def test_readme_documents_streamlit_session05_usage():
    assert "New conversation" in README
    assert "Project metadata" in README
    assert "PDF" in README
    assert "DOCX" in README
    assert "ESTIMADOR_BACKEND_URL" in README
