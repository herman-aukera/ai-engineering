"""Versioned model-registry service for Session 13 Plus V3.

The registry is a deterministic, in-memory collection of :class:`ModelRecord`
entries.  It answers capability queries without calling any provider.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.schemas.v3_registry import ModelRecord


@dataclass(frozen=True)
class ModelRegistry:
    """Versioned, immutable model-capability registry.

    Duplicate (provider, provider_model_id) pairs are rejected at construction
    time.  The registry is read-only after creation — updates produce a new
    instance.
    """

    _records: tuple[ModelRecord, ...]

    def __init__(self, records: Iterable[ModelRecord]) -> None:
        by_key: dict[tuple[str, str], ModelRecord] = {}
        for record in records:
            key = (record.provider, record.provider_model_id)
            if key in by_key:
                raise ValueError(
                    f"duplicate model registry entry: {record.provider}/{record.provider_model_id}"
                )
            by_key[key] = record
        # Use __setattr__ because the dataclass is frozen.
        object.__setattr__(self, "_records", tuple(by_key.values()))

    def lookup(self, *, provider: str, provider_model_id: str) -> ModelRecord | None:
        """Return the matching record or ``None``."""
        for record in self._records:
            if record.provider == provider and record.provider_model_id == provider_model_id:
                return record
        return None

    def list_enabled(self) -> list[ModelRecord]:
        """Return every record whose calibration_status is ``enabled`` and availability is ``available``."""
        return [
            record
            for record in self._records
            if record.calibration_status == "enabled" and record.availability == "available"
        ]

    def list_by_provider(self, provider: str) -> list[ModelRecord]:
        """Return every record for the given provider."""
        return [record for record in self._records if record.provider == provider]

    def __len__(self) -> int:
        return len(self._records)


_LIFECYCLE_ORDER: dict[str, int] = {
    "documented": 0,
    "configured": 1,
    "reachable": 2,
    "contract_verified": 3,
    "benchmark_calibrated": 4,
    "enabled": 5,
}


def transition_allowed(current: str, proposed: str) -> bool:
    """Return True if the lifecycle transition is valid.

    Transitions must follow the documented order.  Skipping stages is not
    allowed.  Staying at the same status is always allowed.
    """
    current_rank = _LIFECYCLE_ORDER.get(current)
    proposed_rank = _LIFECYCLE_ORDER.get(proposed)
    if current_rank is None or proposed_rank is None:
        raise ValueError(
            f"Unknown calibration status: current={current!r}, proposed={proposed!r}"
        )
    # Same status or exactly one step forward.
    return proposed_rank in (current_rank, current_rank + 1)
