from pathlib import Path

DOC = Path("docs/energy_aware_chat_release_snapshot.md").read_text(encoding="utf-8")


def test_release_snapshot_guide_mentions_gates_and_renderer() -> None:
    assert "bash scripts/validate_energy_chat.sh" in DOC
    assert "bash scripts/check_energy_chat_ci.sh" in DOC
    assert "scripts/render_energy_chat_release_snapshot.py" in DOC


def test_release_snapshot_guide_preserves_claim_token() -> None:
    assert "measurement_only_no_quality_claim" in DOC
    assert "evidence bookkeeping only" in DOC
