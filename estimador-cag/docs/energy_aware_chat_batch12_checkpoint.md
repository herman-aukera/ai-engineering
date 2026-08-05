# Energy Aware Chat Batch 12 checkpoint

Status: live-demo readiness batch on `gg-finalproject-energy-aware-chat`.

Starting certified baseline:

    b045777 docs: prefer dedicated energy chat ci proof

Baseline proof before this batch:

- Local gate: `91 passed` focused Energy Chat tests.
- Full suite: `349 passed`.
- Dedicated workflow: `Energy Aware Chat CI` succeeded on the exact commit.

## Added in Batch 12

### Demo payload fixtures

New fixture folder:

    demo_payloads/energy_chat/

Payloads added:

1. `evaluate_accept.json`
2. `evaluate_repair_once.json`
3. `source_needed_project.json`
4. `evidence_bundle_project.json`
5. `benchmark_measurement.json`

### Live demo readiness guide

New document:

    docs/energy_aware_chat_live_demo_readiness.md

Purpose:

- Start FastAPI.
- Start Streamlit.
- Rehearse Energy Card flow.
- Exercise evidence bundle and benchmark paths.
- Preserve the no-fake-claim boundary.

### Standalone export README draft

New document:

    docs/energy_aware_chat_standalone_export_readme.md

Purpose:

- Provide the first README draft for the future standalone repository.
- Preserve the current export boundary.
- Keep deferred features explicit.

### Repository readiness update

Updated document:

    docs/energy_aware_chat_repository_readiness.md

Purpose:

- Include demo payload fixtures in the standalone export boundary.
- Include live demo readiness and standalone README draft in delivery artifacts.

## Connector-blocked attempts

The GitHub connector blocked several attempted additions:

- Python API smoke script.
- Shell API smoke script.
- Endpoint-exercising demo payload pytest file.
- Extended delivery artifact pytest update.
- Evidence matrix document.

Those were not committed. The committed Batch 12 scope is therefore intentionally documentation and fixture heavy, with no runtime evaluator changes.

## Validation required

After pulling this batch, run:

    bash scripts/validate_energy_chat.sh

Then from repository root:

    bash estimador-cag/scripts/check_energy_chat_ci.sh

Acceptance requires both to be green for the same commit.

## Current claim boundary

The benchmark status remains:

    measurement_only_no_quality_claim

Do not claim RAG grounding, agent orchestration, deployment readiness, production readiness, or model-quality improvement yet.
