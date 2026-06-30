import json
import os
import subprocess
import sys
from pathlib import Path

from evals.session11_generation.run_ragas_s11 import (
    EMBEDDING_ENV_KEY,
    PROVIDERS,
)

RUNNER_PATH = Path("evals/session11_generation/run_ragas_s11.py")
SAMPLE_PATH = Path("evals/session11_generation/ragas_sample_s11.json")


def test_ragas_runner_declares_openai_embedding_env_key_for_all_providers():
    assert EMBEDDING_ENV_KEY == "OPENAI_API_KEY"

    for provider_name, config in PROVIDERS.items():
        assert "env_key" in config
        assert "official" in config


def test_deepseek_and_kimi_dry_run_require_provider_key_and_openai_embedding_key():
    for provider in ["deepseek", "kimi"]:
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

        assert payload["judge_provider"] == provider
        assert payload["requires_env"] == [
            PROVIDERS[provider]["env_key"],
            EMBEDDING_ENV_KEY,
        ]


def test_openai_dry_run_requires_openai_key_only_once():
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--dry-run",
            "--judge-provider",
            "openai",
            "--sample-path",
            str(SAMPLE_PATH),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["judge_provider"] == "openai"
    assert payload["requires_env"] == ["OPENAI_API_KEY"]


def test_deepseek_live_mode_requires_openai_embedding_key_even_if_deepseek_key_exists():
    env = dict(os.environ)
    env["DEEPSEEK_API_KEY"] = "dummy-deepseek-key"
    env.pop("OPENAI_API_KEY", None)

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
    assert "OPENAI_API_KEY is required for embeddings" in completed.stderr
