from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAYLOADS = ROOT / "demo_payloads" / "energy_chat"

REVIEWER_INDEX = (DOCS / "energy_aware_chat_reviewer_index.md").read_text(encoding="utf-8")
API_SMOKE_GUIDE = (DOCS / "energy_aware_chat_api_smoke_guide.md").read_text(encoding="utf-8")
RESULTS_TEMPLATE = (DOCS / "energy_aware_chat_demo_results_template.md").read_text(encoding="utf-8")
LIVE_READINESS = (DOCS / "energy_aware_chat_live_demo_readiness.md").read_text(encoding="utf-8")


def test_reviewer_index_points_to_core_demo_artifacts() -> None:
    required_paths = [
        "docs/energy_aware_chat_demo.md",
        "docs/energy_aware_chat_live_demo_readiness.md",
        "docs/energy_aware_chat_api_smoke_guide.md",
        "docs/energy_aware_chat_demo_results_template.md",
        "docs/energy_aware_chat_final_project_delivery_plan.md",
        "docs/energy_aware_chat_repository_readiness.md",
        "docs/energy_aware_chat_session17_backlog.md",
    ]

    for path in required_paths:
        assert path in REVIEWER_INDEX


def test_reviewer_index_preserves_strategy_and_non_claims() -> None:
    assert "gg-finalproject-energy-aware-chat" in REVIEWER_INDEX
    assert "herman-aukera/energy-aware-chat" in REVIEWER_INDEX
    assert "measurement_only_no_quality_claim" in REVIEWER_INDEX
    assert "Do not claim" in REVIEWER_INDEX
    assert "RAG grounding" in REVIEWER_INDEX
    assert "Quality improvement over DeepSeek" in REVIEWER_INDEX


def test_api_smoke_guide_uses_committed_payloads_and_exact_paths() -> None:
    expected_payloads = [
        "evaluate_accept.json",
        "evaluate_repair_once.json",
        "source_needed_project.json",
        "evidence_bundle_project.json",
        "benchmark_measurement.json",
    ]
    expected_routes = [
        "/energy-chat/evaluate",
        "/energy-chat/evaluate/repair-once",
        "/energy-chat/source-needed",
        "/energy-chat/evidence/bundle",
    ]

    for payload in expected_payloads:
        assert (PAYLOADS / payload).exists()
        assert f"demo_payloads/energy_chat/{payload}" in API_SMOKE_GUIDE

    for route in expected_routes:
        assert route in API_SMOKE_GUIDE


def test_demo_results_template_requires_local_and_ci_proof() -> None:
    assert "bash scripts/validate_energy_chat.sh" in RESULTS_TEMPLATE
    assert "bash estimador-cag/scripts/check_energy_chat_ci.sh" in RESULTS_TEMPLATE
    assert "Energy Aware Chat CI" in RESULTS_TEMPLATE
    assert "Working tree" in RESULTS_TEMPLATE
    assert "clean" in RESULTS_TEMPLATE


def test_demo_results_template_preserves_open_backlog_and_claim_boundary() -> None:
    assert "measurement_only_no_quality_claim" in RESULTS_TEMPLATE
    assert "Open backlog after demo" in RESULTS_TEMPLATE
    assert "RAG grounding" in RESULTS_TEMPLATE
    assert "Agent layer" in RESULTS_TEMPLATE
    assert "Standalone repo" in RESULTS_TEMPLATE


def test_live_demo_readiness_mentions_streamlit_and_no_fake_claims() -> None:
    assert "energy_chat_streamlit_app.py" in LIVE_READINESS
    assert "Streamlit" in LIVE_READINESS
    assert "measurement_only_no_quality_claim" in LIVE_READINESS
    assert "No production readiness claim" in LIVE_READINESS
