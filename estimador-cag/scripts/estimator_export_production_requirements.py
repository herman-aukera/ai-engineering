"""Verify and export the isolated estimator production dependency lock."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_ROOT = PROJECT_ROOT / "deploy" / "estimator"
LOCK_PATH = DEPLOY_ROOT / "uv.lock"
LOCK_DIGEST_PATH = DEPLOY_ROOT / "uv.lock.sha256"
OUTPUT_PATH = DEPLOY_ROOT / "requirements.generated.txt"

FORBIDDEN_PRODUCTION_PACKAGES = (
    "anthropic==",
    "ipykernel==",
    "jupyter==",
    "pandas==",
    "pypdf==",
    "python-docx==",
    "redis==",
    "sentence-transformers==",
    "sse-starlette==",
    "streamlit==",
    "torch==",
)


def _run(*args: str) -> None:
    subprocess.run(args, cwd=PROJECT_ROOT, check=True)


def _verify_lock_digest() -> None:
    expected_line = LOCK_DIGEST_PATH.read_text(encoding="utf-8").strip()
    expected_hash, expected_name = expected_line.split(maxsplit=1)
    if expected_name.lstrip("*") != "uv.lock":
        raise RuntimeError("estimator uv.lock.sha256 must name uv.lock")
    actual_hash = hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise RuntimeError("estimator isolated production lock digest mismatch")


def _verify_export_surface() -> None:
    exported = OUTPUT_PATH.read_text(encoding="utf-8").casefold()
    leaked = [name for name in FORBIDDEN_PRODUCTION_PACKAGES if name in exported]
    if leaked:
        raise RuntimeError(
            "estimator production dependency closure contains non-runtime packages: "
            + ", ".join(leaked)
        )
    required = (
        "asyncpg==",
        "fastapi==",
        "langgraph==",
        "litellm==",
        "logfire==",
        "openai==",
        "pgvector==",
        "psycopg==",
        "pydantic-settings==",
        "sqlalchemy==",
        "structlog==",
        "tiktoken==",
        "uvicorn==",
    )
    missing = [name for name in required if name not in exported]
    if missing:
        raise RuntimeError(
            "estimator production dependency closure is missing runtime packages: "
            + ", ".join(missing)
        )


def main() -> None:
    for required_path in (DEPLOY_ROOT / "pyproject.toml", LOCK_PATH, LOCK_DIGEST_PATH):
        if not required_path.is_file():
            raise RuntimeError(f"missing estimator production dependency file: {required_path}")

    _verify_lock_digest()
    _run("uv", "lock", "--project", str(DEPLOY_ROOT), "--check")
    _run(
        "uv",
        "export",
        "--project",
        str(DEPLOY_ROOT),
        "--frozen",
        "--no-dev",
        "--format",
        "requirements-txt",
        "--output-file",
        str(OUTPUT_PATH),
    )
    _verify_export_surface()
    print("ESTIMATOR_ISOLATED_PRODUCTION_DEPENDENCIES_OK")


if __name__ == "__main__":
    main()
