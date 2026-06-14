"""Validate committed Energy Aware Chat demo payloads against typed contracts.

This script is intentionally provider-free and HTTP-free. It is useful before a
reviewer demo, before standalone repository export, and inside future CI jobs
that want to validate demo fixtures without starting FastAPI.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_DIR = ROOT / "demo_payloads" / "energy_chat"

CONTRACT_MODULE = "app.energy_chat.contracts"
CONTRACT_NAMES = {
    "evaluate_accept.json": "EnergyChatRequest",
    "evaluate_repair_once.json": "EnergyChatRequest",
    "source_needed_project.json": "SourceNeedRequest",
    "evidence_bundle_project.json": "EvidenceBundleRequest",
    "benchmark_measurement.json": "DeepSeekBenchmarkRequest",
}


def _ensure_project_root_on_path() -> None:
    """Allow this script to be run directly from scripts/ or the project root."""

    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _contract_map() -> dict[str, Any]:
    """Return payload filename to Pydantic model mapping after path bootstrap."""

    _ensure_project_root_on_path()
    module = importlib.import_module(CONTRACT_MODULE)
    return {
        filename: getattr(module, contract_name)
        for filename, contract_name in CONTRACT_NAMES.items()
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_demo_payloads() -> list[str]:
    """Return human-readable validation lines for every demo payload."""

    contracts = _contract_map()
    lines: list[str] = []
    missing: list[str] = []

    for filename, contract in contracts.items():
        path = PAYLOAD_DIR / filename
        if not path.exists():
            missing.append(filename)
            continue
        contract.model_validate(_load_json(path))
        lines.append(f"OK {filename} -> {contract.__name__}")

    unexpected = sorted(
        path.name for path in PAYLOAD_DIR.glob("*.json") if path.name not in contracts
    )
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if unexpected:
            details.append(f"unexpected={unexpected}")
        raise RuntimeError("Invalid Energy Chat demo payload set: " + "; ".join(details))

    return lines


def main() -> int:
    for line in validate_demo_payloads():
        print(line)
    print("Energy Chat demo payload contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
