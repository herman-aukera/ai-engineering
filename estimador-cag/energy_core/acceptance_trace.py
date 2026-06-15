from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from energy_core.evidence_matrix import build_evidence_matrix
from energy_core.package_manifest import resolve_project_root
from energy_core.policy import load_policy

TRACE_VERSION = "1.0.0"
DEFAULT_SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")

CRITERION_PROOFS: dict[int, dict[str, list[str]]] = {
    1: {
        "evidence": ["compile_output", "pytest_output"],
        "tests": ["tests/test_energy_core_policy_loading.py"],
        "surfaces": ["policy_validate", "package_manifest"],
    },
    2: {
        "evidence": ["compile_output", "pytest_output"],
        "tests": ["tests/test_energy_core_decider_accept.py"],
        "surfaces": ["candidate_validate", "schema_bundle"],
    },
    3: {
        "evidence": ["compile_output", "pytest_output"],
        "tests": ["tests/test_energy_core_evidence_matrix.py"],
        "surfaces": ["evidence_summary", "evidence_matrix"],
    },
    4: {
        "evidence": ["pytest_output"],
        "tests": ["tests/test_energy_core_decider_hard_reject.py"],
        "surfaces": ["example_matrix", "candidate_readiness"],
    },
    5: {
        "evidence": ["lint_output", "pytest_output"],
        "tests": ["tests/test_energy_core_decider_hard_repair.py"],
        "surfaces": ["constraint_index", "critic_coverage"],
    },
    6: {
        "evidence": ["pytest_output", "compile_output", "lint_output"],
        "tests": ["tests/test_energy_core_decider_hard_repair.py"],
        "surfaces": ["evidence_matrix", "review_gap_register"],
    },
    7: {
        "evidence": ["pytest_output", "compile_output", "lint_output", "secret_scan_output", "git_diff"],
        "tests": ["tests/test_energy_core_decider_accept.py"],
        "surfaces": ["example_matrix", "review_pack"],
    },
    8: {
        "evidence": ["pytest_output"],
        "tests": ["tests/test_energy_core_cli.py"],
        "surfaces": ["command_catalog", "schema_bundle"],
    },
    9: {
        "evidence": ["pytest_output", "git_diff"],
        "tests": ["tests/test_energy_core_ledger_append_only.py"],
        "surfaces": ["ledger_summary", "ledger_integrity"],
    },
}


def build_acceptance_trace(
    project_root: Path,
    *,
    spec_dir: Path | None = None,
) -> dict[str, Any]:
    """Trace acceptance criteria to evidence, tests, and reviewer surfaces."""

    root = resolve_project_root(project_root)
    resolved_spec_dir = (root / (spec_dir or DEFAULT_SPEC_DIR)).resolve()
    acceptance_path = resolved_spec_dir / "acceptance.md"
    policy_path = resolved_spec_dir / "energy-policy.yaml"
    evidence_path = resolved_spec_dir / "evidence.jsonl"

    policy = load_policy(policy_path)
    evidence_matrix = build_evidence_matrix(policy_path, evidence_path)
    trusted_evidence = {
        row["evidence_type"]
        for row in evidence_matrix["rows"]
        if row["has_trusted_pass"]
    }
    criteria = _extract_acceptance_criteria(acceptance_path)

    rows = [
        _trace_row(
            criterion,
            policy_required_evidence=set(policy.required_acceptance_evidence),
            trusted_evidence=trusted_evidence,
        )
        for criterion in criteria
    ]
    missing_trace = [row["criterion_id"] for row in rows if not row["complete"]]

    return {
        "trace_version": TRACE_VERSION,
        "project_root": str(root),
        "spec_dir": str(resolved_spec_dir),
        "policy_id": policy.policy_id,
        "policy_version": policy.version,
        "complete": bool(criteria)
        and not missing_trace
        and not evidence_matrix["missing_required_acceptance"],
        "criterion_total": len(criteria),
        "traced_total": sum(1 for row in rows if row["complete"]),
        "missing_trace": missing_trace,
        "missing_required_acceptance": evidence_matrix["missing_required_acceptance"],
        "rows": rows,
        "non_goals": [
            "Acceptance trace does not execute shell actions.",
            "Acceptance trace does not call LLM providers.",
            "Acceptance trace does not mutate evidence or the decision ledger.",
        ],
    }


def format_acceptance_trace_text(trace: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Acceptance Trace",
            f"Version: {trace['trace_version']}",
            f"Policy: {trace['policy_id']} {trace['policy_version']}",
            f"Complete: {trace['complete']}",
            f"Criteria: {trace['traced_total']}/{trace['criterion_total']}",
            f"Missing trace: {_inline_list(trace['missing_trace'])}",
        ]
    )


def format_acceptance_trace_markdown(trace: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Acceptance Trace",
        "",
        f"- Version: {trace['trace_version']}",
        f"- Project root: {trace['project_root']}",
        f"- Policy: {trace['policy_id']}",
        f"- Policy version: {trace['policy_version']}",
        f"- Complete: {trace['complete']}",
        f"- Criteria: {trace['traced_total']}/{trace['criterion_total']}",
        "",
        "## Missing trace",
        "",
    ]
    lines.extend(_bullet_list(trace["missing_trace"]))
    lines.extend(["", "## Missing required acceptance evidence", ""])
    lines.extend(_bullet_list(trace["missing_required_acceptance"]))
    lines.extend(["", "## Criteria", ""])
    for row in trace["rows"]:
        lines.extend(
            [
                f"### {row['criterion_id']}",
                "",
                f"- Text: {row['text']}",
                f"- Complete: {row['complete']}",
                f"- Evidence: {_inline_list(row['evidence'])}",
                f"- Missing evidence: {_inline_list(row['missing_evidence'])}",
                f"- Tests: {_inline_list(row['tests'])}",
                f"- Surfaces: {_inline_list(row['surfaces'])}",
                "",
            ]
        )
    lines.extend(["## Non goals", ""])
    lines.extend(_bullet_list(trace["non_goals"]))
    return "\n".join(lines)


def _extract_acceptance_criteria(path: Path) -> list[dict[str, Any]]:
    criteria: list[dict[str, Any]] = []
    pattern = re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$")
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = pattern.match(line)
        if not match:
            continue
        number = int(match.group(1))
        criteria.append(
            {
                "criterion_id": f"A{number}",
                "number": number,
                "text": match.group(2),
                "line": line_number,
            }
        )
    return criteria


def _trace_row(
    criterion: dict[str, Any],
    *,
    policy_required_evidence: set[str],
    trusted_evidence: set[str],
) -> dict[str, Any]:
    proof = CRITERION_PROOFS.get(criterion["number"], {})
    evidence = proof.get("evidence", [])
    tests = proof.get("tests", [])
    surfaces = proof.get("surfaces", [])
    evidence_to_check = [item for item in evidence if item in policy_required_evidence]
    missing_evidence = [item for item in evidence_to_check if item not in trusted_evidence]
    return {
        **criterion,
        "complete": bool(tests) and bool(surfaces) and not missing_evidence,
        "evidence": evidence,
        "missing_evidence": missing_evidence,
        "tests": tests,
        "surfaces": surfaces,
    }


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
