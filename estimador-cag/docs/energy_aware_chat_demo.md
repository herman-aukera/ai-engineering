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
9. Deterministic evidence bundle builder for project and research evidence refs
10. Dynamic Energy Chat validation gate and CI conformance tests

## Repository status

This branch is a final-project staging branch inside the LIDR coursework repository. It is not a normal coursework merge branch and should not be merged into `main` just because GitHub reports it as mechanically mergeable.

Repository readiness and future standalone extraction strategy are documented in:

    docs/energy_aware_chat_repository_readiness.md

The expected future standalone repository is:

    herman-aukera/energy-aware-chat

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

This gate runs Ruff auto-fix, Ruff check, Python compilation, dynamic focused Energy Chat test discovery, the full test suite, root diff check, and dirty-tree detection.

The gate must fail when a generated formatting change, test cache, or any other file leaves the working tree dirty after validation.

## CI gate

`.github/workflows/ci.yml` runs on `gg-*` branches and invokes:

    bash scripts/validate_energy_chat.sh

The validation script discovers focused tests with:

    tests/test_energy_chat_*.py

This prevents new Energy Chat tests from being accidentally left out of the focused gate.

For exact GitHub Actions proof, use the non-interactive helper from repository root:

    bash estimador-cag/scripts/check_energy_chat_ci.sh

This helper scopes the check to the current commit and `gg-finalproject-energy-aware-chat`, avoiding failed workflow runs from unrelated branches.

## Run FastAPI

From `estimador-cag`:

    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Open:

    http://localhost:8000/docs

Useful endpoints:

    POST /energy-chat/evaluate
    POST /energy-chat/evaluate/repair-once
    POST /energy-chat/source-needed
    POST /energy-chat/evidence/bundle
    POST /energy-chat/draft/deepseek-baseline
    POST /energy-chat/benchmark/deepseek-energy-aware

## Run Streamlit demo

From `estimador-cag`:

    streamlit run energy_chat_streamlit_app.py --server.address 0.0.0.0 --server.port 8501

Open the forwarded port 8501.

Demo tabs:

1. Evaluate answer
2. Evidence bundle
3. Benchmark harness

The first tab renders the Energy Card for a draft answer. The second tab normalizes evidence refs for project and research claims. The third tab runs a tiny measurement-only benchmark through the API.

## Evidence refs

The evaluator already accepts `evidence_refs`. The evidence bundle endpoint prepares those refs without crawling a repository or retrieving RAG documents.

Trusted evidence prefixes:

1. `git:` for branch or status evidence
2. `test:` for validation output
3. `ci:` for GitHub Actions or pipeline evidence
4. `file:` for repository file evidence
5. `source:` for uploaded source-pack evidence
6. `web:` for retrieved external evidence
7. `manual:` for manually attached evidence
8. `cmd:` for command-output excerpts

Project mode should attach project-state and validation evidence before claiming branch readiness.

Example project evidence refs:

    git:status-clean
    test:325-passed
    ci:energy-chat-validation-green
    file:docs/energy_aware_chat_demo.md

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

For evidence bundling:

    evidence refs + command outputs
    -> normalize trusted refs
    -> detect missing project/research evidence kinds
    -> attach trusted refs to evaluation requests

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
