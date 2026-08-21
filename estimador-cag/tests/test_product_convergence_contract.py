from pathlib import Path

from scripts.verify_repo_split_readiness import verify

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_energy_aware_protocol_v1_declares_neutral_authority_contract() -> None:
    protocol = (PROJECT_ROOT / "docs/ENERGY_AWARE_PROTOCOL_V1.md").read_text(encoding="utf-8")
    for concept in (
        "CriticFinding",
        "ConstraintViolation",
        "EnergyScore",
        "DecisionRecord",
        "ExecutionEvidence",
        "accept`, `repair`, `clarify`, `reject`, `escalate",
        "product -> eacore",
    ):
        assert concept in protocol


def test_estimator_repository_split_contract() -> None:
    verify()


def test_current_readme_points_to_isolated_production_app() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "app.estimator.production_app:app" in readme
    assert "docs/ENERGY_AWARE_PROTOCOL_V1.md" in readme
    assert "production-ready" in readme
