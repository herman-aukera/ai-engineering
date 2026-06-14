"""Validate committed Energy Aware Chat demo payloads against typed contracts.

This script is intentionally provider-free and HTTP-free. It is useful before a
reviewer demo, before standalone repository export, and inside future CI jobs
that want to validate demo fixtures without starting FastAPI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.energy_chat.contracts import (
    DeepSeekBenchmarkRequest,
    EnergyChatRequest,
    EvidenceBundleRequest,
    SourceNeedRequest,
)

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_DIR = ROOT / "demo_payloads" / "energy_chat"

CONTRACTS = {
    "evaluate_accept.json": EnergyChatRequest,
    "evaluate_repair_once.json": EnergyChatRequest,
    "source_needed_project.json": SourceNeedRequest,
    "evidence_bundle_project.json": EvidenceBundleRequest,
    "benchmark_measurement.json": DeepSeekBenchmarkRequest,
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_demo_payloads() -> list[str]:
    """Return human-readable validation lines for every demo payload."""
    lines: list[str] = []
    missing: list[str] = []

    for filename, contract in CONTRACTS.items():
        path = PAYLOAD_DIR / filename
        if not path.exists():
            missing.append(filename)
            continue
        contract.model_validate(_load_json(path))
        lines.append(f"OK {filename} -> {contract.__name__}")

    unexpected = sorted(
        path.name for path in PAYLOAD_DIR.glob("*.json") if path.name not in CONTRACTS
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
