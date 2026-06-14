from pathlib import Path

DOC = Path("docs/energy_aware_chat_demo.md").read_text(encoding="utf-8")


def test_energy_chat_demo_doc_lists_current_layers() -> None:
    assert "Deterministic evaluator core" in DOC
    assert "FastAPI `/energy-chat/evaluate`" in DOC
    assert "Streamlit Energy Card demo" in DOC
    assert "Measurement-only benchmark harness" in DOC
    assert "Benchmark report writer" in DOC


def test_energy_chat_demo_doc_preserves_claim_boundaries() -> None:
    assert "No RAG grounding yet" in DOC
    assert "No DeepSeek improvement claim" in DOC
    assert "measurement_only_no_quality_claim" in DOC


def test_energy_chat_demo_doc_explains_validation_and_demo_commands() -> None:
    assert "bash scripts/validate_energy_chat.sh" in DOC
    assert "uv run uvicorn app.main:app" in DOC
    assert "streamlit run energy_chat_streamlit_app.py" in DOC
    assert "POST /energy-chat/benchmark/deepseek-energy-aware" in DOC
