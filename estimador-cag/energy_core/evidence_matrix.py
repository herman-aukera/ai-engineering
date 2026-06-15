from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from energy_core.evidence import read_evidence_records
from energy_core.policy import load_policy

MATRIX_VERSION = "1.0.0"


def build_evidence_matrix(policy_path: Path, evidence_path: Path) -> dict[str, Any]:
    policy = load_policy(policy_path)
    records = read_evidence_records(evidence_path)
    required = set(policy.required_acceptance_evidence)
    rows = [
        _row(evidence_type, required=evidence_type in required, records=records)
        for evidence_type in sorted(policy.evidence_types)
    ]
    missing_required = [
        row["evidence_type"]
        for row in rows
        if row["required_acceptance"] and not row["has_trusted_pass"]
    ]
    undeclared_types = sorted(
        {record.type for record in records if record.type not in policy.evidence_types}
    )

    return {
        "matrix_version": MATRIX_VERSION,
        "policy_id": policy.policy_id,
        "policy_version": policy.version,
        "complete": not missing_required and not undeclared_types,
        "evidence_type_total": len(rows),
        "record_total": len(records),
        "required_acceptance_total": len(required),
        "missing_required_acceptance": missing_required,
        "undeclared_record_types": undeclared_types,
        "status_counts": dict(sorted(Counter(record.status for record in records).items())),
        "rows": rows,
    }


def format_evidence_matrix_text(matrix: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Evidence Matrix",
            f"Matrix version: {matrix['matrix_version']}",
            f"Policy: {matrix['policy_id']} {matrix['policy_version']}",
            f"Complete: {matrix['complete']}",
            f"Evidence types: {matrix['evidence_type_total']}",
            f"Records: {matrix['record_total']}",
            f"Missing required: {_inline_list(matrix['missing_required_acceptance'])}",
        ]
    )


def format_evidence_matrix_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Evidence Matrix",
        "",
        f"- Matrix version: {matrix['matrix_version']}",
        f"- Policy: {matrix['policy_id']}",
        f"- Policy version: {matrix['policy_version']}",
        f"- Complete: {matrix['complete']}",
        f"- Evidence types: {matrix['evidence_type_total']}",
        f"- Records: {matrix['record_total']}",
        f"- Required acceptance evidence: {matrix['required_acceptance_total']}",
        "",
        "## Missing required acceptance evidence",
        "",
    ]
    lines.extend(_bullet_list(matrix["missing_required_acceptance"]))
    lines.extend(["", "## Undeclared record types", ""])
    lines.extend(_bullet_list(matrix["undeclared_record_types"]))
    lines.extend(["", "## Rows", ""])
    for row in matrix["rows"]:
        lines.extend(
            [
                f"### {row['evidence_type']}",
                "",
                f"- Required acceptance: {row['required_acceptance']}",
                f"- Records: {row['record_total']}",
                f"- Trusted pass: {row['trusted_pass_total']}",
                f"- Has trusted pass: {row['has_trusted_pass']}",
                f"- Failing: {row['fail_total']}",
                f"- Missing: {row['missing_total']}",
                f"- Conflicting: {row['conflict_total']}",
                "",
            ]
        )
    return "\n".join(lines)


def _row(evidence_type: str, *, required: bool, records: list[Any]) -> dict[str, Any]:
    matching = [record for record in records if record.type == evidence_type]
    counts = Counter(record.status for record in matching)
    trusted_pass = [
        record for record in matching if record.status == "pass" and record.trusted
    ]
    return {
        "evidence_type": evidence_type,
        "required_acceptance": required,
        "record_total": len(matching),
        "trusted_pass_total": len(trusted_pass),
        "has_trusted_pass": bool(trusted_pass),
        "fail_total": counts.get("fail", 0),
        "missing_total": counts.get("missing", 0),
        "conflict_total": counts.get("conflict", 0),
        "record_ids": [record.evidence_id for record in matching],
    }


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]
