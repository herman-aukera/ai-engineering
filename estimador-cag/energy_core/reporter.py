from __future__ import annotations

from energy_core.models import EnergyDecision


def format_decision_summary(decision: EnergyDecision) -> str:
    lines = [
        "Energy Aware Code Decision",
        f"Decision: {decision.decision}",
        f"Candidate: {decision.candidate_id}",
        f"Policy: {decision.policy_id}",
        f"Energy: {decision.energy_after}",
        f"Energy before: {decision.energy_before}",
        f"Energy delta: {decision.energy_delta}",
        f"Hard reject violations: {_inline_list(decision.hard_reject_violations)}",
        f"Hard repair violations: {_inline_list(decision.hard_repair_violations)}",
        f"Soft violations: {_inline_list(decision.soft_violations)}",
        f"Missing evidence: {_inline_list(decision.missing_evidence)}",
        "Evidence refs:",
        *_bullet_list(decision.evidence_refs),
        "Required repairs:",
        *_bullet_list(decision.required_repairs),
        f"Reasoning: {decision.reasoning_summary}",
        f"Next action: {decision.next_action}",
    ]
    return "\n".join(lines)


def format_decision_markdown_report(decision: EnergyDecision) -> str:
    sections = [
        "# Energy Aware Code Decision Report",
        "",
        f"Decision: {decision.decision}",
        f"Candidate: {decision.candidate_id}",
        f"Policy: {decision.policy_id}",
        "",
        "## Energy",
        "",
        f"- Energy before: {decision.energy_before}",
        f"- Energy after: {decision.energy_after}",
        f"- Energy delta: {decision.energy_delta}",
        "",
        "## Violations",
        "",
        f"- Hard reject: {_inline_list(decision.hard_reject_violations)}",
        f"- Hard repair: {_inline_list(decision.hard_repair_violations)}",
        f"- Soft: {_inline_list(decision.soft_violations)}",
        f"- Missing evidence: {_inline_list(decision.missing_evidence)}",
        "",
        "## Evidence refs",
        "",
        *_bullet_list(decision.evidence_refs),
        "",
        "## Required repairs",
        "",
        *_bullet_list(decision.required_repairs),
        "",
        "## Reasoning summary",
        "",
        decision.reasoning_summary,
        "",
        "## Next action",
        "",
        decision.next_action,
        "",
    ]
    return "\n".join(sections)


def format_evidence_summary(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Evidence Summary",
            f"Total records: {summary['total']}",
            f"Trusted records: {summary['trusted']}",
            f"Not trusted records: {summary['not_trusted']}",
            f"By status: {_inline_mapping(summary['by_status'])}",
            f"By type: {_inline_mapping(summary['by_type'])}",
            f"Failed evidence: {_inline_list(summary['failed_evidence'])}",
            f"Missing evidence: {_inline_list(summary['missing_evidence'])}",
            f"Conflicting evidence: {_inline_list(summary['conflicting_evidence'])}",
        ]
    )


def format_evidence_markdown_report(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Energy Aware Code Evidence Summary",
            "",
            f"- Total records: {summary['total']}",
            f"- Trusted records: {summary['trusted']}",
            f"- Not trusted records: {summary['not_trusted']}",
            "",
            "## By status",
            "",
            *_mapping_bullet_list(summary["by_status"]),
            "",
            "## By type",
            "",
            *_mapping_bullet_list(summary["by_type"]),
            "",
            "## Failed evidence",
            "",
            *_bullet_list(summary["failed_evidence"]),
            "",
            "## Missing evidence",
            "",
            *_bullet_list(summary["missing_evidence"]),
            "",
            "## Conflicting evidence",
            "",
            *_bullet_list(summary["conflicting_evidence"]),
            "",
        ]
    )


def format_ledger_summary(summary: dict[str, object]) -> str:
    latest = summary["latest_decision"]
    latest_line = "none" if latest is None else f"{latest['candidate_id']} -> {latest['decision']}"
    return "\n".join(
        [
            "Energy Aware Code Decision Ledger Summary",
            f"Total decisions: {summary['total']}",
            f"By decision: {_inline_mapping(summary['by_decision'])}",
            f"Accepted: {summary['accepted']}",
            f"Repair: {summary['repair']}",
            f"Reject: {summary['reject']}",
            f"Escalate: {summary['escalate']}",
            f"Latest decision: {latest_line}",
            f"Candidate ids: {_inline_list(summary['candidate_ids'])}",
        ]
    )


def format_ledger_markdown_report(summary: dict[str, object]) -> str:
    latest = summary["latest_decision"]
    latest_lines = ["- none"]
    if latest is not None:
        latest_lines = [
            f"- Candidate: {latest['candidate_id']}",
            f"- Decision: {latest['decision']}",
            f"- Energy after: {latest['energy_after']}",
            f"- Next action: {latest['next_action']}",
        ]
    return "\n".join(
        [
            "# Energy Aware Code Decision Ledger Summary",
            "",
            f"- Total decisions: {summary['total']}",
            f"- Accepted: {summary['accepted']}",
            f"- Repair: {summary['repair']}",
            f"- Reject: {summary['reject']}",
            f"- Escalate: {summary['escalate']}",
            "",
            "## By decision",
            "",
            *_mapping_bullet_list(summary["by_decision"]),
            "",
            "## Candidate ids",
            "",
            *_bullet_list(summary["candidate_ids"]),
            "",
            "## Latest decision",
            "",
            *latest_lines,
            "",
        ]
    )


def format_spec_coverage_summary(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Spec Coverage",
            f"Spec dir: {summary['spec_dir']}",
            f"Complete: {summary['complete']}",
            f"Required present: {summary['present_required']}/{summary['total_required']}",
            f"Missing: {_inline_list(summary['missing'])}",
            f"Required files: {_inline_mapping_bool(summary['required_files'])}",
            f"Example files: {_inline_mapping_bool(summary['example_files'])}",
            f"Optional files: {_inline_mapping_bool(summary['optional_files'])}",
        ]
    )


def format_spec_coverage_markdown_report(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Energy Aware Code Spec Coverage",
            "",
            f"- Spec dir: {summary['spec_dir']}",
            f"- Complete: {summary['complete']}",
            f"- Required present: {summary['present_required']}/{summary['total_required']}",
            "",
            "## Missing",
            "",
            *_bullet_list(summary["missing"]),
            "",
            "## Required files",
            "",
            *_mapping_bool_bullet_list(summary["required_files"]),
            "",
            "## Example files",
            "",
            *_mapping_bool_bullet_list(summary["example_files"]),
            "",
            "## Optional files",
            "",
            *_mapping_bool_bullet_list(summary["optional_files"]),
            "",
        ]
    )


def format_evidence_summary_text(summary: dict[str, object]) -> str:
    """Backward-compatible alias for older smoke probes."""

    return format_evidence_summary(summary)


def format_evidence_summary_markdown(summary: dict[str, object]) -> str:
    """Backward-compatible alias for older smoke probes."""

    return format_evidence_markdown_report(summary)


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]


def _inline_mapping(mapping: dict[str, int]) -> str:
    if not mapping:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in mapping.items())


def _inline_mapping_bool(mapping: dict[str, bool]) -> str:
    if not mapping:
        return "none"
    return ", ".join(f"{key}={_bool_status(value)}" for key, value in mapping.items())


def _mapping_bullet_list(mapping: dict[str, int]) -> list[str]:
    if not mapping:
        return ["- none"]
    return [f"- {key}: {value}" for key, value in mapping.items()]


def _mapping_bool_bullet_list(mapping: dict[str, bool]) -> list[str]:
    if not mapping:
        return ["- none"]
    return [f"- {key}: {_bool_status(value)}" for key, value in mapping.items()]


def _bool_status(value: bool) -> str:
    return "present" if value else "missing"
