# Energy Aware Chat demo walkthrough

Status: operator script for a short final-project demo.

Use this walkthrough for a live demo, a screen recording, or a reviewer handoff.

## Preconditions

1. Branch is `gg-finalproject-energy-aware-chat`.
2. Local gate passed with `bash scripts/validate_energy_chat.sh`.
3. Exact-commit CI proof passed with `bash scripts/check_energy_chat_ci.sh`.
4. No real provider key is needed for deterministic evaluator, repair, source, or evidence demos.
5. A live DeepSeek key is optional and only needed for real provider smoke.

## Start services

From `estimador-cag`:

    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

In a second terminal from `estimador-cag`:

    streamlit run energy_chat_streamlit_app.py --server.address 0.0.0.0 --server.port 8501

Open the forwarded Streamlit port.

## Demo 1: accepted answer

Tab: Evaluate answer

User message:

    Review this release-readiness answer and tell me whether it satisfies the constraints.

Draft answer:

    The answer is scoped, cites no fabricated sources, names the main caveat, and the next action is to run the validation gate before claiming success.

Expected visible result:

    Decision: accept
    Energy: 0
    Hard constraints passed
    No critic findings

Reviewer message:

    This shows the happy path. A clean candidate is accepted without model calls.

## Demo 2: repairable answer

Tab: Evaluate answer

User message:

    Review this release-readiness answer.

Draft answer:

    Start with tests.

Required constraint:

    DeepSeek remains deferred

Then call the repair endpoint from FastAPI docs or explain the repair-once endpoint.

Expected result:

    Initial decision: repair
    Repair attempted: true
    Repaired answer includes the missing constraint and a next action

Reviewer message:

    This shows a deterministic repair seam. It is not an LLM self-critique loop yet.

## Demo 3: evidence bundle

Tab: Evidence bundle

Mode:

    project

Evidence refs:

    file:docs/energy_aware_chat_demo.md

Command output label:

    git status --short

Command output body:

    leave empty

Add another command output label:

    energy chat validation gate

Command output body:

    342 passed in 5.00s

Expected trusted refs:

    file:docs/energy_aware_chat_demo.md
    git:status-clean
    test:pytest-passed

Reviewer message:

    This prepares project-mode evidence without adding a RAG database yet.

## Demo 4: benchmark harness

Tab: Benchmark harness

Run the default small benchmark.

Expected visible result:

    cases total
    accepted baseline
    accepted after repair
    repairs attempted
    claim status

Required claim status:

    measurement_only_no_quality_claim

Reviewer message:

    This benchmark harness measures behavior. It does not claim DeepSeek improvement yet.

## Closing message

Energy Aware Chat currently demonstrates a constraint-governed evaluation loop, typed contracts, visible Energy Cards, deterministic repair, source-needed classification, evidence bundling, and measurement-only benchmarking.

The next major layers are project RAG, agent orchestration, documented eval runs, and deployment or video proof.
