# Energy Aware Chat reviewer index

Status: navigation index for final-project review, demo recording, and later standalone extraction.

Branch:

```text
EACHAT
```

Canonical final-project mirror:

```text
finalproject-GGC
```

Product target after Session 17:

```text
herman-aukera/energy-aware-chat
```

## Fast path for review

Read in this order:

1. `docs/energy_aware_chat_examiner_quickstart.md`
2. `docs/energy_aware_chat_closeout_pack.md`
3. `docs/energy_aware_chat_final_project_acceptance_matrix.md`
4. `docs/energy_aware_chat_mvp_upgrade.md`
5. `docs/energy_aware_chat_deployment_readiness_runbook.md`
6. `docs/energy_aware_chat_live_provider_evidence_template.md`
7. `docs/energy_aware_chat_mvp_demo_recording_packet.md`
8. `docs/energy_aware_chat_final_submission_handoff.md`
9. `docs/energy_aware_chat_final_project_proof_packet.md`
10. `docs/energy_aware_chat_actions_filtering.md`
11. `docs/energy_aware_chat_demo.md`
12. `docs/energy_aware_chat_live_demo_readiness.md`
13. `docs/energy_aware_chat_demo_script.md`
14. `docs/energy_aware_chat_demo_command_checklist.md`
15. `docs/energy_aware_chat_api_smoke_guide.md`
16. `docs/energy_aware_chat_demo_results_template.md`
17. `docs/energy_aware_chat_pr_body_draft.md`
18. `docs/energy_aware_chat_final_project_delivery_plan.md`
19. `docs/energy_aware_chat_repository_readiness.md`
20. `docs/energy_aware_chat_session17_backlog.md`
21. `docs/energy_aware_chat_release_snapshot.md`

## Executable proof entry points

| Purpose | Command |
|---|---|
| Examiner quickstart | `docs/energy_aware_chat_examiner_quickstart.md` |
| Closeout pack | `uv run python scripts/render_energy_chat_closeout_pack.py --fail-on-incomplete` |
| Final-project acceptance matrix | `docs/energy_aware_chat_final_project_acceptance_matrix.md` |
| MVP upgrade proof | `docs/energy_aware_chat_mvp_upgrade.md` |
| Deployment readiness runbook | `docs/energy_aware_chat_deployment_readiness_runbook.md` |
| Live provider evidence template | `docs/energy_aware_chat_live_provider_evidence_template.md` |
| MVP demo recording packet | `docs/energy_aware_chat_mvp_demo_recording_packet.md` |
| Final submission handoff | `docs/energy_aware_chat_final_submission_handoff.md` |
| Pull request body draft | `docs/energy_aware_chat_pr_body_draft.md` |
| Demo narration script | `docs/energy_aware_chat_demo_script.md` |
| Demo command checklist | `docs/energy_aware_chat_demo_command_checklist.md` |
| Local Energy Chat gate | `bash scripts/validate_energy_chat.sh` |
| Exact commit CI proof | `bash estimador-cag/scripts/check_energy_chat_ci.sh` from repository root |
| Manual live provider smoke | `gh workflow run "Energy Aware Chat Live Provider Smoke" --ref EACHAT` |
| Actions filtering guide | `docs/energy_aware_chat_actions_filtering.md` |
| Demo API startup | `bash scripts/start_energy_chat.sh` from `estimador-cag` |
| Docker compose API | `docker compose -f docker-compose.energy-chat.yml up --build` from `estimador-cag` |
| Streamlit UI | `streamlit run energy_chat_streamlit_app.py --server.address 0.0.0.0 --server.port 8501` |
| Standalone export manifest | `bash scripts/export_energy_chat_manifest.sh` from `estimador-cag` |
| Release snapshot renderer | `uv run python scripts/render_energy_chat_release_snapshot.py` from `estimador-cag` |

## Demo payloads

| Payload | Purpose |
|---|---|
| `demo_payloads/energy_chat/evaluate_accept.json` | accepted deterministic answer |
| `demo_payloads/energy_chat/evaluate_repair_once.json` | deterministic one-pass repair |
| `demo_payloads/energy_chat/source_needed_project.json` | project evidence requirement |
| `demo_payloads/energy_chat/evidence_bundle_project.json` | project evidence normalization |
| `demo_payloads/energy_chat/benchmark_measurement.json` | measurement-only benchmark request shape |
| `demo_payloads/energy_chat/rag_search_project_rules.json` | deterministic project-source RAG search |
| `demo_payloads/energy_chat/chat_project_release_readiness.json` | local agent orchestration over project rules |

## Current implemented layers

| Layer | Status |
|---|---|
| deterministic evaluator | implemented |
| Energy Card | implemented |
| one-pass repair seam | implemented |
| source-needed classifier | implemented |
| evidence bundle builder | implemented |
| DeepSeek baseline seam | implemented |
| DeepSeek-to-Kimi fallback seam | implemented and deterministic-test covered |
| deterministic RAG grounding baseline | implemented |
| deterministic agent orchestration | implemented |
| measurement-only benchmark harness | implemented |
| report writer | implemented |
| release snapshot helper | implemented |
| closeout pack helper | implemented |
| Streamlit demo | implemented |
| Docker and compose deployment path | implemented |
| dedicated Energy Chat CI | implemented |
| manual live provider smoke workflow | implemented |
| standalone repository extraction plan | documented |

## Explicit non-claims

Do not claim these yet:

1. Production readiness.
2. Public deployment is live.
3. Quality improvement over DeepSeek.
4. Live provider fallback proof unless the manual live-provider smoke workflow passes.
5. Vector database RAG grounding for Energy Aware Chat.
6. Security hardening beyond the current deterministic boundaries.

Required benchmark claim token:

```text
measurement_only_no_quality_claim
```

## Session 17 intake rule

New class material should enter through:

```text
docs/energy_aware_chat_session17_backlog.md
```

Do not add class-inspired features directly to runtime code without:

1. a target slice,
2. a test contract,
3. local validation,
4. exact commit CI proof.
