from __future__ import annotations

from typing import Any

EVIDENCE_SCHEMA_VERSION = "1.0.0"
DECISION_SCHEMA_VERSION = "1.0.0"


def migrate_evidence_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a current evidence payload without mutating legacy source data."""

    migrated = dict(payload)
    migrated.setdefault("schema_version", EVIDENCE_SCHEMA_VERSION)
    migrated.setdefault("run_id", "legacy")
    migrated.setdefault("recorded_at", None)
    migrated.setdefault("provenance", {"migration": "legacy-unversioned"})
    migrated.setdefault("redaction_status", "unknown")
    migrated.setdefault(
        "trust_classification",
        "trusted" if migrated.get("trusted", True) else "untrusted",
    )
    migrated.setdefault("command_hash", None)
    migrated.setdefault("artifact_hash", None)
    return migrated


def migrate_decision_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a current decision payload without mutating legacy source data."""

    migrated = dict(payload)
    migrated.setdefault("schema_version", DECISION_SCHEMA_VERSION)
    migrated.setdefault("decision_id", None)
    migrated.setdefault("run_id", "legacy")
    migrated.setdefault("recorded_at", None)
    migrated.setdefault("provenance", {"migration": "legacy-unversioned"})
    return migrated
