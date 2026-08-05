from pathlib import Path

INDEX = Path("docs/energy_aware_chat_reviewer_index.md").read_text(encoding="utf-8")


def test_reviewer_index_links_release_snapshot_guide_and_renderer() -> None:
    assert "docs/energy_aware_chat_release_snapshot.md" in INDEX
    assert "scripts/render_energy_chat_release_snapshot.py" in INDEX
    assert "release snapshot helper" in INDEX
