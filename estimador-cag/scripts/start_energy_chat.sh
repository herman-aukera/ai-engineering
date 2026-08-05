#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

exec uv run uvicorn app.main:app --host "$HOST" --port "$PORT"
