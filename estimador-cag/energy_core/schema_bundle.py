from __future__ import annotations

from typing import Any

from energy_core.models import (
    CandidateState,
    EnergyDecision,
    EnergyPolicy,
    EvidenceRecord,
    Violation,
)

SCHEMA_BUNDLE_VERSION = "1.0.0"

_SCHEMA_MODELS = {
    "candidate_state": CandidateState,
    "energy_decision": EnergyDecision,
    "energy_policy": EnergyPolicy,
    "evidence_record": EvidenceRecord,
    "violation": Violation,
}


def list_schema_names() -> list[str]:
    """Return stable schema names included in the public schema bundle."""

    return sorted(_SCHEMA_MODELS)


def get_schema(name: str) -> dict[str, Any]:
    """Return one JSON schema by stable public name."""

    if name not in _SCHEMA_MODELS:
        available = ", ".join(list_schema_names())
        raise ValueError(f"Unknown schema '{name}'. Available: {available}")
    return _SCHEMA_MODELS[name].model_json_schema()


def build_schema_bundle() -> dict[str, Any]:
    """Build a deterministic JSON-schema bundle for extraction readiness."""

    return {
        "schema_bundle_version": SCHEMA_BUNDLE_VERSION,
        "models": {
            name: get_schema(name)
            for name in list_schema_names()
        },
    }
