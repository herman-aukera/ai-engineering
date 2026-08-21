from pathlib import Path

from scripts.verify_repo_split_readiness import verify

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_energy_aware_protocol_v1_declares_neutral_authority_contract() -> None:
    protocol = (PROJECT_ROOT / "docs/ENERGY_AWARE_PROTOCOL_V1.md").read_text(encoding="utf-8")
    for concept in (
        "CriticFinding",
        "ConstraintViolation",
        "DecisionRecord",
        "ExecutionEvidence",
        "accept`, `repair`, `clarify`, `reject`, `escalate",
        "product -> eacore",
    ):
        assert concept in protocol


def test_eacode_repository_split_contract() -> None:
    verify()


def test_readme_states_postgres_authority_and_simulated_execution() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "EACODE_DATABASE_URL" in readme
    assert "simulated execution" in readme
    assert "Session 07: Embedding pipeline pre-exercise" not in readme
