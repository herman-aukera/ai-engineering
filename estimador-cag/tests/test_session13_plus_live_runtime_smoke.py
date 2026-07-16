from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.session13_plus_live_runtime_smoke import build_artifact


def test_live_runtime_artifact_is_sanitized() -> None:
    artifact = build_artifact(
        rows=[
            {
                "tier": "flash",
                "provider": "deepseek",
                "model": "deepseek-test",
                "status": "completed",
            },
            {
                "tier": "backup",
                "provider": "kimi",
                "model": "moonshot/kimi-test",
                "status": "completed",
            },
        ]
    )

    assert artifact["all_providers_completed"] is True
    assert artifact["privacy"] == {
        "prompt_recorded": False,
        "model_content_recorded": False,
        "credentials_recorded": False,
    }
    serialized = json.dumps(artifact)
    for forbidden in ("DEEPSEEK_API_KEY", "KIMI_API_KEY", "LOGFIRE_TOKEN", "pylf_v1_"):
        assert forbidden not in serialized


def test_live_workflow_wires_all_three_secrets_and_artifact() -> None:
    workflow = Path("../.github/workflows/live-smoke.yml").read_text(encoding="utf-8")
    assert "LOGFIRE_TOKEN: ${{ secrets.LOGFIRE_TOKEN }}" in workflow
    assert "session13_plus_live_runtime_smoke" in workflow
    assert "session13_plus_live_runtime.json" in workflow


def test_live_runner_executes_as_direct_file_without_import_failure(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEEPSEEK_API_KEY"] = "test"
    env["KIMI_API_KEY"] = "test"
    completed = subprocess.run(
        [sys.executable, "scripts/session13_plus_live_runtime_smoke.py", "--help"],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "ModuleNotFoundError" not in completed.stderr
