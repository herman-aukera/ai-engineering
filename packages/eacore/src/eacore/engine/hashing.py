from __future__ import annotations

from hashlib import sha256
from typing import Any

from .canonical import canonical_json_bytes


def sha256_hex(value: bytes | str) -> str:
    payload = value.encode("utf-8") if isinstance(value, str) else value
    return sha256(payload).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_hex(canonical_json_bytes(value))


def candidate_fingerprint(*, candidate_kind: str, payload: Any, parent_id: str | None = None) -> str:
    return canonical_hash(
        {"candidate_kind": candidate_kind, "parent_candidate_id": parent_id, "payload": payload}
    )


def ledger_record_hash(record: Any) -> str:
    """Hash a ledger record excluding its self-referential canonical_hash field."""
    if hasattr(record, "model_dump"):
        payload = record.model_dump(mode="python")
    elif isinstance(record, dict):
        payload = dict(record)
    else:
        raise TypeError("ledger record must be a model or mapping")
    payload.pop("canonical_hash", None)
    return canonical_hash(payload)
