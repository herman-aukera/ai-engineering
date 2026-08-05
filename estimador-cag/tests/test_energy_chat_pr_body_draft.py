from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PR_DRAFT = (ROOT / "docs" / "energy_aware_chat_pr_body_draft.md").read_text(
    encoding="utf-8"
)
INDEX = (ROOT / "docs" / "energy_aware_chat_reviewer_index.md").read_text(
    encoding="utf-8"
)
MANIFEST = (ROOT / "scripts" / "export_energy_chat_manifest.sh").read_text(
    encoding="utf-8"
)


def test_pr_body_draft_has_validation_commands_and_boundaries() -> None:
    assert "bash scripts/validate_energy_chat.sh" in PR_DRAFT
    assert "bash estimador-cag/scripts/check_energy_chat_ci.sh" in PR_DRAFT
    assert "measurement_only_no_quality_claim" in PR_DRAFT
    assert "RAG grounding" in PR_DRAFT


def test_pr_body_draft_is_linked_from_reviewer_index_and_manifest() -> None:
    path = "docs/energy_aware_chat_pr_body_draft.md"
    assert path in INDEX
    assert path in MANIFEST
