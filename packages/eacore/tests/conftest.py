from __future__ import annotations

from datetime import datetime, timezone

import pytest

from eacore.contracts import (
    DecisionEnvelope,
    EnergyComponent,
    EnergySnapshot,
    OutcomeClass,
    RecordIdentity,
    RetentionClass,
    VersionIdentity,
)
from eacore.engine import ledger_record_hash
from eacore.contracts import LedgerRecord


@pytest.fixture
def accepted_energy() -> EnergySnapshot:
    return EnergySnapshot(
        energy_snapshot_id="energy:1",
        candidate_id="candidate:1",
        policy_ref="policy:1.0.0",
        energy_before=10,
        energy_after=2,
        energy_delta=-8,
        components=(
            EnergyComponent(
                component_id="component:quality",
                constraint_id="quality",
                penalty=2,
                observation_refs=("observation:1",),
            ),
        ),
    )


@pytest.fixture
def accepted_decision() -> DecisionEnvelope:
    return DecisionEnvelope(
        decision_id="decision:1",
        candidate_id="candidate:1",
        product_decision_code="accept",
        outcome_class=OutcomeClass.ACCEPTED,
        policy_ref="policy:1.0.0",
        energy_snapshot_ref="energy:1",
        authorization_ref="policy-decision:1",
        reason_summary="All common invariants passed.",
    )


@pytest.fixture
def ledger_record(accepted_decision: DecisionEnvelope) -> LedgerRecord:
    identity = RecordIdentity(
        record_id="record:1",
        run_id="run:1",
        product="eachat",
        recorded_at=datetime(2026, 7, 17, tzinfo=timezone.utc),
        producer="eachat-adapter",
    )
    version = VersionIdentity(
        contract_name="decision-ledger",
        contract_version="0.1.0",
        schema_version="1.0.0",
        policy_version="1.0.0",
    )
    provisional = {
        "identity": identity,
        "version": version,
        "decision": accepted_decision,
        "previous_record_hash": None,
        "retention_class": RetentionClass.AUDIT,
    }
    return LedgerRecord(canonical_hash=ledger_record_hash(provisional), **provisional)
