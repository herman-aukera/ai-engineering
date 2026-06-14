from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from energy_core.models import EnergyPolicy


class PolicyLoadError(ValueError):
    """Raised when an energy policy cannot be loaded as a typed policy."""


def _load_json_compatible_yaml(path: Path) -> dict[str, Any]:
    """Load the Slice 1 policy without adding parser dependencies.

    The MVP stores the `.yaml` policy as JSON-compatible YAML. JSON is valid YAML,
    keeps this first slice dependency-free, and can later be replaced by PyYAML or
    ruamel.yaml when richer YAML syntax becomes necessary.
    """

    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PolicyLoadError(f"Energy policy not found: {path}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PolicyLoadError(
            f"Energy policy must be JSON-compatible YAML in Slice 1: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise PolicyLoadError(f"Energy policy root must be an object: {path}")

    return payload


def load_policy(path: str | Path) -> EnergyPolicy:
    """Load and validate an Energy Aware Code policy file."""

    payload = _load_json_compatible_yaml(Path(path))
    return EnergyPolicy.model_validate(payload)
