from pathlib import Path

REPOSITORY_DOC = Path("docs/energy_aware_chat_repository_readiness.md").read_text(encoding="utf-8")
CI_HELPER = Path("scripts/check_energy_chat_ci.sh").read_text(encoding="utf-8")
VALIDATION_GATE = Path("scripts/validate_energy_chat.sh").read_text(encoding="utf-8")


def test_repository_readiness_doc_declares_staging_not_merge_branch() -> None:
    assert "final-project staging branch" in REPOSITORY_DOC
    assert "not intended to be merged into the coursework `main` branch" in REPOSITORY_DOC
    assert "unmerged = expected" in REPOSITORY_DOC
    assert "product target = future standalone repository" in REPOSITORY_DOC


def test_repository_readiness_doc_names_future_standalone_repo() -> None:
    assert "herman-aukera/energy-aware-chat" in REPOSITORY_DOC
    assert "Session 17" in REPOSITORY_DOC
    assert "Extract to the standalone repository" in REPOSITORY_DOC


def test_repository_readiness_doc_lists_export_boundary() -> None:
    required_paths = [
        "estimador-cag/app/energy_chat/",
        "estimador-cag/energy_chat_streamlit_app.py",
        "estimador-cag/docs/energy_aware_chat_demo.md",
        "estimador-cag/docs/energy_aware_chat_repository_readiness.md",
        "estimador-cag/scripts/validate_energy_chat.sh",
        "estimador-cag/tests/test_energy_chat_*.py",
        ".github/workflows/ci.yml",
    ]

    for required_path in required_paths:
        assert required_path in REPOSITORY_DOC


def test_repository_readiness_doc_preserves_claim_boundaries() -> None:
    assert "No RAG grounding yet" in REPOSITORY_DOC or "RAG grounding" in REPOSITORY_DOC
    assert "DeepSeek quality improvement" in REPOSITORY_DOC
    assert "measurement_only_no_quality_claim" in REPOSITORY_DOC


def test_ci_helper_is_noninteractive_and_commit_scoped() -> None:
    assert "gh api" in CI_HELPER
    assert "actions/runs?per_page=100" in CI_HELPER
    assert ".head_branch == \"$BRANCH\"" in CI_HELPER
    assert ".head_sha == \"$SHA\"" in CI_HELPER
    assert ".name == \"$workflow_name\"" in CI_HELPER
    assert "gh run view \"$RUN_ID\"" in CI_HELPER
    assert "--log-failed" in CI_HELPER
    assert "conclusion" in CI_HELPER
    assert "success" in CI_HELPER


def test_validation_gate_dynamically_discovers_focused_tests_and_fails_dirty_tree() -> None:
    assert "test_energy_chat_*.py" in VALIDATION_GATE
    assert "git status --short" in VALIDATION_GATE
    assert "DIRTY TREE DETECTED" in VALIDATION_GATE
    assert "exit 1" in VALIDATION_GATE
