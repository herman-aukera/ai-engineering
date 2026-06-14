#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== ENERGY CHAT VALIDATION: RUFF FIX ==="
uv run ruff check --fix app tests energy_chat_streamlit_app.py

echo "=== ENERGY CHAT VALIDATION: RUFF CHECK ==="
uv run ruff check app tests energy_chat_streamlit_app.py

echo "=== ENERGY CHAT VALIDATION: PY COMPILE ==="
uv run python -m py_compile $(find app tests -name '*.py' -type f 2>/dev/null) streamlit_app.py energy_chat_streamlit_app.py

echo "=== ENERGY CHAT VALIDATION: FOCUSED TESTS ==="
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q \
  tests/test_energy_chat_contracts.py \
  tests/test_energy_chat_critics.py \
  tests/test_energy_chat_scorer.py \
  tests/test_energy_chat_decider.py \
  tests/test_energy_chat_evaluator.py \
  tests/test_energy_chat_repairs.py \
  tests/test_energy_chat_router.py \
  tests/test_energy_chat_streamlit_app.py \
  tests/test_energy_chat_baseline.py \
  tests/test_energy_chat_benchmark.py

echo "=== ENERGY CHAT VALIDATION: FULL TEST SUITE ==="
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q

echo "=== ENERGY CHAT VALIDATION: ROOT DIFF CHECK ==="
cd ..
git diff --check origin/main...HEAD

echo "=== ENERGY CHAT VALIDATION: STATUS ==="
git status --short
