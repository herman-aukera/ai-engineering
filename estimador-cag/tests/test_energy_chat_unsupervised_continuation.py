from pathlib import Path

from app.energy_chat.unsupervised_continuation import (
    REQUIRED_UNSUPERVISED_CONTINUATION_ARTIFACTS,
    build_energy_chat_unsupervised_continuation_pack,
    render_energy_chat_unsupervised_continuation_markdown,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_energy_chat_unsupervised_continuation_pack_is_complete() -> None:
    pack = build_energy_chat_unsupervised_continuation_pack(PROJECT_ROOT)

    assert pack.complete is True
    assert pack.missing_artifacts == ()
    assert len(pack.sections) == 5
    assert all(section.complete for section in pack.sections)


def test_energy_chat_unsupervised_continuation_renders_claim_boundaries() -> None:
    pack = build_energy_chat_unsupervised_continuation_pack(PROJECT_ROOT)
    markdown = render_energy_chat_unsupervised_continuation_markdown(pack)

    assert "# Energy Aware Chat unsupervised continuation pack" in markdown
    assert "- Complete: True" in markdown
    assert "- Mode: unsupervised-continuation-safe" in markdown
    assert "measurement_only_no_quality_claim" in markdown
    assert "No Session 08 implementation" in markdown
    assert "No Session 09 implementation" in markdown
    assert "This pack does not prove production readiness" in markdown


def test_energy_chat_unsupervised_continuation_required_artifacts_are_explicit() -> None:
    assert (
        "scripts/validate_energy_chat.sh"
        in REQUIRED_UNSUPERVISED_CONTINUATION_ARTIFACTS
    )
    assert (
        "scripts/check_energy_chat_ci.sh"
        in REQUIRED_UNSUPERVISED_CONTINUATION_ARTIFACTS
    )
    assert (
        "docs/energy_aware_chat_session17_backlog.md"
        in REQUIRED_UNSUPERVISED_CONTINUATION_ARTIFACTS
    )
