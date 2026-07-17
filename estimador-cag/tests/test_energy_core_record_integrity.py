from __future__ import annotations

import json
from pathlib import Path

from energy_core.evidence import read_evidence_records
from energy_core.ledger import append_decision, read_decisions
from energy_core.ledger_integrity import build_ledger_integrity
from energy_core.models import EnergyDecision


def _decision(**updates: object) -> EnergyDecision:
    payload: dict[str, object] = {
        "policy_id": "energy-code-default",
        "candidate_id": "candidate-1",
        "decision": "accept",
        "energy_before": 10,
        "energy_after": 0,
        "energy_delta": -10,
        "hard_reject_violations": [],
        "hard_repair_violations": [],
        "soft_violations": [],
        "missing_evidence": [],
        "evidence_refs": ["ev-1"],
        "required_repairs": [],
        "reasoning_summary": "ok",
        "next_action": "stop",
    }
    payload.update(updates)
    return EnergyDecision.model_validate(payload)


def test_legacy_evidence_is_migrated_in_memory() -> None:
    fixture = Path(__file__).parents[1] / ".energy/specs/0001-energy-policy-ledger/evidence.jsonl"

    records = read_evidence_records(fixture)

    assert records
    assert all(record.schema_version == "1.0.0" for record in records)
    assert all(record.run_id == "legacy" for record in records)
    assert all(record.trust_classification in {"trusted", "untrusted"} for record in records)


def test_append_enriches_new_decision_envelope(tmp_path: Path) -> None:
    ledger = tmp_path / "decisions.jsonl"

    append_decision(ledger, _decision())
    stored = json.loads(ledger.read_text(encoding="utf-8"))
    loaded = read_decisions(ledger)[0]

    assert stored["schema_version"] == "1.0.0"
    assert stored["decision_id"].startswith("decision-")
    assert stored["run_id"].startswith("run-")
    assert stored["recorded_at"].endswith("Z")
    assert loaded.decision_id == stored["decision_id"]


def test_integrity_fails_duplicate_decision_ids(tmp_path: Path) -> None:
    ledger = tmp_path / "decisions.jsonl"
    record = _decision(decision_id="decision-duplicate", run_id="run-1").model_dump_json()
    ledger.write_text(f"{record}\n{record}\n", encoding="utf-8")

    report = build_ledger_integrity(ledger)

    assert report["complete"] is False
    assert report["duplicate_decision_ids"] == ["decision-duplicate"]


def test_integrity_fails_duplicate_evidence_and_dangling_refs(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.jsonl"
    ledger = tmp_path / "decisions.jsonl"
    row = {"evidence_id": "ev-1", "type": "pytest_output", "status": "pass", "summary": "ok"}
    evidence.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    ledger.write_text(_decision(evidence_refs=["ev-1", "ev-missing"]).model_dump_json() + "\n", encoding="utf-8")

    report = build_ledger_integrity(ledger, evidence_path=evidence)

    assert report["complete"] is False
    assert report["duplicate_evidence_ids"] == ["ev-1"]
    assert report["dangling_evidence_refs"] == [
        {"candidate_id": "candidate-1", "evidence_id": "ev-missing", "line": 1}
    ]
