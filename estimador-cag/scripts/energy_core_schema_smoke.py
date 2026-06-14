from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    bundle = _run("--format", "json")
    payload = json.loads(bundle.stdout)
    _assert(payload["schema_bundle_version"] == "1.0.0", "schema bundle version should be stable")
    _assert("candidate_state" in payload["models"], "candidate schema should be present")
    _assert("energy_decision" in payload["models"], "decision schema should be present")

    evidence = _run("--schema", "evidence_record", "--format", "text")
    _assert("Schema: evidence_record" in evidence.stdout, "single schema text should print schema name")
    _assert("- evidence_id" in evidence.stdout, "single schema text should print evidence_id field")
    _assert("- status" in evidence.stdout, "single schema text should print status field")

    print("Energy Core schema smoke passed.")
    return 0


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "energy_core.schema_cli", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
