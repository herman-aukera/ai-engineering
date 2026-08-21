from __future__ import annotations

import os

import pytest

from energy_core.beta_demo import BetaDemoRunner
from energy_core.coding_agent import CodingProposal
from energy_core.postgres_beta_store import PostgresBetaDemoStore, migrate_database

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_EACODE_POSTGRES_INTEGRATION") != "1",
    reason="requires explicit EACODE PostgreSQL integration environment",
)


def _proposal(proposal_id: str) -> CodingProposal:
    return CodingProposal(
        proposal_id=proposal_id,
        objective="Add a safe health check",
        spec_id="0012-production-hardening",
        patch="def health():\n    return 'todo'\n",
        changed_files=("app/health.py",),
        proposed_commands=(("pytest", "-q", "tests/test_health.py"),),
    )


def test_postgres_authority_survives_store_reconstruction() -> None:
    database_url = os.environ["EACODE_DATABASE_URL"]
    migrate_database(database_url)
    runner = BetaDemoRunner()
    proposal = _proposal("postgres-authority-integration")
    prepared = runner.prepare(proposal)
    store = PostgresBetaDemoStore(database_url)
    store.verify_schema()
    store.create_result(prepared, owner_id="operator-integration")

    receipt = store.issue_authorization(
        proposal_id=proposal.proposal_id,
        actor="operator-integration",
        owner_id="operator-integration",
        scope=runner.authorization_scope(prepared),
    )
    consumed = store.consume_authorization(
        receipt_id=receipt.receipt_id,
        proposal_id=proposal.proposal_id,
        actor="operator-integration",
        owner_id="operator-integration",
        scope=runner.authorization_scope(prepared),
    )
    completed = runner.execute(
        prepared,
        authorization_id=consumed.receipt_id,
        actor=consumed.actor,
    )
    store.update_result(completed, owner_id="operator-integration")

    reconstructed = PostgresBetaDemoStore(database_url)
    reconstructed.verify_schema()
    recovered = reconstructed.get_result(
        proposal.proposal_id,
        owner_id="operator-integration",
    )
    recovered_receipt = reconstructed.get_authorization(receipt.receipt_id)

    assert recovered is not None
    assert recovered.final_decision.disposition == "accept"
    assert recovered.execution.execution_performed is True
    assert recovered_receipt is not None
    assert recovered_receipt.consumed_at is not None

    with pytest.raises(PermissionError, match="already_consumed|already_reserved"):
        reconstructed.consume_authorization(
            receipt_id=receipt.receipt_id,
            proposal_id=proposal.proposal_id,
            actor="operator-integration",
            owner_id="operator-integration",
            scope=runner.authorization_scope(prepared),
        )
