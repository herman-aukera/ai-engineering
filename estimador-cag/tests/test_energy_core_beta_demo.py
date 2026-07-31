from energy_core.beta_demo import BetaDemoRunner
from energy_core.coding_agent import CodingProposal


def test_demo_repairs_authorizes_executes_and_reevaluates() -> None:
    proposal = CodingProposal(
        proposal_id="proposal-1",
        objective="Add a safe health check.",
        spec_id="0011-demo-ready-beta",
        patch="def health():\n    return 'todo'\n",
        changed_files=("app/health.py",),
        proposed_commands=(("pytest", "-q", "tests/test_health.py"),),
    )

    result = BetaDemoRunner().run(proposal, human_authorization=True)

    assert result.initial_decision.disposition == "repair"
    assert result.final_decision.disposition == "accept"
    assert result.authorization.authorized is True
    assert result.execution.execution_performed is True
    assert result.execution.sanitized is True
    assert result.execution.exit_code == 0
    assert len(result.repair_history) == 1
    assert result.rollback.available is True
    assert result.timeline[-1].event_type == "reevaluation"


def test_proposal_is_inert_without_human_authorization() -> None:
    proposal = CodingProposal(
        proposal_id="proposal-2",
        objective="Inspect status.",
        spec_id="0011-demo-ready-beta",
        patch="def status():\n    return 'ok'\n",
        changed_files=("app/status.py",),
        proposed_commands=(("git", "status", "--short"),),
    )

    result = BetaDemoRunner().run(proposal, human_authorization=False)

    assert result.authorization.authorized is False
    assert result.execution.execution_performed is False
    assert result.final_decision.disposition == "escalate"
