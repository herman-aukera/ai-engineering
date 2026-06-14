from __future__ import annotations

import json
from pathlib import Path

from energy_core.models import CandidateState


class CandidateStateLoadError(ValueError):
    """Raised when a candidate state JSON file is invalid."""


def read_candidate_state(path: str | Path) -> CandidateState:
    candidate_path = Path(path)
    try:
        payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CandidateStateLoadError(f"Candidate state not found: {candidate_path}") from exc
    except json.JSONDecodeError as exc:
        raise CandidateStateLoadError(f"Candidate state is not valid JSON: {candidate_path}") from exc

    if not isinstance(payload, dict):
        raise CandidateStateLoadError(f"Candidate state root must be an object: {candidate_path}")

    return CandidateState.model_validate(payload)
