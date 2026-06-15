#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-300}"

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
uv run ruff check --fix app tests energy_chat_streamlit_app.py scripts/validate_energy_chat_demo_payloads.py scripts/render_energy_chat_release_snapshot.py scripts/list_energy_chat_artifacts.py

echo "=== ENERGY CHAT VALIDATION: RUFF CHECK ==="
uv run ruff check app tests energy_chat_streamlit_app.py scripts/validate_energy_chat_demo_payloads.py scripts/render_energy_chat_release_snapshot.py scripts/list_energy_chat_artifacts.py

echo "=== ENERGY CHAT VALIDATION: PY COMPILE ==="
uv run python -m py_compile $(find app tests -name '*.py' -type f 2>/dev/null) streamlit_app.py energy_chat_streamlit_app.py scripts/validate_energy_chat_demo_payloads.py scripts/render_energy_chat_release_snapshot.py scripts/list_energy_chat_artifacts.py

echo "=== ENERGY CHAT VALIDATION: DEMO PAYLOAD CONTRACTS ==="
uv run python scripts/validate_energy_chat_demo_payloads.py

echo "=== ENERGY CHAT VALIDATION: FOCUSED TEST DISCOVERY ==="
mapfile -t energy_chat_tests < <(find tests -maxdepth 1 -name 'test_energy_chat_*.py' -type f | sort)
if [[ ${#energy_chat_tests[@]} -eq 0 ]]; then
  echo "No focused Energy Chat tests found."
  exit 1
fi
printf ' - %s\n' "${energy_chat_tests[@]}"

echo "=== ENERGY CHAT VALIDATION: FOCUSED TESTS ==="
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q "${energy_chat_tests[@]}"

echo "=== ENERGY CHAT VALIDATION: FULL TEST SUITE ==="
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q

echo "=== ENERGY CHAT VALIDATION: ROOT DIFF CHECK ==="
cd ..
git diff --check origin/main...HEAD

echo "=== ENERGY CHAT VALIDATION: STATUS ==="
git status --short
fail_on_dirty_tree
