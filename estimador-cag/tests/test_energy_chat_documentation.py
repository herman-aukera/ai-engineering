from pathlib import Path

from app.energy_chat import build_release_snapshot, build_release_snapshot_markdown

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


def test_release_snapshot_helper_builds_markdown_from_gate_counts() -> None:
    snapshot = build_release_snapshot(
        commit_sha="abcdef1234567890",
        focused_tests=110,
        full_tests=368,
        local_status="green",
        ci_status="green",
        local_ref="local-proof",
        ci_ref="remote-proof",
    )

    markdown = build_release_snapshot_markdown(snapshot)

    assert snapshot.status == "green"
    assert snapshot.short_sha == "abcdef1"
    assert "# Energy Aware Chat release snapshot" in markdown
    assert "measurement_only_no_quality_claim" in markdown
    assert "local-proof" in markdown
    assert "remote-proof" in markdown
    assert "110 focused tests and 368 full tests passed" in markdown
