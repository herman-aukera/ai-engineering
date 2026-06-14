from __future__ import annotations

from pathlib import Path

from energy_core.models import EnergyDecision


def append_decision(path: str | Path, decision: EnergyDecision) -> Path:
    """Append a decision record to JSONL without mutating previous records."""

    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(decision.model_dump_json())
        handle.write("\n")
    return ledger_path
