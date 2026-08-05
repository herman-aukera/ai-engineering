import pytest

from energy_core.beta_demo import BetaDemoRunner
from energy_core.coding_agent import CodingProposal


def _proposal(
    proposal_id: str,
    *,
    patch: str = "def health():\n    return 'todo'\n",
    commands: tuple[tuple[str, ...], ...] = (
        ("pytest", "-q", "tests/test_health.py"),
    ),
) -> CodingProposal:
    return CodingProposal(
        proposal_id=proposal_id,
        objective="Add a safe health check.",
        spec_id="0012-production-hardening",
        patch=patch,
        changed_files=("app/health.py",),
        proposed_commands=commands,
    )


def test_demo_prepares_repair_but_remains_inert_without_server_receipt() -> None:
    result = BetaDemoRunner().prepare(_proposal("proposal-1"))

    assert result.initial_decision.disposition == "repair"
    assert result.final_decision.disposition == "escalate"
    assert result.authorization.authorized is False
    assert result.execution.execution_performed is False
    assert result.effective_proposal.patch.endswith("return 'ok'\n")
    assert len(result.repair_history) == 1


def test_server_authorized_execution_uses_effective_revision_and_reevaluates() -> None:
    runner = BetaDemoRunner()
    prepared = runner.prepare(_proposal("proposal-2"))

    completed = runner.execute(
        prepared,
        authorization_id="demo-receipt-abcdefghijklmnopqrstuvwxyz",
        actor="operator-1",
    )

    assert completed.final_decision.disposition == "accept"
    assert completed.authorization.authorized is True
    assert completed.authorization.source == "server_session_receipt"
    assert completed.execution.execution_performed is True
    assert completed.execution.sanitized is True
    assert completed.execution.exit_code == 0
    assert completed.timeline[-1].event_type == "reevaluation"


def test_hard_rejected_proposal_cannot_be_authorized() -> None:
    proposal = _proposal(
        "proposal-3",
        patch="API_KEY = 'sk-this-is-a-secret-value-123456789'\n",
    )
    runner = BetaDemoRunner()
    prepared = runner.prepare(proposal)

    assert prepared.initial_decision.disposition == "reject"
    assert prepared.final_decision.disposition == "reject"
    with pytest.raises(PermissionError, match="hard-rejected"):
        runner.authorization_scope(prepared)


def test_unresolved_semantic_repair_cannot_be_authorized() -> None:
    runner = BetaDemoRunner()
    prepared = runner.prepare(
        _proposal("proposal-4", patch="def health():\n    return 'ok'\n", commands=())
    )

    assert prepared.final_decision.disposition == "repair"
    with pytest.raises(PermissionError, match="still requires repair"):
        runner.authorization_scope(prepared)
