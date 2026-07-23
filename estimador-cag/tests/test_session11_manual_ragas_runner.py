import json
import os
import subprocess
import sys
from pathlib import Path

from evals.session11_generation.run_ragas_s11 import (
    CHAT_JUDGE_MODEL,
    EMBEDDING_MODEL,
    METRICS,
    build_ragas_rows,
    load_sample_contract,
)

RUNNER_PATH = Path("evals/session11_generation/run_ragas_s11.py")
SAMPLE_PATH = Path("evals/session11_generation/ragas_sample_s11.json")


def test_manual_ragas_runner_declares_required_openai_models():
    assert CHAT_JUDGE_MODEL
    assert EMBEDDING_MODEL == "text-embedding-3-small"
    assert METRICS == [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]


def test_manual_ragas_runner_builds_required_ragas_rows():
    payload = load_sample_contract(SAMPLE_PATH)
    rows = build_ragas_rows(payload)

    assert len(rows) == 5

    for row in rows:
        assert set(row) == {
            "question",
            "answer",
            "contexts",
            "ground_truth",
        }
        assert row["question"]
        assert row["answer"]
        assert row["contexts"]
        assert row["ground_truth"]


def test_manual_ragas_runner_dry_run_outputs_contract_summary():
    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--dry-run",
            "--sample-path",
            str(SAMPLE_PATH),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["mode"] == "dry_run"
    assert payload["sample_count"] == 5
    assert payload["metrics"] == METRICS
    assert payload["chat_judge_model"] == CHAT_JUDGE_MODEL
    assert payload["embedding_model"] == EMBEDDING_MODEL
    assert payload["requires_env"] == ["OPENAI_API_KEY"]


def test_manual_ragas_runner_live_mode_requires_openai_key():
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)

    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--live",
            "--sample-path",
            str(SAMPLE_PATH),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode != 0
    assert "OPENAI_API_KEY is required" in completed.stderr
