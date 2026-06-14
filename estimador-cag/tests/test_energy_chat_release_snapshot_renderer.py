from pathlib import Path

SCRIPT = Path("scripts/render_energy_chat_release_snapshot.py").read_text(encoding="utf-8")


def test_release_snapshot_renderer_exposes_expected_arguments() -> None:
    assert "--commit-sha" in SCRIPT
    assert "--focused-tests" in SCRIPT
    assert "--full-tests" in SCRIPT
    assert "--local-ref" in SCRIPT
    assert "--ci-ref" in SCRIPT
    assert "--output" in SCRIPT


def test_release_snapshot_renderer_writes_markdown() -> None:
    assert "build_release_snapshot_markdown" in SCRIPT
    assert "write_text" in SCRIPT
    assert "Wrote" in SCRIPT
