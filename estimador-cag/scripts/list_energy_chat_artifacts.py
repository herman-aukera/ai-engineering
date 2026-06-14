#!/usr/bin/env python3
"""Print the canonical Energy Aware Chat artifact registry."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.energy_chat.artifact_registry import list_energy_chat_artifacts  # noqa: E402


def main() -> int:
    for artifact in list_energy_chat_artifacts():
        print(f"{artifact.kind}\t{artifact.path}\t{artifact.purpose}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
