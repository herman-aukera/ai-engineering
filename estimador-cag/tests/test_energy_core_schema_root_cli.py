import json
import subprocess
import sys
from pathlib import Path


def test_schema_cli_runs_from_repository_root() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "-m", "energy_core.schema_cli", "--format", "json"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["schema_bundle_version"] == "1.0.0"
    assert "candidate_state" in payload["models"]
    assert "evidence_record" in payload["models"]
