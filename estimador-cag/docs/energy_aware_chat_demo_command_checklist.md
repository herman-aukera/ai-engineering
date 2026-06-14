# Energy Aware Chat demo command checklist

Status: command-only checklist for local demo reproduction.

## Start point

```bash
cd /workspaces/ai-engineering
git switch gg-finalproject-energy-aware-chat
git pull --ff-only
cd estimador-cag
```

## Validate before demo

```bash
bash scripts/validate_energy_chat.sh
```

## Prove dedicated CI

From repository root:

```bash
cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh
```

The target workflow is:

```text
Energy Aware Chat CI
```

## Run Streamlit demo

From `estimador-cag`:

```bash
streamlit run energy_chat_streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

## Demo payloads to open

```text
demo_payloads/energy_chat/evaluate_accept.json
demo_payloads/energy_chat/evaluate_repair_once.json
demo_payloads/energy_chat/source_needed_project.json
demo_payloads/energy_chat/evidence_bundle_project.json
demo_payloads/energy_chat/benchmark_measurement.json
```

## Claim boundary to say aloud

```text
measurement_only_no_quality_claim
```
