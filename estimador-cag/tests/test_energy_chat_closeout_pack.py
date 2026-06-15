from pathlib import Path

from app.energy_chat.closeout_pack import (
    REQUIRED_CLOSEOUT_ARTIFACTS,
    build_energy_chat_closeout_pack,
    render_energy_chat_closeout_markdown,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_energy_chat_closeout_pack_is_complete_for_current_tree() -> None:
    pack = build_energy_chat_closeout_pack(PROJECT_ROOT)

    assert pack.complete is True
    assert pack.missing_artifacts == ()
    assert len(pack.sections) == 5
    assert all(section.complete for section in pack.sections)


def test_energy_chat_closeout_pack_renders_reviewer_markdown() -> None:
    pack = build_energy_chat_closeout_pack(PROJECT_ROOT)
    markdown = render_energy_chat_closeout_markdown(pack)

    assert "# Energy Aware Chat closeout pack" in markdown
    assert "- Complete: True" in markdown
    assert "measurement_only_no_quality_claim" in markdown
    assert "Claim boundary reminders" in markdown
    assert "Keep production claims tied to deployment evidence" in markdown


def test_required_closeout_artifacts_are_registered() -> None:
    pack = build_energy_chat_closeout_pack(PROJECT_ROOT)

    assert pack.complete is True
    assert "scripts/validate_energy_chat.sh" in REQUIRED_CLOSEOUT_ARTIFACTS
    assert "docs/energy_aware_chat_session17_backlog.md" in REQUIRED_CLOSEOUT_ARTIFACTS
