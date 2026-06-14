from pathlib import Path

from energy_core.decider import evaluate_candidate
from energy_core.evidence import read_evidence_records
from energy_core.ledger import append_decision
from energy_core.policy import load_policy
from energy_core.release import build_release_readiness, format_release_readiness_markdown
from energy_core.state import read_candidate_state

PROJECT_ROOT = Path(".")
SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")
POLICY_PATH = SPEC_DIR / "energy-policy.yaml"
ACCEPT_CANDIDATE = SPEC_DIR / "examples/candidate_accept.json"
EVIDENCE_PATH = SPEC_DIR / "evidence.jsonl"


def test_release_readiness_accepts_extractable_candidate(tmp_path: Path) -> None:
    decisions_path = tmp_path / "decisions.jsonl"
    policy = load_policy(POLICY_PATH)
    candidate = read_candidate_state(ACCEPT_CANDIDATE)
    evidence = read_evidence_records(EVIDENCE_PATH)
    append_decision(decisions_path, evaluate_candidate(policy=policy, candidate=candidate, evidence=evidence))

    summary = build_release_readiness(
        project_root=PROJECT_ROOT,
        spec_dir=SPEC_DIR,
        policy_path=POLICY_PATH,
        candidate_path=ACCEPT_CANDIDATE,
        evidence_path=EVIDENCE_PATH,
        decisions_path=decisions_path,
    )

    assert summary["ready_to_extract"] is True
    assert summary["blockers"] == []
    assert summary["boundary"]["clean"] is True
    assert summary["release_artifacts"]["complete"] is True
    assert "Ready to extract: True" in format_release_readiness_markdown(summary)


def test_release_readiness_blocks_missing_supplied_ledger(tmp_path: Path) -> None:
    missing_decisions_path = tmp_path / "missing-decisions.jsonl"

    summary = build_release_readiness(
        project_root=PROJECT_ROOT,
        spec_dir=SPEC_DIR,
        policy_path=POLICY_PATH,
        candidate_path=ACCEPT_CANDIDATE,
        evidence_path=EVIDENCE_PATH,
        decisions_path=missing_decisions_path,
    )

    assert summary["ready_to_extract"] is False
    assert "supplied_decisions_missing" in summary["blockers"]
    assert summary["supplied_decisions_missing"] is True


def test_release_readiness_blocks_missing_release_artifacts(tmp_path: Path) -> None:
    summary = build_release_readiness(
        project_root=tmp_path,
        spec_dir=SPEC_DIR,
        policy_path=POLICY_PATH,
        candidate_path=ACCEPT_CANDIDATE,
        evidence_path=EVIDENCE_PATH,
    )

    assert summary["ready_to_extract"] is False
    assert "release_artifacts_missing" in summary["blockers"]
    assert summary["release_artifacts"]["complete"] is False
