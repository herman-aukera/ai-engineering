from __future__ import annotations

from pathlib import Path

from energy_core.bundle import build_bundle_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = PROJECT_ROOT / ".energy/specs/0001-energy-policy-ledger"
POLICY = SPEC_DIR / "energy-policy.yaml"
ACCEPT_CANDIDATE = SPEC_DIR / "examples/candidate_accept.json"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def test_bundle_manifest_marks_supplied_ledger_path_as_required(tmp_path: Path) -> None:
    supplied_ledger = tmp_path / "ledger.jsonl"

    manifest = build_bundle_manifest(
        spec_dir=SPEC_DIR,
        policy_path=POLICY,
        candidate_path=ACCEPT_CANDIDATE,
        evidence_path=EVIDENCE,
        decisions_path=supplied_ledger,
    )

    assert manifest["complete"] is False
    assert str(supplied_ledger.resolve()) in manifest["missing_required"]
    assert any(entry["role"] == "active_decisions" and entry["exists"] is False for entry in manifest["files"])
