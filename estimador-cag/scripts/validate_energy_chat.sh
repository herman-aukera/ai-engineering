#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

cleanup_pycaches() {
  find app tests -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
  rm -rf .pytest_cache 2>/dev/null || true
}

fail_on_dirty_tree() {
  cleanup_pycaches
  local status
  status=$(git status --short)
  if [[ -n "$status" ]]; then
    echo "=== ENERGY CHAT VALIDATION: DIRTY TREE DETECTED ==="
    echo "$status"
    echo "Validation failed because the working tree is dirty after the gate."
    exit 1
  fi
}

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
  tests/test_energy_chat_benchmark.py \
  tests/test_energy_chat_reports.py \
  tests/test_energy_chat_documentation.py \
  tests/test_energy_chat_source_guard.py

echo "=== ENERGY CHAT VALIDATION: FULL TEST SUITE ==="
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q

echo "=== ENERGY CHAT VALIDATION: ROOT DIFF CHECK ==="
cd ..
git diff --check origin/main...HEAD

echo "=== ENERGY CHAT VALIDATION: STATUS ==="
git status --short
fail_on_dirty_tree
