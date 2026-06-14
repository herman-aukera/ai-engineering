from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from energy_core.models import EnergyDecision


class LedgerLoadError(ValueError):
    """Raised when a decision ledger cannot be parsed as EnergyDecision JSONL."""


def append_decision(path: str | Path, decision: EnergyDecision) -> Path:
    """Append a decision record to JSONL without mutating previous records."""

    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(decision.model_dump_json())
        handle.write("\n")
    return ledger_path


def read_decisions(path: str | Path) -> list[EnergyDecision]:
    """Read an append-only decision ledger.

    A missing ledger is treated as an empty history so inspection commands are
    safe before the first accepted decision exists.
    """

    ledger_path = Path(path)
    if not ledger_path.exists():
        return []

    decisions: list[EnergyDecision] = []
    for line_number, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            decisions.append(EnergyDecision.model_validate(payload))
        except json.JSONDecodeError as exc:
            raise LedgerLoadError(f"{ledger_path}:{line_number}: invalid JSON decision record: {exc.msg}") from exc
        except ValidationError as exc:
            raise LedgerLoadError(f"{ledger_path}:{line_number}: invalid decision record: {exc}") from exc
    return decisions


def summarize_decisions(decisions: list[EnergyDecision]) -> dict[str, object]:
    """Create a deterministic, JSON-compatible summary of decision history."""

    by_decision = Counter(decision.decision for decision in decisions)
    latest = decisions[-1] if decisions else None
    return {
        "total": len(decisions),
        "by_decision": dict(sorted(by_decision.items())),
        "candidate_ids": [decision.candidate_id for decision in decisions],
        "latest_decision": latest.model_dump(mode="json") if latest else None,
        "accepted": by_decision.get("accept", 0),
        "repair": by_decision.get("repair", 0),
        "reject": by_decision.get("reject", 0),
        "escalate": by_decision.get("escalate", 0),
    }
