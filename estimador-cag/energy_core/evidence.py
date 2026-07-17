from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from energy_core.models import EvidenceRecord
from energy_core.record_schema import migrate_evidence_payload


class EvidenceLoadError(ValueError):
    """Raised when an evidence JSONL file cannot be parsed."""


def read_evidence_records(path: str | Path) -> list[EvidenceRecord]:
    evidence_path = Path(path)
    try:
        raw_lines = evidence_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise EvidenceLoadError(f"Evidence file not found: {evidence_path}") from exc

    records: list[EvidenceRecord] = []
    for line_number, line in enumerate(raw_lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise EvidenceLoadError(
                f"Evidence file contains invalid JSON on line {line_number}: {evidence_path}"
            ) from exc
        if not isinstance(payload, dict):
            raise EvidenceLoadError(
                f"Evidence line {line_number} must be an object: {evidence_path}"
            )
        try:
            records.append(EvidenceRecord.model_validate(migrate_evidence_payload(payload)))
        except ValidationError as exc:
            raise EvidenceLoadError(
                f"Evidence line {line_number} does not match the Energy Aware Code evidence schema. "
                "Expected fields include evidence_id, type, status, summary, and trusted. "
                "Valid status values are pass, fail, missing, and conflict."
            ) from exc

    return records


def load_evidence_records(path: str | Path) -> list[EvidenceRecord]:
    """Backward-compatible alias for older smoke probes."""

    return read_evidence_records(path)


def summarize_evidence(records: list[EvidenceRecord]) -> dict[str, object]:
    """Summarize evidence records without executing or approving anything."""

    by_status = Counter(record.status for record in records)
    by_type = Counter(record.type for record in records)
    trusted_count = sum(1 for record in records if record.trusted)

    return {
        "total": len(records),
        "by_status": dict(sorted(by_status.items())),
        "by_type": dict(sorted(by_type.items())),
        "trusted": trusted_count,
        "not_trusted": len(records) - trusted_count,
        "failed_evidence": [record.evidence_id for record in records if record.status == "fail"],
        "missing_evidence": [record.evidence_id for record in records if record.status == "missing"],
        "conflicting_evidence": [record.evidence_id for record in records if record.status == "conflict"],
    }
