"""Verify and export the isolated EACHAT production dependency lock."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_ROOT = PROJECT_ROOT / "deploy" / "eachat"
LOCK_PATH = DEPLOY_ROOT / "uv.lock"
LOCK_DIGEST_PATH = DEPLOY_ROOT / "uv.lock.sha256"
OUTPUT_PATH = DEPLOY_ROOT / "requirements.generated.txt"

FORBIDDEN_PRODUCTION_PACKAGES = (
    "anthropic==", "ipykernel==", "jupyter==", "pandas==", "pypdf==",
    "python-docx==", "redis==", "sentence-transformers==", "streamlit==", "torch==",
)


def _run(*args: str) -> None:
    subprocess.run(args, cwd=PROJECT_ROOT, check=True)


def main() -> None:
    expected_line = LOCK_DIGEST_PATH.read_text(encoding="utf-8").strip()
    expected_hash, expected_name = expected_line.split(maxsplit=1)
    if expected_name.lstrip("*") != "uv.lock":
        raise RuntimeError("EACHAT uv.lock.sha256 must name uv.lock")
    if hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest() != expected_hash:
        raise RuntimeError("EACHAT isolated production lock digest mismatch")
    _run("uv", "lock", "--project", str(DEPLOY_ROOT), "--check")
    _run(
        "uv", "export", "--project", str(DEPLOY_ROOT), "--frozen", "--no-dev",
        "--format", "requirements-txt", "--output-file", str(OUTPUT_PATH),
    )
    exported = OUTPUT_PATH.read_text(encoding="utf-8").casefold()
    leaked = [name for name in FORBIDDEN_PRODUCTION_PACKAGES if name in exported]
    if leaked:
        raise RuntimeError("EACHAT production closure leaked coursework packages: " + ", ".join(leaked))
    required = (
        "cryptography==", "fastapi==", "langgraph==", "openai==", "psycopg==",
        "psycopg-pool==", "pydantic-settings==", "uvicorn==",
    )
    missing = [name for name in required if name not in exported]
    if missing:
        raise RuntimeError("EACHAT production closure misses runtime packages: " + ", ".join(missing))
    print("EACHAT_ISOLATED_PRODUCTION_DEPENDENCIES_OK")


if __name__ == "__main__":
    main()
