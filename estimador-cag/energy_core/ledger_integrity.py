from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from energy_core.models import EnergyDecision
from energy_core.record_schema import migrate_decision_payload

LEDGER_INTEGRITY_VERSION = "1.0.0"


def build_ledger_integrity(
    ledger_path: Path,
    *,
    evidence_path: Path | None = None,
) -> dict[str, Any]:
    """Inspect an append-only decision ledger without mutating it."""

    path = ledger_path.resolve()
    if not path.exists():
        return {
            "ledger_integrity_version": LEDGER_INTEGRITY_VERSION,
            "ledger_path": str(path),
            "exists": False,
            "complete": False,
            "record_total": 0,
            "valid_record_total": 0,
            "invalid_record_total": 0,
            "blank_line_total": 0,
            "decision_counts": {},
            "candidate_ids": [],
            "duplicate_candidate_ids": [],
            "duplicate_decision_ids": [],
            "duplicate_evidence_ids": [],
            "dangling_evidence_refs": [],
            "invalid_records": [
                {
                    "line": None,
                    "error": "ledger file does not exist",
                }
            ],
            "energy_delta_mismatches": [],
            "warnings": [],
            "non_goals": _non_goals(),
        }

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    valid_records: list[EnergyDecision] = []
    invalid_records: list[dict[str, Any]] = []
    blank_line_total = 0

    for line_number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            blank_line_total += 1
            continue
        try:
            payload = json.loads(line)
            valid_records.append(
                EnergyDecision.model_validate(migrate_decision_payload(payload))
            )
        except json.JSONDecodeError as exc:
            invalid_records.append(
                {
                    "line": line_number,
                    "error": f"invalid JSON decision record: {exc.msg}",
                }
            )
        except ValidationError as exc:
            invalid_records.append(
                {
                    "line": line_number,
                    "error": f"invalid decision record: {exc.errors()}",
                }
            )

    duplicate_candidate_ids = _duplicate_candidate_ids(valid_records)
    duplicate_decision_ids = _duplicate_decision_ids(valid_records)
    evidence_ids, duplicate_evidence_ids = _inspect_evidence_ids(evidence_path)
    dangling_evidence_refs = _dangling_evidence_refs(valid_records, evidence_ids)
    energy_delta_mismatches = _energy_delta_mismatches(valid_records)
    warnings = []
    if duplicate_candidate_ids:
        warnings.append(
            "Duplicate candidate IDs are allowed for repeated evaluations but should be reviewed."
        )
    if blank_line_total:
        warnings.append("Blank lines are ignored but should be avoided in committed ledgers.")
    if evidence_path is None:
        warnings.append("Evidence referential integrity was not checked because no evidence path was supplied.")

    decision_counts = Counter(record.decision for record in valid_records)
    record_total = len(raw_lines) - blank_line_total
    invalid_total = len(invalid_records)

    return {
        "ledger_integrity_version": LEDGER_INTEGRITY_VERSION,
        "ledger_path": str(path),
        "exists": True,
        "complete": (
            invalid_total == 0
            and not energy_delta_mismatches
            and not duplicate_decision_ids
            and not duplicate_evidence_ids
            and not dangling_evidence_refs
        ),
        "record_total": record_total,
        "valid_record_total": len(valid_records),
        "invalid_record_total": invalid_total,
        "blank_line_total": blank_line_total,
        "decision_counts": dict(sorted(decision_counts.items())),
        "candidate_ids": [record.candidate_id for record in valid_records],
        "duplicate_candidate_ids": duplicate_candidate_ids,
        "duplicate_decision_ids": duplicate_decision_ids,
        "duplicate_evidence_ids": duplicate_evidence_ids,
        "dangling_evidence_refs": dangling_evidence_refs,
        "invalid_records": invalid_records,
        "energy_delta_mismatches": energy_delta_mismatches,
        "warnings": warnings,
        "non_goals": _non_goals(),
    }


def format_ledger_integrity_text(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Energy Aware Code Ledger Integrity",
            f"Version: {report['ledger_integrity_version']}",
            f"Ledger: {report['ledger_path']}",
            f"Exists: {report['exists']}",
            f"Complete: {report['complete']}",
            f"Records: {report['valid_record_total']}/{report['record_total']}",
            f"Invalid records: {report['invalid_record_total']}",
            f"Energy delta mismatches: {len(report['energy_delta_mismatches'])}",
            f"Duplicate candidate IDs: {_inline_list(report['duplicate_candidate_ids'])}",
            f"Duplicate decision IDs: {_inline_list(report['duplicate_decision_ids'])}",
            f"Duplicate evidence IDs: {_inline_list(report['duplicate_evidence_ids'])}",
            f"Dangling evidence refs: {len(report['dangling_evidence_refs'])}",
        ]
    )


def format_ledger_integrity_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Energy Aware Code Ledger Integrity",
        "",
        f"- Version: {report['ledger_integrity_version']}",
        f"- Ledger: {report['ledger_path']}",
        f"- Exists: {report['exists']}",
        f"- Complete: {report['complete']}",
        f"- Valid records: {report['valid_record_total']}/{report['record_total']}",
        f"- Invalid records: {report['invalid_record_total']}",
        f"- Blank lines: {report['blank_line_total']}",
        "",
        "## Decision counts",
        "",
    ]
    lines.extend(_key_value_bullets(report["decision_counts"]))
    lines.extend(["", "## Duplicate candidate IDs", ""])
    lines.extend(_bullet_list(report["duplicate_candidate_ids"]))
    lines.extend(["", "## Duplicate decision IDs", ""])
    lines.extend(_bullet_list(report["duplicate_decision_ids"]))
    lines.extend(["", "## Duplicate evidence IDs", ""])
    lines.extend(_bullet_list(report["duplicate_evidence_ids"]))
    lines.extend(["", "## Dangling evidence references", ""])
    lines.extend(_record_bullets(report["dangling_evidence_refs"]))
    lines.extend(["", "## Invalid records", ""])
    lines.extend(_record_bullets(report["invalid_records"]))
    lines.extend(["", "## Energy delta mismatches", ""])
    lines.extend(_record_bullets(report["energy_delta_mismatches"]))
    lines.extend(["", "## Warnings", ""])
    lines.extend(_bullet_list(report["warnings"]))
    lines.extend(["", "## Non goals", ""])
    lines.extend(_bullet_list(report["non_goals"]))
    return "\n".join(lines)


def _duplicate_candidate_ids(records: list[EnergyDecision]) -> list[str]:
    counts = Counter(record.candidate_id for record in records)
    return sorted(candidate_id for candidate_id, count in counts.items() if count > 1)


def _duplicate_decision_ids(records: list[EnergyDecision]) -> list[str]:
    counts = Counter(record.decision_id for record in records if record.decision_id)
    return sorted(decision_id for decision_id, count in counts.items() if count > 1)


def _inspect_evidence_ids(evidence_path: Path | None) -> tuple[set[str] | None, list[str]]:
    if evidence_path is None:
        return None, []
    if not evidence_path.exists():
        return set(), []
    ids: list[str] = []
    for line in evidence_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        evidence_id = payload.get("evidence_id") if isinstance(payload, dict) else None
        if isinstance(evidence_id, str):
            ids.append(evidence_id)
    counts = Counter(ids)
    return set(ids), sorted(item for item, count in counts.items() if count > 1)


def _dangling_evidence_refs(
    records: list[EnergyDecision],
    evidence_ids: set[str] | None,
) -> list[dict[str, Any]]:
    if evidence_ids is None:
        return []
    return [
        {"line": line, "candidate_id": record.candidate_id, "evidence_id": evidence_id}
        for line, record in enumerate(records, start=1)
        for evidence_id in record.evidence_refs
        if evidence_id not in evidence_ids
    ]


def _energy_delta_mismatches(records: list[EnergyDecision]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        expected_delta = record.energy_after - record.energy_before
        if record.energy_delta != expected_delta:
            mismatches.append(
                {
                    "line": index,
                    "candidate_id": record.candidate_id,
                    "expected_delta": expected_delta,
                    "actual_delta": record.energy_delta,
                }
            )
    return mismatches


def _non_goals() -> list[str]:
    return [
        "Ledger integrity does not append to the decision ledger.",
        "Ledger integrity does not execute shell actions.",
        "Ledger integrity does not call LLM providers.",
        "Ledger integrity does not prove git-level append-only history by itself.",
    ]


def _inline_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def _key_value_bullets(items: dict[str, Any]) -> list[str]:
    return [f"- {key}: {value}" for key, value in items.items()] if items else ["- none"]


def _record_bullets(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return ["- none"]
    return [f"- {json.dumps(record, sort_keys=True)}" for record in records]
