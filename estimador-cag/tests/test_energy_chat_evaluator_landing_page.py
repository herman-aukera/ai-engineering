from pathlib import Path

LANDING_PAGE = Path("docs/energy_aware_chat_evaluator_landing_page.md")


def test_energy_chat_evaluator_landing_page_exists() -> None:
    assert LANDING_PAGE.exists()


def test_energy_chat_evaluator_landing_page_points_to_browser_and_streamlit_paths() -> None:
    text = LANDING_PAGE.read_text(encoding="utf-8")

    assert "/energy-chat/demo" in text
    assert "energy_chat_streamlit_app.py" in text
    assert "ESTIMADOR_BACKEND_URL=https://<codespace-8000-url>" in text


def test_energy_chat_evaluator_landing_page_lists_core_routes() -> None:
    text = LANDING_PAGE.read_text(encoding="utf-8")

    required_routes = [
        "POST /energy-chat/rag/search",
        "POST /energy-chat/chat",
        "POST /energy-chat/chat/live",
        "GET  /energy-chat/benchmark/fixed",
        "GET  /energy-chat/benchmark/fixed/report",
    ]
    for route in required_routes:
        assert route in text


def test_energy_chat_evaluator_landing_page_preserves_claim_boundaries() -> None:
    text = LANDING_PAGE.read_text(encoding="utf-8")

    assert "measurement_only_no_quality_claim" in text
    assert "Allowed claims" in text
    assert "Forbidden" in text
    assert "production ready" in text
    assert "quality improvement" in text
    assert "frontier models" in text


def test_energy_chat_evaluator_landing_page_documents_execution_audit() -> None:
    text = LANDING_PAGE.read_text(encoding="utf-8")

    assert "provider_draft_calls = 1" in text
    assert "critic_llm_calls = 0" in text
    assert "repair_llm_calls = 0" in text
    assert "does not run six hidden model calls" in text


def test_energy_chat_evaluator_landing_page_links_benchmark_evidence_files() -> None:
    text = LANDING_PAGE.read_text(encoding="utf-8")

    assert "evals/energy_chat/fixed_benchmark_cases.jsonl" in text
    assert "evals/energy_chat/fixed_benchmark_result.json" in text
    assert "docs/energy_aware_chat_fixed_benchmark_report.md" in text
