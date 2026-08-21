from pathlib import Path

from scripts.verify_repo_split_readiness import verify

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_energy_aware_protocol_v1_declares_neutral_authority_contract() -> None:
    protocol = (PROJECT_ROOT / "docs/ENERGY_AWARE_PROTOCOL_V1.md").read_text(encoding="utf-8")
    for concept in (
        "CriticFinding",
        "EnergyScore",
        "DecisionRecord",
        "ExecutionEvidence",
        "accept`, `repair`, `clarify`, `reject`, `escalate",
        "product -> eacore",
    ):
        assert concept in protocol


def test_eachat_repository_split_contract() -> None:
    verify()


def test_readme_describes_current_v2_production_surface() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "app.energy_chat.production_app:app" in readme
    assert "/energy-chat/v2/*" in readme
    assert "incubator branch" not in readme
