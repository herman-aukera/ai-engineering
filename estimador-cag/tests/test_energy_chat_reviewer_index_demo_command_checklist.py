from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEWER_INDEX = (ROOT / "docs/energy_aware_chat_reviewer_index.md").read_text(
    encoding="utf-8"
)


def test_reviewer_index_links_demo_command_checklist() -> None:
    assert "docs/energy_aware_chat_demo_command_checklist.md" in REVIEWER_INDEX
    assert "| Demo command checklist |" in REVIEWER_INDEX
