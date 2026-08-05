from pathlib import Path

REVIEWER_INDEX = Path("docs/energy_aware_chat_reviewer_index.md").read_text(
    encoding="utf-8"
)


def test_reviewer_index_links_actions_filtering_guide() -> None:
    assert "docs/energy_aware_chat_actions_filtering.md" in REVIEWER_INDEX
    assert "Actions filtering guide" in REVIEWER_INDEX
