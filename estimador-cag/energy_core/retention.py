from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.models import EvidenceRecord

RETENTION_POLICY_VERSION = "1.0.0"
DEFAULT_RETENTION_POLICY = {
    "release_days": None,
    "audit_days": 365,
    "transient_days": 30,
}
_RELEASE_TYPES = {"release_artifact", "decision_manifest"}
_TRANSIENT_TYPES = {"agent_explanation"}


def build_retention_report(
    records: list[EvidenceRecord],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Classify retention eligibility without deleting or rewriting evidence."""

    current = now or datetime.now(UTC)
    eligible: list[str] = []
    retained: list[str] = []
    retained_missing_timestamp: list[str] = []
    classifications: list[dict[str, Any]] = []
    for record in records:
        retention_class = _retention_class(record.type)
        days = DEFAULT_RETENTION_POLICY[f"{retention_class}_days"]
        if record.recorded_at is None:
            disposition = "retain_missing_timestamp"
            retained_missing_timestamp.append(record.evidence_id)
        elif days is None:
            disposition = "retain"
            retained.append(record.evidence_id)
        else:
            recorded_at = datetime.fromisoformat(record.recorded_at.replace("Z", "+00:00"))
            age_days = (current - recorded_at).days
            disposition = "eligible_for_review" if age_days >= days else "retain"
            (eligible if disposition == "eligible_for_review" else retained).append(
                record.evidence_id
            )
        classifications.append(
            {
                "evidence_id": record.evidence_id,
                "retention_class": retention_class,
                "disposition": disposition,
            }
        )
    return {
        "retention_policy_version": RETENTION_POLICY_VERSION,
        "evaluated_at": current.isoformat().replace("+00:00", "Z"),
        "policy": dict(DEFAULT_RETENTION_POLICY),
        "record_total": len(records),
        "eligible_for_review": sorted(eligible),
        "retained": sorted(retained),
        "retained_missing_timestamp": sorted(retained_missing_timestamp),
        "deleted_record_total": 0,
        "classifications": classifications,
        "non_goals": ["This report never deletes or rewrites evidence."],
    }


def _retention_class(evidence_type: str) -> str:
    if evidence_type in _RELEASE_TYPES:
        return "release"
    if evidence_type in _TRANSIENT_TYPES:
        return "transient"
    return "audit"
