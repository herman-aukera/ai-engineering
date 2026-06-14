#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

cat <<'MANIFEST'
# Energy Aware Chat standalone export manifest

Target repository:
  herman-aukera/energy-aware-chat

Source branch:
  gg-finalproject-energy-aware-chat

Required paths:
  app/energy_chat/
  energy_chat_streamlit_app.py
  demo_payloads/energy_chat/
  docs/energy_aware_chat_demo.md
  docs/energy_aware_chat_live_demo_readiness.md
  docs/energy_aware_chat_api_smoke_guide.md
  docs/energy_aware_chat_demo_results_template.md
  docs/energy_aware_chat_reviewer_index.md
  docs/energy_aware_chat_repository_readiness.md
  docs/energy_aware_chat_final_project_delivery_plan.md
  docs/energy_aware_chat_demo_walkthrough.md
  docs/energy_aware_chat_session17_backlog.md
  docs/energy_aware_chat_standalone_export_readme.md
  scripts/validate_energy_chat.sh
  scripts/check_energy_chat_ci.sh
  scripts/export_energy_chat_manifest.sh
  scripts/render_energy_chat_release_snapshot.py
  tests/test_energy_chat_*.py
  ../.github/workflows/energy-chat-ci.yml

Required proof before export:
  bash scripts/validate_energy_chat.sh
  bash scripts/check_energy_chat_ci.sh
  git status --short

Claim boundary:
  measurement_only_no_quality_claim

Not exported as product claims yet:
  RAG grounding
  agent orchestration
  production readiness
  DeepSeek quality improvement
  deployment readiness
MANIFEST
