from __future__ import annotations

import hashlib
import json
from pathlib import Path

from energy_core.hashing import sha256_bytes, sha256_file, sha256_text
from energy_core.ledger_recovery import recover_decision_ledger
from energy_core.ledger_recovery_cli import main as recovery_main
from energy_core.models import EnergyDecision, EvidenceRecord
from energy_core.policy import load_policy
from energy_core.validation import validate_evidence_records


def _decision(candidate_id: str = "candidate-1") -> EnergyDecision:
    return EnergyDecision(
        decision_id=f"decision-{candidate_id}",
        run_id="run-1",
        policy_id="energy-code-default",
        candidate_id=candidate_id,
        decision="accept",
        energy_before=0,
        energy_after=0,
        energy_delta=0,
        hard_reject_violations=[],
        hard_repair_violations=[],
        soft_violations=[],
        missing_evidence=[],
        evidence_refs=[],
        required_repairs=[],
        reasoning_summary="ok",
        next_action="stop",
    )


def test_sha256_helpers_hash_exact_bytes(tmp_path: Path) -> None:
    payload = "pytest -q\n"
    artifact = tmp_path / "artifact.txt"
    artifact.write_bytes(payload.encode("utf-8"))
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    assert sha256_bytes(payload.encode("utf-8")) == f"sha256:{expected}"
    assert sha256_text(payload) == f"sha256:{expected}"
    assert sha256_file(artifact) == f"sha256:{expected}"


def test_evidence_validation_rejects_unknown_type_and_bad_hash() -> None:
    policy = load_policy(Path(".energy/specs/0001-energy-policy-ledger/energy-policy.yaml"))
    records = [
        EvidenceRecord(
            evidence_id="ev-unknown",
            type="invented_output",
            status="pass",
            summary="unsupported",
            command_hash="md5:not-allowed",
        )
    ]

    report = validate_evidence_records(policy, records)

    assert report["complete"] is False
    assert report["unknown_evidence_types"] == ["invented_output"]
    assert report["invalid_hashes"] == [
        {"evidence_id": "ev-unknown", "field": "command_hash", "value": "md5:not-allowed"}
    ]


def test_recovery_preserves_source_and_quarantines_invalid_rows(tmp_path: Path) -> None:
    source = tmp_path / "decisions.jsonl"
    recovered = tmp_path / "recovered.jsonl"
    quarantine = tmp_path / "quarantine.jsonl"
    valid = _decision().model_dump_json()
    original = f"{valid}\n{{broken-json\n"
    source.write_text(original, encoding="utf-8")

    report = recover_decision_ledger(source, recovered, quarantine)

    assert source.read_text(encoding="utf-8") == original
    assert report["source_record_total"] == 2
    assert report["recovered_record_total"] == 1
    assert report["quarantined_record_total"] == 1
    assert json.loads(recovered.read_text(encoding="utf-8"))["candidate_id"] == "candidate-1"
    quarantined = json.loads(quarantine.read_text(encoding="utf-8"))
    assert quarantined["line"] == 2
    assert quarantined["raw"] == "{broken-json"
    assert report["source_sha256"].startswith("sha256:")


def test_recovery_refuses_to_overwrite_source_or_outputs(tmp_path: Path) -> None:
    source = tmp_path / "decisions.jsonl"
    source.write_text(_decision().model_dump_json() + "\n", encoding="utf-8")

    for recovered, quarantine in [
        (source, tmp_path / "q.jsonl"),
        (tmp_path / "r.jsonl", source),
    ]:
        try:
            recover_decision_ledger(source, recovered, quarantine)
        except ValueError as exc:
            assert "must differ" in str(exc)
        else:
            raise AssertionError("recovery must not overwrite its source")

    existing = tmp_path / "existing.jsonl"
    existing.write_text("keep", encoding="utf-8")
    try:
        recover_decision_ledger(source, existing, tmp_path / "q2.jsonl")
    except FileExistsError:
        pass
    else:
        raise AssertionError("recovery must not overwrite existing outputs")


def test_recovery_cli_reports_quarantine_and_returns_nonzero(
    tmp_path: Path,
    capsys,
) -> None:
    source = tmp_path / "decisions.jsonl"
    recovered = tmp_path / "recovered.jsonl"
    quarantine = tmp_path / "quarantine.jsonl"
    source.write_text("{broken-json\n", encoding="utf-8")

    result = recovery_main(
        [
            "--source",
            str(source),
            "--recovered",
            str(recovered),
            "--quarantine",
            str(quarantine),
            "--fail-on-quarantine",
        ]
    )
    report = json.loads(capsys.readouterr().out)

    assert result == 1
    assert report["quarantined_record_total"] == 1
