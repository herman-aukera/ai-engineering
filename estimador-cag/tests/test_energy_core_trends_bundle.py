from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from energy_core.bundle import build_bundle_manifest
from energy_core.models import EnergyDecision
from energy_core.trends import summarize_decision_trends

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = PROJECT_ROOT / ".energy/specs/0001-energy-policy-ledger"
POLICY = SPEC_DIR / "energy-policy.yaml"
ACCEPT_CANDIDATE = SPEC_DIR / "examples/candidate_accept.json"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def test_decision_trends_marks_regression() -> None:
    decisions = [
        _decision(candidate_id="slice-accept", decision="accept", energy_before=500, energy_after=0, energy_delta=-500),
        _decision(candidate_id="slice-repair", decision="repair", energy_before=0, energy_after=120, energy_delta=120),
    ]

    summary = summarize_decision_trends(decisions)

    assert summary["total"] == 2
    assert summary["accepted"] == 1
    assert summary["non_accept"] == 1
    assert summary["regressing"] == 1
    assert summary["trend"] == "needs_attention"
    assert summary["non_accept_candidate_ids"] == ["slice-repair"]
    assert summary["regressing_candidate_ids"] == ["slice-repair"]


def test_bundle_manifest_hashes_required_files() -> None:
    manifest = build_bundle_manifest(
        spec_dir=SPEC_DIR,
        policy_path=POLICY,
        candidate_path=ACCEPT_CANDIDATE,
        evidence_path=EVIDENCE,
    )

    assert manifest["complete"] is True
    assert manifest["missing_required"] == []
    policy_entries = [entry for entry in manifest["files"] if entry["role"] == "active_policy"]
    assert len(policy_entries) == 1
    assert policy_entries[0]["exists"] is True
    assert len(policy_entries[0]["sha256"]) == 64


def test_cli_decision_trends_and_bundle_manifest(tmp_path: Path) -> None:
    decisions = tmp_path / "decisions.jsonl"
    _run(
        "evaluate",
        "--policy",
        str(POLICY),
        "--candidate",
        str(ACCEPT_CANDIDATE),
        "--evidence",
        str(EVIDENCE),
        "--decisions",
        str(decisions),
        "--format",
        "json",
    )

    trends = _run("decision-trends", "--decisions", str(decisions), "--format", "json")
    trend_payload = json.loads(trends.stdout)
    assert trend_payload["total"] == 1
    assert trend_payload["trend"] == "improving"

    trend_report = tmp_path / "decision-trends.md"
    trend_markdown = _run(
        "decision-trends",
        "--decisions",
        str(decisions),
        "--format",
        "markdown",
        "--report",
        str(trend_report),
    )
    assert "# Energy Aware Code Decision Trends" in trend_markdown.stdout
    assert "# Energy Aware Code Decision Trends" in trend_report.read_text(encoding="utf-8")

    bundle = _run(
        "bundle-manifest",
        "--spec-dir",
        str(SPEC_DIR),
        "--policy",
        str(POLICY),
        "--candidate",
        str(ACCEPT_CANDIDATE),
        "--evidence",
        str(EVIDENCE),
        "--decisions",
        str(decisions),
        "--format",
        "json",
        "--fail-on-incomplete",
    )
    bundle_payload = json.loads(bundle.stdout)
    assert bundle_payload["complete"] is True
    assert bundle_payload["missing_required"] == []
    assert any(entry["role"] == "active_decisions" for entry in bundle_payload["files"])


def _decision(
    *,
    candidate_id: str,
    decision: str,
    energy_before: int,
    energy_after: int,
    energy_delta: int,
) -> EnergyDecision:
    return EnergyDecision(
        policy_id="energy-code-default",
        candidate_id=candidate_id,
        decision=decision,
        energy_before=energy_before,
        energy_after=energy_after,
        energy_delta=energy_delta,
        hard_reject_violations=[],
        hard_repair_violations=[] if decision == "accept" else ["missing_required_evidence"],
        soft_violations=[],
        missing_evidence=[],
        evidence_refs=["ev-pytest"],
        required_repairs=[] if decision == "accept" else ["Add required evidence."],
        reasoning_summary="Synthetic decision for trend testing.",
        next_action="stop" if decision == "accept" else "repair",
    )


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "energy_core.cli", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
