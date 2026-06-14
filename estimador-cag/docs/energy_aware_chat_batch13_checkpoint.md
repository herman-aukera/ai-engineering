# Energy Aware Chat Batch 13 checkpoint

Status: demo contract and reviewer proof package.

Base checkpoint before this batch:

```text
b045777 docs: prefer dedicated energy chat ci proof
```

Purpose:

Make the Batch 12 demo artifacts executable and reviewer-ready without changing evaluator semantics.

## Added proof assets

| Asset | Purpose |
|---|---|
| `tests/test_energy_chat_demo_payloads.py` | validates committed JSON payloads against Pydantic contracts and deterministic FastAPI routes |
| `docs/energy_aware_chat_demo_results_template.md` | reusable template for recording validation, endpoint, UI, and claim-boundary proof |
| `docs/energy_aware_chat_api_smoke_guide.md` | manual curl path for demo payloads and deterministic endpoints |
| `docs/energy_aware_chat_reviewer_index.md` | navigation index for final-project review and standalone extraction |
| `tests/test_energy_chat_demo_readiness.py` | guards demo docs, payload references, and claim boundaries |
| `scripts/export_energy_chat_manifest.sh` update | includes demo payloads and dedicated workflow in standalone export boundary |
| `tests/test_energy_chat_export_manifest.py` | executes the export manifest and verifies proof requirements |

## Runtime behavior changed

No evaluator, critic, scorer, router, provider, benchmark, or source-guard semantics changed in this batch.

## Demo payloads now covered

The committed payloads are now covered by automated tests:

```text
demo_payloads/energy_chat/evaluate_accept.json
demo_payloads/energy_chat/evaluate_repair_once.json
demo_payloads/energy_chat/source_needed_project.json
demo_payloads/energy_chat/evidence_bundle_project.json
demo_payloads/energy_chat/benchmark_measurement.json
```

## Required validation after pull

```bash
cd /workspaces/ai-engineering

git fetch origin
git switch gg-finalproject-energy-aware-chat
git pull --ff-only

cd estimador-cag

bash scripts/validate_energy_chat.sh
```

Then exact commit CI proof:

```bash
cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh
```

## Claim boundary

This batch preserves:

```text
measurement_only_no_quality_claim
```

Do not claim:

1. production readiness,
2. deployment readiness,
3. RAG grounding,
4. autonomous agent orchestration,
5. DeepSeek quality improvement.
