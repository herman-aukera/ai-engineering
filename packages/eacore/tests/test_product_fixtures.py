from pathlib import Path
import json

import pytest

from eacore.contracts import (
    CandidateRef,
    CriticFindingEnvelope,
    CriticSeverity,
    DecisionEnvelope,
    OutcomeClass,
)
from eacore.engine import candidate_fingerprint

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("product", ["session13", "eachat", "eacode"])
def test_frozen_product_fixture_has_exact_source_metadata(product: str) -> None:
    metadata = json.loads((FIXTURES / product / "metadata.json").read_text(encoding="utf-8"))
    assert len(metadata["source_commit"]) == 40
    assert metadata["source_branch"]
    assert metadata["source_files"]
    assert metadata["redaction_status"] == "sanitized_reference_only"


@pytest.mark.parametrize("product", ["session13", "eachat", "eacode"])
def test_product_fixture_maps_to_neutral_references_without_importing_product(product: str) -> None:
    fixture = json.loads((FIXTURES / product / f"{product}_fixture.json").read_text())
    candidate = fixture["candidate"]
    fingerprint = candidate_fingerprint(
        candidate_kind=candidate["candidate_kind"],
        payload={"payload_ref": candidate["payload_ref"]},
    )
    candidate_ref = CandidateRef(
        candidate_id=candidate["candidate_id"],
        candidate_version=candidate["candidate_version"],
        candidate_kind=candidate["candidate_kind"],
        fingerprint=fingerprint,
        payload_ref=candidate["payload_ref"],
    )
    finding = CriticFindingEnvelope(
        finding_id=f"finding:{product}:1",
        critic_id=fixture["critic"]["critic_id"],
        critic_version=fixture["critic"]["critic_version"],
        constraint_id=fixture["critic"]["product_issue_code"],
        severity=CriticSeverity(fixture["critic"]["severity"]),
        status="open",
        summary=fixture["critic"]["summary"],
        deterministic=True,
    )
    decision = DecisionEnvelope(
        decision_id=f"decision:{product}:1",
        candidate_id=candidate_ref.candidate_id,
        product_decision_code=fixture["decision"]["product_decision_code"],
        outcome_class=OutcomeClass(fixture["decision"]["outcome_class"]),
        policy_ref=f"{product}:policy:1",
        energy_snapshot_ref=f"{product}:energy:1",
        finding_refs=(finding.finding_id,),
        reason_summary="Frozen fixture mapping for compatibility testing.",
    )
    assert len(candidate_ref.fingerprint) == 64
    assert decision.product_decision_code
    assert finding.constraint_id == fixture["critic"]["product_issue_code"]
