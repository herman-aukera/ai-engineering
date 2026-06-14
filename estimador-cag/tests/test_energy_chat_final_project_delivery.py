from pathlib import Path

DELIVERY_PLAN = Path("docs/energy_aware_chat_final_project_delivery_plan.md").read_text(
    encoding="utf-8"
)
DEMO_WALKTHROUGH = Path("docs/energy_aware_chat_demo_walkthrough.md").read_text(
    encoding="utf-8"
)
SESSION17_BACKLOG = Path("docs/energy_aware_chat_session17_backlog.md").read_text(
    encoding="utf-8"
)
EXPORT_MANIFEST = Path("scripts/export_energy_chat_manifest.sh").read_text(
    encoding="utf-8"
)


def test_delivery_plan_preserves_product_thesis_and_claim_boundaries() -> None:
    assert "constraint-governed assistant answer evaluator" in DELIVERY_PLAN
    assert "measurement-only benchmark harness" in DELIVERY_PLAN
    assert "DeepSeek quality improvement" in DELIVERY_PLAN
    assert "measurement_only_no_quality_claim" in DELIVERY_PLAN
    assert "bash scripts/validate_energy_chat.sh" in DELIVERY_PLAN
    assert "bash scripts/check_energy_chat_ci.sh" in DELIVERY_PLAN


def test_demo_walkthrough_covers_main_reviewer_paths() -> None:
    required_sections = [
        "Demo 1: accepted answer",
        "Demo 2: repairable answer",
        "Demo 3: evidence bundle",
        "Demo 4: benchmark harness",
        "measurement_only_no_quality_claim",
    ]

    for required_section in required_sections:
        assert required_section in DEMO_WALKTHROUGH


def test_session17_backlog_prevents_random_scope_creep() -> None:
    assert "controlled intake list" in SESSION17_BACKLOG
    assert "Reject as scope creep" in SESSION17_BACKLOG
    assert "Project-source RAG" in SESSION17_BACKLOG
    assert "Fixed eval dataset" in SESSION17_BACKLOG
    assert "Session 17" in SESSION17_BACKLOG


def test_export_manifest_names_future_repo_and_required_paths() -> None:
    required_fragments = [
        "herman-aukera/energy-aware-chat",
        "EACHAT",
        "app/energy_chat/",
        "energy_chat_streamlit_app.py",
        "docs/energy_aware_chat_final_project_delivery_plan.md",
        "docs/energy_aware_chat_demo_walkthrough.md",
        "docs/energy_aware_chat_session17_backlog.md",
        "docs/energy_aware_chat_mvp_upgrade.md",
        "scripts/validate_energy_chat.sh",
        "scripts/check_energy_chat_ci.sh",
        "tests/test_energy_chat_*.py",
        "measurement_only_no_quality_claim",
    ]

    for required_fragment in required_fragments:
        assert required_fragment in EXPORT_MANIFEST


def test_export_manifest_keeps_non_claimed_layers_explicit() -> None:
    assert "production readiness" in EXPORT_MANIFEST
    assert "public deployment is live" in EXPORT_MANIFEST
    assert "quality improvement over DeepSeek" in EXPORT_MANIFEST
    assert "vector database RAG" in EXPORT_MANIFEST
