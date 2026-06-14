# Energy Aware Chat live demo readiness

Status: final-project demo preparation for `gg-finalproject-energy-aware-chat`.

This document is the reviewer-facing checklist for the current Energy Aware Chat staging branch. It assumes the branch has already passed:

- `bash scripts/validate_energy_chat.sh`
- `bash scripts/check_energy_chat_ci.sh`

## Demo objective

Show that Energy Aware Chat is a constraint-governed assistant answer evaluator, not a generic chatbot wrapper.

The demo should prove five capabilities:

1. A clean answer can be accepted with a visible Energy Card.
2. A weak answer can trigger a deterministic one-pass repair.
3. A project claim can require evidence before acceptance.
4. Evidence refs can be normalized into a trusted evidence bundle.
5. Benchmark output is measurement-only and carries the `measurement_only_no_quality_claim` boundary.

## Start services

From `estimador-cag`:

    bash ../.devcontainer/start-estimador-services.sh api

Then, in another terminal:

    streamlit run energy_chat_streamlit_app.py --server.address 0.0.0.0 --server.port 8501

If Streamlit runs outside localhost, set:

    ESTIMADOR_BACKEND_URL=<forwarded FastAPI URL>

## Demo payload fixtures

The current payload fixtures live in:

    demo_payloads/energy_chat/

Current fixtures:

- `evaluate_accept.json`
- `evaluate_repair_once.json`
- `source_needed_project.json`
- `evidence_bundle_project.json`
- `benchmark_measurement.json`

They are designed for manual API smoke, demo rehearsal, and future standalone repository export.

## Manual API smoke examples

Evaluate a clean answer:

    curl -sS -X POST http://127.0.0.1:8000/energy-chat/evaluate \
      -H 'Content-Type: application/json' \
      --data-binary @demo_payloads/energy_chat/evaluate_accept.json

Evaluate and repair once:

    curl -sS -X POST http://127.0.0.1:8000/energy-chat/evaluate/repair-once \
      -H 'Content-Type: application/json' \
      --data-binary @demo_payloads/energy_chat/evaluate_repair_once.json

Classify whether sources are needed:

    curl -sS -X POST http://127.0.0.1:8000/energy-chat/source-needed \
      -H 'Content-Type: application/json' \
      --data-binary @demo_payloads/energy_chat/source_needed_project.json

Build an evidence bundle:

    curl -sS -X POST http://127.0.0.1:8000/energy-chat/evidence/bundle \
      -H 'Content-Type: application/json' \
      --data-binary @demo_payloads/energy_chat/evidence_bundle_project.json

Run the measurement-only benchmark harness:

    curl -sS -X POST http://127.0.0.1:8000/energy-chat/benchmark/deepseek-energy-aware \
      -H 'Content-Type: application/json' \
      --data-binary @demo_payloads/energy_chat/benchmark_measurement.json

## Streamlit demo path

Open the Streamlit forwarded URL and run these tabs in order:

1. Evaluate answer
2. Evidence bundle
3. Benchmark harness

Do not claim production readiness, RAG grounding, or model quality improvement. The current benchmark layer is still measurement-only.

## Recording checklist

Before recording:

- Local gate is green.
- Dedicated Energy Aware Chat CI is green for the exact commit.
- Browser shows the Streamlit app.
- FastAPI `/docs` opens.
- No secrets are visible in terminal, browser, or screenshots.

After recording:

- Save the run SHA.
- Save the CI run URL.
- Note which features are still deferred until later class sessions.
