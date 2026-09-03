"""Manual end-to-end proof for docker-compose.final-project.yml.

This script intentionally requires a real embedding credential because the final-project
container stack enables the real support RAG. It records no credentials or answer bodies.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.energy_chat.identity import SignedSessionCodec

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = PROJECT_ROOT.parent / "docker-compose.final-project.yml"
BASE_URL = "http://127.0.0.1:8080"
DEFAULT_SIGNING_KEY = "local-final-project-signing-key-change-me-1234567890"


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke the complete EACHAT final-project stack.")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()

    embedding_key = os.getenv("EACHAT_SUPPORT_EMBEDDING_API_KEY", "").strip()
    if not _usable_secret(embedding_key):
        raise RuntimeError("Set EACHAT_SUPPORT_EMBEDDING_API_KEY to a real embedding credential")

    env = os.environ.copy()
    signing_key = env.get("EACHAT_SESSION_SIGNING_KEY", DEFAULT_SIGNING_KEY)
    try:
        _compose("up", "-d", "--build", env=env)
        _wait_ready()
        token = _token(signing_key)
        before = _chat(
            token,
            "PostgreSQL connections are exhausted. Which server-side limits and active "
            "session evidence should L2 support inspect before assigning a root cause?",
        )
        before_sources = _source_refs(before)
        if not before_sources:
            raise RuntimeError("Initial request did not retain real RAG source evidence")

        _compose("restart", "eachat", env=env)
        _wait_ready()
        after = _chat(
            token,
            "A Docker container exits after startup. Which logs and runtime state should L2 "
            "support inspect first?",
        )
        after_sources = _source_refs(after)
        if not after_sources:
            raise RuntimeError("RAG evidence disappeared after EACHAT container restart")

        evidence = {
            "status": "success",
            "stack": COMPOSE_FILE.name,
            "ready_before_restart": True,
            "ready_after_restart": True,
            "initial_source_ref_count": len(before_sources),
            "post_restart_source_ref_count": len(after_sources),
            "initial_disposition": before.get("final_disposition"),
            "post_restart_disposition": after.get("final_disposition"),
            "answer_body_recorded": False,
            "credential_recorded": False,
        }
        print(json.dumps(evidence, indent=2, sort_keys=True))
        return 0
    finally:
        if args.cleanup:
            _compose("down", env=env, check=False)


def _compose(*args: str, env: dict[str, str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), *args],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        check=check,
    )


def _wait_ready(timeout_seconds: int = 180) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/ready", timeout=3) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
                if response.status == 200 and payload.get("ready") is True:
                    return
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = type(exc).__name__
        time.sleep(2)
    raise RuntimeError(f"EACHAT stack did not become ready: {last_error}")


def _chat(token: str, question: str) -> dict[str, object]:
    payload = json.dumps(
        {
            "user_message": question,
            "mode": "project",
            "k": 5,
            "orchestration_mode": "critic",
        }
    ).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310
        f"{BASE_URL}/energy-chat/v2/chat",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("final_answer"):
        raise RuntimeError("EACHAT returned no final answer")
    return result


def _token(signing_key: str) -> str:
    return SignedSessionCodec(signing_key.encode("utf-8")).issue(
        subject="final-project-reviewer",
        tenant_id="local-final-project",
        roles=("reviewer",),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


def _source_refs(response: dict[str, object]) -> list[str]:
    refs = response.get("evidence_refs", [])
    return [str(ref) for ref in refs if str(ref).startswith("source:")]


def _usable_secret(value: str) -> bool:
    normalized = value.strip().casefold()
    return bool(normalized) and normalized not in {"test", "dummy", "placeholder", "changeme"}


if __name__ == "__main__":
    raise SystemExit(main())
