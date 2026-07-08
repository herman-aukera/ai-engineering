from pathlib import Path


def test_session12_handoff_doc_exists_and_names_evidence_files():
    handoff = Path("docs/session12_agentic_handoff.md")

    assert handoff.exists()

    content = handoff.read_text(encoding="utf-8")

    required_fragments = [
        "Session 12 Agentic Handoff",
        "session12_live_provider_matrix_summary.md",
        "session12_executed_provider_plan_summary.md",
        "scripts/session12_live_provider_smoke.py",
        "scripts/session12_execute_provider_plan.py",
        "scripts/session12_summarize_executed_provider_plans.py",
        "manual live-provider planning",
        "deterministic local tool execution",
        "does not claim remote CI green",
        "does not claim browser UI proof",
    ]

    for fragment in required_fragments:
        assert fragment in content


def test_readme_points_to_session12_handoff_doc():
    readme = Path("README.md")
    content = readme.read_text(encoding="utf-8")

    assert "Session 12 agentic handoff" in content
    assert "docs/session12_agentic_handoff.md" in content
