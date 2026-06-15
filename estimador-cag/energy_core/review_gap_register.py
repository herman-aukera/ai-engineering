from __future__ import annotations

from pathlib import Path
from typing import Any

from energy_core.candidate_readiness import build_candidate_readiness_matrix
from energy_core.evidence_matrix import build_evidence_matrix
from energy_core.package_manifest import resolve_project_root
from energy_core.policy_roadmap import build_policy_roadmap
from energy_core.surface_consistency import build_surface_consistency

GAP_REGISTER_VERSION = "1.0.0"
SPEC_RELATIVE_PATH = Path(".energy/specs/0001-energy-policy-ledger")
POLICY_FILENAME = "energy-policy.yaml"
EVIDENCE_FILENAME = "evidence.jsonl"


def build_review_gap_register(project_root: Path) -> dict[str, Any]:
    """Build a non-mutating register of review gaps and accepted boundaries."""

    root = resolve_project_root(project_root)
    spec_dir = root / SPEC_RELATIVE_PATH
    policy_path = spec_dir / POLICY_FILENAME
    evidence_path = spec_dir / EVIDENCE_FILENAME

    policy_roadmap = build_policy_roadmap(policy_path)
    evidence_matrix = build_evidence_matrix(policy_path, evidence_path)
    candidate_readiness = build_candidate_readiness_matrix(
        spec_dir=spec_dir,
        policy_path=policy_path,
        evidence_path=evidence_path,
    )
    surface_consistency = build_surface_consistency(root)

    gaps = [
        *_policy_only_gaps(policy_roadmap),
        *_evidence_gaps(evidence_matrix),
        *_candidate_gaps(candidate_readiness),
        *_surface_gaps(surface_consistency),
    ]
    blocking = [gap for gap in gaps if gap["blocking"]]

    return {
        "gap_register_version": GAP_REGISTER_VERSION,
        "project_root": str(root),
        "complete": not blocking,
        "gap_total": len(gaps),
        "blocking_gap_total": len(blocking),
        "nonblocking_gap_total": len(gaps) - len(blocking),
        "gaps": gaps,
        "non_goals": [
            "Review gap register does not execute shell actions.",
            "Review gap register does not call LLM providers.",
            "Review gap register does not mutate evidence or the decision ledger.",
            "Review gap register reports known boundaries instead of hiding them.",
        ],
    }


def format_review_gap_register_text(register: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Review Gap Register",
            f"Version: {register['gap_register_version']}",
            f"Complete: {register['complete']}",
            f"Gaps: {register['gap_total']}",
            f"Blocking gaps: {register['blocking_gap_total']}",
            f"Nonblocking gaps: {register['nonblocking_gap_total']}",
        ]
    )


def format_review_gap_register_markdown(register: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Review Gap Register",
        "",
        f"- Version: {register['gap_register_version']}",
        f"- Project root: {register['project_root']}",
        f"- Complete: {register['complete']}",
        f"- Gaps: {register['gap_total']}",
        f"- Blocking gaps: {register['blocking_gap_total']}",
        f"- Nonblocking gaps: {register['nonblocking_gap_total']}",
        "",
        "## Gaps",
        "",
    ]
    for gap in register["gaps"]:
        lines.extend(
            [
                f"### {gap['id']}",
                "",
                f"- Category: {gap['category']}",
                f"- Severity: {gap['severity']}",
                f"- Blocking: {gap['blocking']}",
                f"- Summary: {gap['summary']}",
                f"- Evidence: {gap['evidence']}",
                f"- Next action: {gap['next_action']}",
                "",
            ]
        )
    lines.extend(["## Non goals", ""])
    lines.extend(_bullet_list(register["non_goals"]))
    return "\n".join(lines)


def _policy_only_gaps(roadmap: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"policy_only:{entry['constraint_id']}",
            "category": "policy_boundary",
            "severity": "planned",
            "blocking": False,
            "summary": entry["boundary"],
            "evidence": f"future evidence: {entry['future_evidence']}",
            "next_action": entry["slice"],
        }
        for entry in roadmap["entries"]
    ]


def _evidence_gaps(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for missing in matrix["missing_required_acceptance"]:
        gaps.append(
            {
                "id": f"evidence_missing:{missing}",
                "category": "evidence",
                "severity": "blocking",
                "blocking": True,
                "summary": "Required acceptance evidence has no trusted passing record.",
                "evidence": missing,
                "next_action": "refresh-evidence-jsonl",
            }
        )
    for row in matrix["rows"]:
        if not row["required_acceptance"] and row["record_total"] == 0:
            evidence_type = row["evidence_type"]
            gaps.append(
                {
                    "id": f"optional_evidence_empty:{evidence_type}",
                    "category": "evidence",
                    "severity": "informational",
                    "blocking": False,
                    "summary": "Declared optional evidence has no records yet.",
                    "evidence": evidence_type,
                    "next_action": "add-records-when-this-surface-becomes-required",
                }
            )
    return gaps


def _candidate_gaps(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for case in matrix["cases"]:
        if case["ready"]:
            continue
        gaps.append(
            {
                "id": f"candidate_not_ready:{case['example']}",
                "category": "example_scenario",
                "severity": "expected_scenario",
                "blocking": False,
                "summary": "Bundled example intentionally models repair or reject readiness.",
                "evidence": _inline_list(case["missing_required_evidence"]),
                "next_action": "keep-example-matrix-and-candidate-readiness-in-sync",
            }
        )
    return gaps


def _surface_gaps(consistency: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"surface_missing:{surface_id}",
            "category": "review_surface",
            "severity": "blocking",
            "blocking": True,
            "summary": "Reviewer-facing surface is not consistently exposed.",
            "evidence": surface_id,
            "next_action": "register-surface-in-catalog-reviewer-pack-and-manifest",
        }
        for surface_id in consistency["missing_surface_ids"]
    ]


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
