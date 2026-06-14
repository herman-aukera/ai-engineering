from __future__ import annotations


def format_policy_validation_summary(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Policy Validation",
            f"Policy: {summary['policy_id']}",
            f"Version: {summary['version']}",
            f"Complete: {summary['complete']}",
            f"Missing: {_inline_list(summary['missing'])}",
            f"Warnings: {_inline_list(summary['warnings'])}",
            f"Hard constraints: {summary['hard_constraints']}",
            f"Soft constraints: {summary['soft_constraints']}",
            f"Evidence types: {summary['evidence_types']}",
            f"Decision rules: {summary['decision_rules']}",
            f"Required acceptance evidence: {_inline_list(summary['required_acceptance_evidence'])}",
            f"Missing hard constraints: {_inline_list(summary['missing_hard_constraints'])}",
            f"Missing evidence types: {_inline_list(summary['missing_evidence_types'])}",
            f"Unknown acceptance evidence: {_inline_list(summary['unknown_acceptance_evidence'])}",
            f"Thresholds valid: {summary['thresholds_valid']}",
        ]
    )


def format_policy_validation_markdown_report(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Energy Aware Code Policy Validation",
            "",
            f"- Policy: {summary['policy_id']}",
            f"- Version: {summary['version']}",
            f"- Complete: {summary['complete']}",
            f"- Thresholds valid: {summary['thresholds_valid']}",
            f"- Hard constraints: {summary['hard_constraints']}",
            f"- Soft constraints: {summary['soft_constraints']}",
            f"- Evidence types: {summary['evidence_types']}",
            f"- Decision rules: {summary['decision_rules']}",
            "",
            "## Missing",
            "",
            *_bullet_list(summary["missing"]),
            "",
            "## Warnings",
            "",
            *_bullet_list(summary["warnings"]),
            "",
            "## Required acceptance evidence",
            "",
            *_bullet_list(summary["required_acceptance_evidence"]),
            "",
            "## Missing hard constraints",
            "",
            *_bullet_list(summary["missing_hard_constraints"]),
            "",
            "## Missing evidence types",
            "",
            *_bullet_list(summary["missing_evidence_types"]),
            "",
        ]
    )


def format_candidate_validation_summary(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Candidate Validation",
            f"Candidate: {summary['candidate_id']}",
            f"Spec: {summary['spec_id']}",
            f"Complete: {summary['complete']}",
            f"Missing: {_inline_list(summary['missing'])}",
            f"Warnings: {_inline_list(summary['warnings'])}",
            f"Energy before: {summary['energy_before']}",
            f"Changed files: {summary['changed_file_count']}",
            f"Missing artifacts: {_inline_list(summary['missing_artifacts'])}",
            f"Unknown soft flags: {_inline_list(summary['unknown_soft_flags'])}",
            f"Validation claims: {_inline_list(summary['validation_claims'])}",
            f"Scope claims: {_inline_list(summary['scope_claims'])}",
        ]
    )


def format_candidate_validation_markdown_report(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Energy Aware Code Candidate Validation",
            "",
            f"- Candidate: {summary['candidate_id']}",
            f"- Spec: {summary['spec_id']}",
            f"- Complete: {summary['complete']}",
            f"- Energy before: {summary['energy_before']}",
            f"- Changed files: {summary['changed_file_count']}",
            "",
            "## Missing",
            "",
            *_bullet_list(summary["missing"]),
            "",
            "## Warnings",
            "",
            *_bullet_list(summary["warnings"]),
            "",
            "## Missing artifacts",
            "",
            *_bullet_list(summary["missing_artifacts"]),
            "",
            "## Unknown soft flags",
            "",
            *_bullet_list(summary["unknown_soft_flags"]),
            "",
            "## Validation claims",
            "",
            *_bullet_list(summary["validation_claims"]),
            "",
            "## Scope claims",
            "",
            *_bullet_list(summary["scope_claims"]),
            "",
        ]
    )


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]
