from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import smoke_eachat_final_project_compose

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


def test_compose_smoke_keeps_operational_logs_out_of_json_stdout(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        recorded.update(kwargs)
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(smoke_eachat_final_project_compose.subprocess, "run", fake_run)

    smoke_eachat_final_project_compose._compose("config", env={})

    assert recorded["stdout"] is sys.stderr
