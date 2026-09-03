from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = (
    "scripts/ingest_eachat_support_rag.py",
    "scripts/smoke_eachat_final_project_live.py",
    "scripts/smoke_eachat_final_project_compose.py",
    "evals/energy_chat/final_project_eval.py",
    "evals/energy_chat/final_project_system_eval.py",
)


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS)
def test_final_project_cli_entrypoint_bootstraps_project_imports(entrypoint: str) -> None:
    env = {
        **os.environ,
        "DEEPSEEK_API_KEY": "test",
        "KIMI_API_KEY": "test",
        "OPENAI_API_KEY": "test",
    }

    result = subprocess.run(
        [sys.executable, entrypoint, "--help"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.casefold()
