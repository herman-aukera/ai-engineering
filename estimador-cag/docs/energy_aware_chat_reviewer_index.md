# Energy Aware Chat reviewer index

Status: navigation index for final-project review, demo recording, and later standalone extraction.

Branch:

```text
gg-finalproject-energy-aware-chat
```

Product target after Session 17:

```text
herman-aukera/energy-aware-chat
```

## Fast path for review

Read in this order:

1. `docs/energy_aware_chat_examiner_quickstart.md`
2. `docs/energy_aware_chat_final_submission_handoff.md`
3. `docs/energy_aware_chat_final_project_proof_packet.md`
4. `docs/energy_aware_chat_actions_filtering.md`
5. `docs/energy_aware_chat_demo.md`
6. `docs/energy_aware_chat_live_demo_readiness.md`
7. `docs/energy_aware_chat_demo_script.md`
8. `docs/energy_aware_chat_api_smoke_guide.md`
9. `docs/energy_aware_chat_demo_results_template.md`
10. `docs/energy_aware_chat_pr_body_draft.md`
11. `docs/energy_aware_chat_final_project_delivery_plan.md`
12. `docs/energy_aware_chat_repository_readiness.md`
13. `docs/energy_aware_chat_session17_backlog.md`
14. `docs/energy_aware_chat_release_snapshot.md`

## Executable proof entry points

| Purpose | Command |
|---|---|
| Examiner quickstart | `docs/energy_aware_chat_examiner_quickstart.md` |
| Final submission handoff | `docs/energy_aware_chat_final_submission_handoff.md` |
| Pull request body draft | `docs/energy_aware_chat_pr_body_draft.md` |
| Demo narration script | `docs/energy_aware_chat_demo_script.md` |
| Local Energy Chat gate | `bash scripts/validate_energy_chat.sh` |
| Exact commit CI proof | `bash estimador-cag/scripts/check_energy_chat_ci.sh` from repository root |
| Actions filtering guide | `docs/energy_aware_chat_actions_filtering.md` |
| Demo API startup | `bash ../.devcontainer/start-estimador-services.sh api` from `estimador-cag` |
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

## Current implemented layers

| Layer | Status |
|---|---|
| deterministic evaluator | implemented |
| Energy Card | implemented |
| one-pass repair seam | implemented |
| source-needed classifier | implemented |
| evidence bundle builder | implemented |
| DeepSeek baseline seam | implemented |
| measurement-only benchmark harness | implemented |
| report writer | implemented |
| release snapshot helper | implemented |
| Streamlit demo | implemented |
| dedicated Energy Chat CI | implemented |
| standalone repository extraction plan | documented |

## Explicit non-claims

Do not claim these yet:

1. Production readiness.
2. Deployment readiness.
3. RAG grounding.
4. Autonomous agent orchestration.
5. Quality improvement over DeepSeek.
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
