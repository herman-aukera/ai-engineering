import json
import os
import subprocess
import sys
from pathlib import Path

from evals.session11_generation.run_ragas_s11 import (
    OFFICIAL_PROVIDER,
    PROVIDERS,
)

RUNNER_PATH = Path("evals/session11_generation/run_ragas_s11.py")
SAMPLE_PATH = Path("evals/session11_generation/ragas_sample_s11.json")


def test_ragas_runner_declares_official_openai_and_comparison_providers():
    assert OFFICIAL_PROVIDER == "openai"

    assert set(PROVIDERS) == {"openai", "deepseek", "kimi"}

    assert PROVIDERS["openai"]["env_key"] == "OPENAI_API_KEY"
    assert PROVIDERS["openai"]["official"] is True

    assert PROVIDERS["deepseek"]["env_key"] == "DEEPSEEK_API_KEY"
    assert PROVIDERS["deepseek"]["official"] is False

    assert PROVIDERS["kimi"]["env_key"] == "KIMI_API_KEY"
    assert PROVIDERS["kimi"]["official"] is False


def test_ragas_runner_dry_run_can_select_each_provider():
    for provider in ["openai", "deepseek", "kimi"]:
        completed = subprocess.run(
            [
                sys.executable,
                str(RUNNER_PATH),
                "--dry-run",
                "--judge-provider",
                provider,
                "--sample-path",
                str(SAMPLE_PATH),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        payload = json.loads(completed.stdout)

        assert payload["mode"] == "dry_run"
        assert payload["judge_provider"] == provider
        assert payload["official_baseline"] is (provider == "openai")
        assert payload["sample_count"] == 5
        assert payload["requires_env"] == [PROVIDERS[provider]["env_key"]]


def test_ragas_runner_live_mode_requires_selected_provider_key():
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)

    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--live",
            "--judge-provider",
            "deepseek",
            "--sample-path",
            str(SAMPLE_PATH),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode != 0
    assert "DEEPSEEK_API_KEY is required" in completed.stderr


def test_ragas_runner_rejects_unknown_provider():
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--dry-run",
            "--judge-provider",
            "unknown",
            "--sample-path",
            str(SAMPLE_PATH),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "invalid choice" in completed.stderr
