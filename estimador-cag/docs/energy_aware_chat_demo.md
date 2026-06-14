# Energy Aware Chat demo

Status: final-project-track MVP layer
Branch: `gg-finalproject-energy-aware-chat`

## What exists now

Energy Aware Chat is currently a constraint-governed assistant-answer evaluator. It is not yet a full RAG assistant.

Implemented layers:

1. Deterministic evaluator core
2. FastAPI `/energy-chat/evaluate`
3. Streamlit Energy Card demo
4. One-pass deterministic repair seam
5. DeepSeek baseline draft seam
6. Measurement-only benchmark harness
7. Benchmark report writer
8. Deterministic source-needed classifier for research and project-mode preparation

## What is deliberately not claimed yet

1. No RAG grounding yet.
2. No agent orchestration yet.
3. No production readiness claim.
4. No DeepSeek improvement claim.
5. No frontier-model comparison claim.

Benchmark outputs must keep this claim status until live fixed-case measurements exist:

    measurement_only_no_quality_claim

## Run validation

From `estimador-cag`:

    bash scripts/validate_energy_chat.sh

This gate runs Ruff auto-fix, Ruff check, Python compilation, focused Energy Chat tests, the full test suite, root diff check, and git status.

## Run FastAPI

From `estimador-cag`:

    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Open:

    http://localhost:8000/docs

Useful endpoints:

    POST /energy-chat/evaluate
    POST /energy-chat/evaluate/repair-once
    POST /energy-chat/source-needed
    POST /energy-chat/draft/deepseek-baseline
    POST /energy-chat/benchmark/deepseek-energy-aware

## Run Streamlit demo

From `estimador-cag`:

    streamlit run energy_chat_streamlit_app.py --server.address 0.0.0.0 --server.port 8501

Open the forwarded port 8501.

Demo tabs:

1. Evaluate answer
2. Benchmark harness

The first tab renders the Energy Card for a draft answer. The second tab runs a tiny measurement-only benchmark through the API.

## Source-needed classifier

The source-needed classifier is deterministic and provider-free. It prepares the later research and project modes by detecting whether an answer needs current external evidence or project-specific evidence.

Current or external evidence examples:

1. current API version
2. release notes
3. model availability
4. legal or regulatory claims
5. changing deadlines or pricing

Project evidence examples:

1. branch state
2. repository files
3. validation gate output
4. pytest, Ruff, CI, or git evidence
5. LIDR source-pack rules

The classifier does not retrieve documents yet. It only decides whether evidence is required, recommended, or not required.

## Current architecture flow

    user message + draft answer
    -> deterministic critics
    -> source-needed classifier
    -> energy score
    -> decider
    -> Energy Card

For one-pass repair:

    user message + draft answer
    -> initial evaluation
    -> deterministic repair if repairable
    -> final evaluation
    -> repair decision record

For measurement-only benchmarking:

    fixed cases
    -> plain DeepSeek draft seam
    -> deterministic evaluation
    -> one-pass repair seam
    -> measurement record
    -> optional markdown report

## Next planned layers

1. Persist benchmark reports under an evals folder after live/fake runs are finalized.
2. Add source-grounded RAG over project rules and final-project requirements.
3. Add an agent layer for retrieval plus critic/decider orchestration.
4. Add documented evals and at least one regression case for final delivery.
5. Prepare deployment or a 2 to 3 minute demo video.
