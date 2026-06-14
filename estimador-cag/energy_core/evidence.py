from __future__ import annotations

import json
from pathlib import Path

from energy_core.models import EvidenceRecord


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
        records.append(EvidenceRecord.model_validate(payload))

    return records
