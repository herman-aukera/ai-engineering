from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from energy_core.hashing import sha256_bytes, sha256_file
from energy_core.models import EvidenceRecord
from energy_core.record_schema import migrate_evidence_payload

EVIDENCE_RECOVERY_VERSION = "1.0.0"


def recover_evidence_ledger(
    source_path: str | Path,
    recovered_path: str | Path,
    quarantine_path: str | Path,
) -> dict[str, Any]:
    """Copy valid evidence rows and quarantine invalid rows without mutation."""

    source = Path(source_path).resolve()
    recovered = Path(recovered_path).resolve()
    quarantine = Path(quarantine_path).resolve()
    if len({source, recovered, quarantine}) != 3:
        raise ValueError("Source, recovered, and quarantine paths must differ.")
    for output in (recovered, quarantine):
        if output.exists():
            raise FileExistsError(f"Recovery output already exists: {output}")
    source_bytes = source.read_bytes()
    raw_lines = source_bytes.decode("utf-8").splitlines()
    valid_rows: list[str] = []
    quarantined_rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("evidence row must be an object")
            record = EvidenceRecord.model_validate(migrate_evidence_payload(payload))
            valid_rows.append(record.model_dump_json())
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            quarantined_rows.append(
                {"line": line_number, "error": str(exc), "raw": line}
            )
    recovered.parent.mkdir(parents=True, exist_ok=True)
    quarantine.parent.mkdir(parents=True, exist_ok=True)
    recovered.write_text(
        "".join(f"{row}\n" for row in valid_rows), encoding="utf-8", newline="\n"
    )
    quarantine.write_text(
        "".join(f"{json.dumps(row, sort_keys=True)}\n" for row in quarantined_rows),
        encoding="utf-8",
        newline="\n",
    )
    return {
        "evidence_recovery_version": EVIDENCE_RECOVERY_VERSION,
        "source_sha256": sha256_bytes(source_bytes),
        "recovered_sha256": sha256_file(recovered),
        "quarantine_sha256": sha256_file(quarantine),
        "source_record_total": len([line for line in raw_lines if line.strip()]),
        "recovered_record_total": len(valid_rows),
        "quarantined_record_total": len(quarantined_rows),
        "source_mutated": False,
        "complete": not quarantined_rows,
    }
