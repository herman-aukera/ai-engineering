#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

cat <<'MANIFEST'
# Energy Aware Chat standalone export manifest

Target repository:
  herman-aukera/energy-aware-chat

Source branch:
  EACHAT

Required paths:
  app/energy_chat/
  energy_chat_streamlit_app.py
  demo_payloads/energy_chat/
  docs/energy_aware_chat_examiner_quickstart.md
  docs/energy_aware_chat_mvp_upgrade.md
  docs/energy_aware_chat_final_submission_handoff.md
  docs/energy_aware_chat_pr_body_draft.md
  docs/energy_aware_chat_demo.md
  docs/energy_aware_chat_live_demo_readiness.md
  docs/energy_aware_chat_demo_script.md
  docs/energy_aware_chat_demo_command_checklist.md
  docs/energy_aware_chat_api_smoke_guide.md
  docs/energy_aware_chat_demo_results_template.md
  docs/energy_aware_chat_reviewer_index.md
  docs/energy_aware_chat_final_project_proof_packet.md
  docs/energy_aware_chat_demo_evidence_checklist.md
  docs/energy_aware_chat_actions_filtering.md
  docs/energy_aware_chat_repository_readiness.md
  docs/energy_aware_chat_final_project_delivery_plan.md
  docs/energy_aware_chat_demo_walkthrough.md
  docs/energy_aware_chat_session17_backlog.md
  docs/energy_aware_chat_standalone_export_readme.md
  docs/energy_aware_chat_release_snapshot.md
  scripts/validate_energy_chat.sh
  scripts/check_energy_chat_ci.sh
  scripts/smoke_energy_chat_live_provider.py
  scripts/start_energy_chat.sh
  scripts/export_energy_chat_manifest.sh
  scripts/render_energy_chat_release_snapshot.py
  Dockerfile.energy-chat
  docker-compose.energy-chat.yml
  tests/test_energy_chat_*.py
  ../.github/workflows/energy-chat-ci.yml
  ../.github/workflows/energy-chat-live-provider-smoke.yml

Required proof before export:
  bash scripts/validate_energy_chat.sh
  bash scripts/check_energy_chat_ci.sh
  git status --short

Manual live proof, optional but recommended:
  gh workflow run "Energy Aware Chat Live Provider Smoke" --ref EACHAT

Claim boundary:
  measurement_only_no_quality_claim

Implemented as MVP candidate:
  deterministic RAG baseline
  deterministic agent orchestration
  DeepSeek-to-Kimi fallback seam
  deployment skeleton

Not exported as product claims yet:
  production readiness
  public deployment is live
  quality improvement over DeepSeek
  vector database RAG for Energy Aware Chat
MANIFEST
